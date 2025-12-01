"""
Prospecting API endpoints with SSE streaming.

Routes:
- POST /api/v1/prospect/start - Start prospecting job
- GET /api/v1/prospect/{job_id}/stream - SSE stream for real-time updates
- GET /api/v1/prospect/{job_id}/status - Get job status
- POST /api/v1/prospect/{job_id}/cancel - Cancel running job
"""
import asyncio
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime, timezone
from queue import Queue
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.supervisor_orchestrator import SupervisorOrchestrator, OrchestratorResult
import re


def transform_message(level: str, message: str) -> tuple[str | None, str | None]:
    """Transform technical log to user-friendly message.

    Returns (display_message, event_type) or (None, None) to hide.
    """
    level_upper = level.upper()

    # Messages to HIDE completely (internal/technical)
    HIDE_LEVELS = {"THOUGHT", "REVIEW", "COLLECT", "AGGREGATE", "RUN", "LLM", "RETRY", "FIX"}

    if level_upper in HIDE_LEVELS:
        return None, None

    # Messages to hide by content patterns
    HIDE_PATTERNS = [
        "Supervisor Orchestrator",
        "Architecture:",
        "intra-step",
        "Parallel workers",
        "Product:",
        "ICP:",
    ]

    if any(p.lower() in message.lower() for p in HIDE_PATTERNS):
        return None, None

    # Transform known level patterns
    if level_upper == "START":
        return "Starting lead search...", "thought"

    if level_upper == "PARALLEL":
        if "deploying" in message.lower() or "worker" in message.lower():
            return "Deploying search agents...", "thought"
        return None, None

    if level_upper == "TARGET":
        return "Target reached!", "thought"

    # Strategy messages - keep but clean up
    if level_upper == "STRATEGY":
        if "planning" in message.lower():
            return "Planning search strategy...", "thought"
        if "competitors" in message.lower():
            # Extract competitor count if present
            match = re.search(r"(\d+)\s*competitors?", message.lower())
            if match:
                return f"Identified {match.group(1)} competitors to analyze", "thought"
            return "Analyzing competitors...", "thought"
        return None, None

    # Approved messages - reformat
    if level_upper == "APPROVED":
        # "reddit: 15 leads approved" → "Reddit: Found 15 leads"
        match = re.match(r"(\w+):\s*(\d+)\s*leads?\s*approved", message, re.IGNORECASE)
        if match:
            platform_map = {"reddit": "Reddit", "techcrunch": "TechCrunch", "competitor": "LinkedIn"}
            platform = platform_map.get(match.group(1).lower(), match.group(1).title())
            return f"{platform}: Found {match.group(2)} leads", "thought"
        return None, None

    # Complete messages
    if level_upper == "COMPLETE":
        if "final:" in message.lower():
            match = re.search(r"final:\s*(\d+)", message.lower())
            if match:
                return f"Complete: {match.group(1)} qualified leads", "thought"
            return message.replace("Final:", "Complete:"), "thought"
        return None, None

    # Worker messages - pass through (handled separately)
    if level_upper in ["REDDIT", "TECHCRUNCH", "COMPETITOR"]:
        # Clean up worker messages
        cleaned = message
        # Remove [INFO], [DEBUG], etc prefixes
        cleaned = re.sub(r"\[(?:INFO|DEBUG|WARN|ERROR)\]\s*", "", cleaned)
        return cleaned, None  # None event_type means handle normally as worker

    # Default: pass through for other messages
    return message, "thought"


router = APIRouter(prefix="/api/v1/prospect", tags=["prospecting"])


# In-memory storage for jobs
class ProspectingJob:
    """Represents an active prospecting job."""
    def __init__(self, job_id: str, query: str, max_leads: int):
        self.job_id = job_id
        self.query = query
        self.max_leads = max_leads
        self.status = "initializing"  # initializing, running, completed, failed, cancelled
        self.created_at = datetime.now(timezone.utc)
        self.events = Queue()
        self.result: Optional[OrchestratorResult] = None
        self.error = None
        self.cancel_event = threading.Event()  # For cancellation


# Active jobs storage
active_jobs: Dict[str, ProspectingJob] = {}


# Request/Response models
class StartProspectingRequest(BaseModel):
    """Request to start prospecting."""
    query: str
    max_leads: int = 20


class StartProspectingResponse(BaseModel):
    """Response with job ID."""
    job_id: str
    message: str
    stream_url: str


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    query: str
    max_leads: int
    created_at: datetime
    error: Optional[str] = None


