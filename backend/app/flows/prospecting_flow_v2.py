"""
ProspectingFlow v2 - Simplified flow using single Orchestrator Agent.

This flow replaces the 6-crew sequential pipeline with a single intelligent agent
that autonomously decides which tools to use based on the query.

OLD APPROACH (6 crews, ~15+ min):
Reddit → LinkedIn → Twitter → Google → Aggregation → Qualification

NEW APPROACH (1 agent, ~5-8 min):
Query → Orchestrator Agent (reasons, executes, adapts, retries) → Qualified Leads
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, listen, start, router
from enum import Enum

# Import orchestrator crew
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crews.orchestrator.crew import OrchestratorCrew, ProspectingOutput, Lead, LeadPriority
from utils.agent_logger import AgentLogger
from utils.lead_exporter import export_leads_json, export_leads_csv, format_leads_table


class ProspectingStatus(str, Enum):
    INITIALIZING = "initializing"
    RESEARCHING = "researching"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ProspectingState(BaseModel):
    """State management for simplified prospecting flow."""
    # Input
    query: str = ""
    product_description: str = ""
    target_leads: int = 100
    icp_criteria: Dict[str, Any] = {}

    # Progress
    status: ProspectingStatus = ProspectingStatus.INITIALIZING
    current_strategy: str = ""
    retries: int = 0

    # Results
    leads: List[Dict[str, Any]] = []
    hot_leads: int = 0
    warm_leads: int = 0
    platforms_searched: List[str] = []
    strategies_used: List[str] = []

    # Tracking
    reasoning_log: List[str] = []
    error: str = ""


class ProspectingFlowV2(Flow[ProspectingState]):
    """
    Simplified prospecting flow using single Orchestrator Agent.

    This flow:
    1. Initializes and validates input
    2. Runs the Orchestrator Agent (which autonomously handles all research)
    3. Routes based on result quality
    4. Retries with different strategy if needed
    5. Returns qualified leads with full logging

    Benefits over v1:
    - Single intelligent agent instead of 6 fixed crews
    - Agent adapts strategy based on results
    - Much faster (parallel tool execution)
    - Better results (iterative refinement)
    - Full execution logging for transparency
    """

    def __init__(
        self,
        event_callback: Callable[[Dict], None] = None,
        output_dir: str = "."
    ):
        """
        Initialize flow with optional event callback for SSE streaming.

        Args:
            event_callback: Function to call with events for real-time updates
            output_dir: Directory to save logs and exported leads
        """
        super().__init__()
        self.event_callback = event_callback
        self.output_dir = output_dir
        self.orchestrator_crew = None
        self.logger = None

    def emit_event(self, event_type: str, data: Any):
        """Emit event for SSE streaming."""
        if self.event_callback:
            self.event_callback({"type": event_type, "data": data})
        # Also log to state
        if hasattr(self, 'state') and self.state:
            self.state.reasoning_log.append(f"[{event_type}] {data}")

    @start()
    def initialize(self):
        """Initialize prospecting session and validate inputs."""
        # Initialize logger
        run_id = f"prospecting-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.logger = AgentLogger(run_id=run_id)
        self.logger.log_phase("Initialization")

        self.emit_event("thought", "Initializing intelligent prospecting flow v2...")
        self.logger.log_reasoning("Starting prospecting flow v2 with single Orchestrator Agent")

        # Use query as product_description if not provided
        if not self.state.product_description:
            self.state.product_description = self.state.query

        self.emit_event("thought", f"Product: {self.state.product_description}")
        self.emit_event("thought", f"Target: {self.state.target_leads} high-quality leads")
        self.emit_event("thought", "Using single Orchestrator Agent with full tool suite")

        self.logger.log_reasoning(f"Query: {self.state.product_description}")
        self.logger.log_reasoning(f"Target: {self.state.target_leads} leads")

        # Initialize orchestrator crew
        self.orchestrator_crew = OrchestratorCrew()

        self.state.status = ProspectingStatus.RESEARCHING
        self.logger.log_phase("Initialization", status="completed")
        return self.state

    @listen(initialize)
    def run_orchestrator(self, state: ProspectingState):
        """
        Run the Orchestrator Agent to find leads.

        The agent autonomously:
        - Analyzes the query
        - Chooses best platforms/tools
        - Executes searches
        - Reflects on results
        - Adapts strategy if needed
        - Enriches and scores leads
        """
        self.logger.log_phase("Orchestrator Agent Execution")
        self.emit_event("agent_started", "Orchestrator Agent analyzing query...")
        self.emit_event("thought", f"Strategy: {state.current_strategy or 'Agent will decide'}")

        self.logger.log_reasoning(f"Starting orchestrator with strategy: {state.current_strategy or 'auto'}")
        self.logger.log_tool_call("OrchestratorCrew", {
            "product_description": state.product_description[:100],
            "target_leads": state.target_leads,
            "icp_criteria": state.icp_criteria
        })

        try:
            # Execute orchestrator crew
            result = self.orchestrator_crew.crew().kickoff(inputs={
                "product_description": state.product_description,
                "target_leads": state.target_leads,
                "icp_criteria": state.icp_criteria
            })

            # Parse structured output
            output: ProspectingOutput = result.pydantic

            # Update state with results
            state.leads = [lead.model_dump() for lead in output.leads]
            state.hot_leads = output.hot_leads
            state.warm_leads = output.warm_leads
            state.platforms_searched = output.platforms_searched
            state.strategies_used = output.strategies_used

            # Log results
            self.logger.log_tool_result(
                "OrchestratorCrew",
                f"Found {output.total_leads} leads from {output.platforms_searched}",
                count=output.total_leads,
                success=True
            )

            # Log each lead found
            for lead_data in state.leads:
                self.logger.log_lead_found(lead_data)

            self.emit_event("agent_completed", f"Found {output.total_leads} leads")
            self.emit_event("thought", output.summary)

            self.logger.log_phase("Orchestrator Agent Execution", status="completed")
            return state

        except Exception as e:
            state.error = str(e)
            self.logger.log_error("orchestrator_error", str(e))
            self.emit_event("error", f"Orchestrator Agent failed: {str(e)}")
            return state

    @router(run_orchestrator)
    def check_results(self, state: ProspectingState):
        """Route based on result quality."""
        if state.error:
            if state.retries < 2:
                return "retry"
            else:
                return "failed"

        qualified_count = len([l for l in state.leads if l.get('intent_score', 0) >= 60])
        target_half = state.target_leads * 0.5

        if qualified_count >= target_half:
            return "success"
        elif state.retries < 2:
            return "retry"
        else:
            return "partial"

    @listen("retry")
    def retry_with_new_strategy(self, state: ProspectingState):
        """Retry with alternative strategy if results are insufficient."""
        state.retries += 1
        current_qualified = len([l for l in state.leads if l.get('intent_score', 0) >= 60])

        self.emit_event("thought", f"Retry {state.retries}: Only {current_qualified} qualified leads found")

        # Switch strategy based on what was used
        old_strategy = state.current_strategy or "auto"
        if "intent_signals" in state.strategies_used:
            state.current_strategy = "company_triggers"
            self.emit_event("thought", "Switching to company trigger approach")
        else:
            state.current_strategy = "intent_signals"
            self.emit_event("thought", "Switching to intent signals approach")

        # Log the retry
        self.logger.log_retry(
            reason=f"Only {current_qualified} qualified leads found (target: {state.target_leads})",
            new_strategy=f"Switching from {old_strategy} to {state.current_strategy}"
        )

        # Re-run orchestrator
        return self.run_orchestrator(state)

    @listen("success")
    def finalize_success(self, state: ProspectingState):
        """Complete with full results and export logs/leads."""
        self.logger.log_phase("Finalization")

        qualified_leads = [l for l in state.leads if l.get('intent_score', 0) >= 60]
        hot_leads = [l for l in qualified_leads if l.get('priority') == 'hot' or l.get('intent_score', 0) >= 80]
        warm_leads = [l for l in qualified_leads if l.get('priority') == 'warm' or (60 <= l.get('intent_score', 0) < 80)]

        state.status = ProspectingStatus.COMPLETED
        state.hot_leads = len(hot_leads)
        state.warm_leads = len(warm_leads)

        # Export leads to JSON and CSV
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        json_path = os.path.join(self.output_dir, f"leads_{timestamp}.json")
        csv_path = os.path.join(self.output_dir, f"leads_{timestamp}.csv")
        log_path = os.path.join(self.output_dir, f"agent_run_log_{timestamp}.json")

        export_leads_json(state.leads, json_path, metadata={
            "query": state.product_description,
            "target_leads": state.target_leads,
            "platforms_searched": state.platforms_searched,
            "strategies_used": state.strategies_used
        })
        export_leads_csv(state.leads, csv_path)

        # Print leads table
        print("\n" + format_leads_table(state.leads))

        # Export agent log
        self.logger.print_summary()
        self.logger.export_log(log_path)

        self.emit_event("completed", {
            "total_leads": len(qualified_leads),
            "hot_leads": len(hot_leads),
            "warm_leads": len(warm_leads),
            "platforms": state.platforms_searched,
            "strategies": state.strategies_used,
            "exports": {
                "json": json_path,
                "csv": csv_path,
                "log": log_path
            }
        })

        self.emit_event("thought", f"Success! Found {len(qualified_leads)} qualified leads")
        self.logger.log_phase("Finalization", status="completed")
        return state

    @listen("partial")
    def finalize_partial(self, state: ProspectingState):
        """Complete with partial results after retries exhausted."""
        self.logger.log_phase("Finalization (Partial)")

        qualified_leads = [l for l in state.leads if l.get('intent_score', 0) >= 60]

        state.status = ProspectingStatus.PARTIAL

        # Still export what we have
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        json_path = os.path.join(self.output_dir, f"leads_partial_{timestamp}.json")
        csv_path = os.path.join(self.output_dir, f"leads_partial_{timestamp}.csv")
        log_path = os.path.join(self.output_dir, f"agent_run_log_{timestamp}.json")

        export_leads_json(state.leads, json_path, metadata={
            "query": state.product_description,
            "target_leads": state.target_leads,
            "status": "partial",
            "platforms_searched": state.platforms_searched
        })
        export_leads_csv(state.leads, csv_path)

        # Print leads table
        print("\n" + format_leads_table(state.leads))

        # Export agent log
        self.logger.print_summary()
        self.logger.export_log(log_path)

        self.emit_event("completed", {
            "total_leads": len(qualified_leads),
            "hot_leads": state.hot_leads,
            "warm_leads": state.warm_leads,
            "warning": "Target not reached after retries",
            "platforms": state.platforms_searched,
            "strategies": state.strategies_used,
            "exports": {"json": json_path, "csv": csv_path, "log": log_path}
        })

        self.emit_event("thought", f"Partial success: Found {len(qualified_leads)} leads (target: {state.target_leads})")
        self.logger.log_phase("Finalization (Partial)", status="completed")
        return state

    @listen("failed")
    def finalize_failed(self, state: ProspectingState):
        """Handle complete failure."""
        self.logger.log_phase("Finalization (Failed)")

        state.status = ProspectingStatus.FAILED

        # Still export the log for debugging
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        log_path = os.path.join(self.output_dir, f"agent_run_log_failed_{timestamp}.json")
        self.logger.print_summary()
        self.logger.export_log(log_path)

        self.emit_event("failed", {
            "error": state.error,
            "retries": state.retries,
            "exports": {"log": log_path}
        })

        self.emit_event("thought", f"Failed after {state.retries} retries: {state.error}")
        return state


# Convenience function to run the flow
async def run_prospecting_v2(
    query: str,
    target_leads: int = 100,
    icp_criteria: dict = None,
    event_callback: Callable[[Dict], None] = None,
    output_dir: str = "."
) -> ProspectingState:
    """
    Run the v2 prospecting flow.

    Args:
        query: Product/service description or search query
        target_leads: Target number of leads (default: 100)
        icp_criteria: Optional ICP matching criteria
        event_callback: Optional callback for real-time events
        output_dir: Directory to save logs and exported leads

    Returns:
        ProspectingState with results
    """
    flow = ProspectingFlowV2(event_callback=event_callback, output_dir=output_dir)

    # Initialize state via initial_state dict (CrewAI Flow pattern)
    initial_state = {
        "query": query,
        "product_description": query,
        "target_leads": target_leads,
        "icp_criteria": icp_criteria or {}
    }

    # Run the flow with initial state
    result = await flow.kickoff_async(inputs=initial_state)

    return result


# Test function
if __name__ == "__main__":
    import asyncio

    async def main():
        print("\n" + "=" * 70)
        print("PROSPECTING FLOW V2 TEST")
        print("=" * 70)

        def event_handler(event):
            print(f"[{event['type']}] {event['data']}")

        result = await run_prospecting_v2(
            query="AI design agent that helps startups ship UI faster",
            target_leads=10,
            icp_criteria={
                "titles": ["Founder", "CEO", "Head of Product"],
                "company_size": "1-50"
            },
            event_callback=event_handler
        )

        print("\n" + "=" * 70)
        print("FINAL RESULTS")
        print("=" * 70)
        print(f"Status: {result.status}")
        print(f"Total leads: {len(result.leads)}")
        print(f"Hot leads: {result.hot_leads}")
        print(f"Warm leads: {result.warm_leads}")
        print(f"Platforms: {result.platforms_searched}")
        print(f"Strategies: {result.strategies_used}")
        print("=" * 70)

    asyncio.run(main())
