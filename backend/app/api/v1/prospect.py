"""
Prospecting API endpoints with SSE streaming.

Routes:
- POST /api/v1/prospect/start - Start prospecting job
- GET /api/v1/prospect/{job_id}/stream - SSE stream for real-time updates
- GET /api/v1/prospect/{job_id}/status - Get job status
"""
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime
from queue import Queue
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.flows.prospecting_flow import ProspectingFlow, ProspectingState


router = APIRouter(prefix="/api/v1/prospect", tags=["prospecting"])


# In-memory storage for jobs
class ProspectingJob:
    """Represents an active prospecting job."""
    def __init__(self, job_id: str, query: str, max_leads: int):
        self.job_id = job_id
        self.query = query
        self.max_leads = max_leads
        self.status = "initializing"  # initializing, running, completed, failed
        self.created_at = datetime.now()
        self.events = Queue()
        self.result = None
        self.error = None


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
    error: str = None


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
        """Run ProspectingFlow in background."""
        try:
            job.status = "running"

            # Event callback to queue events for SSE
            def event_callback(event: Dict[str, Any]):
                job.events.put(event)

            # Create and run flow
            flow = ProspectingFlow(event_callback=event_callback)
            result = flow.kickoff(inputs={
                "query": request.query,
                "max_leads": request.max_leads
            })

            # Store result
            job.result = result
            job.status = "completed"
            job.events.put({"type": "completed", "data": "Prospecting completed successfully"})

        except Exception as e:
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
    - tool: Tool execution
    - lead_found: New lead discovered
    - completed: Job finished
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
                event_data = event.get("data", "")

                # Send SSE event
                yield f"event: {event_type}\ndata: {event_data}\n\n"

                # If job completed or failed, end stream
                if event_type in ["completed", "error"]:
                    break

            # Sleep briefly to avoid busy waiting
            await asyncio.sleep(0.1)

            # If job is in terminal state and queue is empty, end stream
            if job.status in ["completed", "failed"] and job.events.empty():
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