@router.post("/start", response_model=StartProspectingResponse)
async def start_prospecting(request: StartProspectingRequest):
    """
    Start a new prospecting job.

    Returns job_id and SSE stream URL for real-time updates.
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Create job
    job = ProspectingJob(
        job_id=job_id,
        query=request.query,
        max_leads=request.max_leads
    )
    active_jobs[job_id] = job

    # Start prospecting in background thread
    def run_prospecting():
        """Run SupervisorOrchestrator in background."""
        try:
            job.status = "running"

            # Log callback to queue events for SSE
            def log_callback(level: str, message: str):
                """Convert orchestrator logs to SSE events."""
                # Check for cancellation
                if job.cancel_event.is_set():
                    raise Exception("Job cancelled by user")

                # Transform message for better UX
                transformed_msg, transformed_type = transform_message(level, message)

                # Skip messages that should be hidden
                if transformed_msg is None:
                    return

                # Determine event type and worker
                event_type = transformed_type or "thought"
                worker = None
                level_upper = level.upper()

                # Handle worker-specific events
                if level_upper in ["REDDIT", "TECHCRUNCH", "COMPETITOR"]:
                    worker = level_upper.lower()
                    msg_lower = message.lower()
                    # Determine worker event type based on content
                    if any(x in msg_lower for x in ["starting", "running", "searching", "fetching", "scraping"]):
                        event_type = "worker_start"
                    elif any(x in msg_lower for x in ["complete", "found", "approved", "finished", "done"]):
                        event_type = "worker_complete"
                    else:
                        event_type = "worker_update"
                elif level_upper in ["ERROR", "FATAL"]:
                    event_type = "error"

                event = {
                    "type": event_type,
                    "data": transformed_msg,
                    "worker": worker,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                job.events.put(event)

            # Lead callback for real-time streaming
            def lead_callback(worker_name: str, leads: list):
                """Emit leads as they're found by each worker."""
                if job.cancel_event.is_set():
                    return

                if leads:
                    job.events.put({
                        "type": "lead_batch",
                        "data": json.dumps(leads),
                        "leads": leads,
                        "worker": worker_name,
                        "count": len(leads),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

            # Create and run orchestrator
            orchestrator = SupervisorOrchestrator(
                log_callback=log_callback,
                lead_callback=lead_callback,
                output_dir="."
            )

            # Run orchestrator
            result = orchestrator.run(
                product_description=request.query,
                target_leads=request.max_leads
            )

            # Check for cancellation before completing
            if job.cancel_event.is_set():
                job.status = "cancelled"
                job.events.put({"type": "cancelled", "data": "Job cancelled by user"})
                return

            # Store result (leads already sent via lead_callback)
            job.result = result

            # Note: leads are now streamed in real-time via lead_callback
            # No final batch needed - leads were emitted as workers completed

            job.status = "completed"
            job.events.put({
                "type": "completed",
                "data": json.dumps({
                    "total_leads": result.total_leads,
                    "hot_leads": result.hot_leads,
                    "warm_leads": result.warm_leads,
                    "execution_time": result.execution_time
                })
            })

        except Exception as e:
            if job.cancel_event.is_set():
                job.status = "cancelled"
                job.events.put({"type": "cancelled", "data": "Job cancelled by user"})
            else:
                job.status = "failed"
                job.error = str(e)
                job.events.put({"type": "error", "data": str(e)})

    # Start background thread
    thread = threading.Thread(target=run_prospecting, daemon=True)
    thread.start()

    return StartProspectingResponse(
        job_id=job_id,
        message="Prospecting job started",
        stream_url=f"/api/v1/prospect/{job_id}/stream"
    )


@router.get("/{job_id}/stream")
async def stream_prospecting(job_id: str):
    """
    SSE stream for real-time prospecting updates.

    Streams events as they happen:
    - thought: Agent reasoning
    - worker_start: Worker begins (reddit/techcrunch/competitor)
    - worker_complete: Worker finished
    - lead_batch: New leads discovered
    - completed: Job finished
    - cancelled: Job cancelled
    - error: Error occurred
    """
    # Check if job exists
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    async def event_generator():
        """Generate SSE events from job queue."""
        # Send initial status
        yield f"event: status\ndata: {{\"status\": \"{job.status}\", \"query\": \"{job.query}\"}}\n\n"

        # Stream events from queue
        while True:
            # Check if there are events in queue
            if not job.events.empty():
                event = job.events.get()
                event_type = event.get("type", "message")

                # Serialize event data as JSON
                event_data = json.dumps(event)

                # Send SSE event
                yield f"event: {event_type}\ndata: {event_data}\n\n"

                # If job completed, failed, or cancelled, end stream
                if event_type in ["completed", "error", "cancelled"]:
                    break

            # Sleep briefly to avoid busy waiting
            await asyncio.sleep(0.1)

            # If job is in terminal state and queue is empty, end stream
            if job.status in ["completed", "failed", "cancelled"] and job.events.empty():
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@router.post("/{job_id}/cancel")
async def cancel_prospecting(job_id: str):
    """
    Cancel a running prospecting job.

    Sets the cancel event which will be checked by the orchestrator.
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    if job.status not in ["initializing", "running"]:
        raise HTTPException(status_code=400, detail=f"Job cannot be cancelled (status: {job.status})")

    # Set cancel event
    job.cancel_event.set()

    return {"message": "Cancel request sent", "job_id": job_id}


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get current status of a prospecting job."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        query=job.query,
        max_leads=job.max_leads,
        created_at=job.created_at,
        error=job.error
    )


@router.get("/{job_id}/results")
async def get_job_results(job_id: str):
    """
    Get final results of a completed prospecting job.

    Returns leads with:
    - Intent scores
    - Intent signals
    - Source platforms
    - Contact information
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    if job.status == "running":
        raise HTTPException(status_code=202, detail="Job still running, check status endpoint")

    if job.status == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error}")

    if job.status == "cancelled":
        return {
            "job_id": job_id,
            "query": job.query,
            "status": "cancelled",
            "lead_count": 0,
            "leads": [],
            "message": "Job was cancelled"
        }

    if job.status != "completed" or not job.result:
        raise HTTPException(status_code=404, detail="No results available yet")

    # Extract results from OrchestratorResult
    result = job.result

    return {
        "job_id": job_id,
        "query": job.query,
        "status": "completed",
        "lead_count": result.total_leads,
        "leads": result.leads,
        "hot_leads": result.hot_leads,
        "warm_leads": result.warm_leads,
        "reddit_leads": result.reddit_leads,
        "techcrunch_leads": result.techcrunch_leads,
        "competitor_leads": result.competitor_leads,
        "platforms_searched": result.platforms_searched,
        "execution_time": result.execution_time,
        "message": f"Found {result.total_leads} leads ({result.hot_leads} hot, {result.warm_leads} warm)"
    }
