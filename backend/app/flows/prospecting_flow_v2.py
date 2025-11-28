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
import io
import re
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, listen, start, router
from enum import Enum
from contextlib import redirect_stdout

# Import orchestrator crew
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crews.orchestrator.crew import OrchestratorCrew, ProspectingOutput, Lead, LeadPriority
from utils.agent_logger import AgentLogger
from utils.lead_exporter import export_leads_json, export_leads_csv, format_leads_table


class ReasoningCapture:
    """Capture and format agent reasoning from CrewAI verbose output."""

    def __init__(self):
        self.reasoning_lines: List[str] = []
        self.tool_calls: List[Dict] = []

    def parse_output(self, output: str) -> None:
        """Parse CrewAI verbose output to extract reasoning."""
        lines = output.split('\n')

        for line in lines:
            # Skip empty lines and ANSI escape codes
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            if not clean_line:
                continue

            # === AGENT THINKING (most important!) ===
            # CrewAI outputs "Thought: ..." when agent reasons
            if 'Thought:' in clean_line:
                # Extract just the thought content
                thought = clean_line.split('Thought:', 1)[-1].strip()
                # Handle double "Thought: Thought:" pattern
                if thought.startswith('Thought:'):
                    thought = thought.split('Thought:', 1)[-1].strip()
                if thought:
                    self.reasoning_lines.append(f"[THINKING] {thought}")

            # === TOOL USAGE ===
            elif 'Using Tool:' in clean_line:
                tool = clean_line.split('Using Tool:', 1)[-1].strip()
                self.reasoning_lines.append(f"[TOOL] {tool}")

            elif 'Tool Usage Failed' in clean_line or 'Tool Error' in clean_line:
                self.reasoning_lines.append(f"[ERROR] {clean_line}")

            # === AGENT STATUS ===
            elif 'Agent Started' in clean_line or 'Agent:' in clean_line:
                self.reasoning_lines.append(f"[AGENT] {clean_line}")

            # Capture planning/reasoning
            elif 'Planning' in clean_line or 'plan' in clean_line.lower():
                self.reasoning_lines.append(f"[PLANNING] {clean_line}")
            elif '[INFO]' in clean_line:
                # Tool usage info
                self.reasoning_lines.append(f"[ACTION] {clean_line.replace('[INFO]', '').strip()}")
            elif '[OK]' in clean_line:
                self.reasoning_lines.append(f"[RESULT] {clean_line.replace('[OK]', '').strip()}")
            elif 'Searching' in clean_line or 'Reddit' in clean_line or 'Google' in clean_line:
                self.reasoning_lines.append(f"[SEARCH] {clean_line}")
            elif 'Found' in clean_line:
                self.reasoning_lines.append(f"[FOUND] {clean_line}")

    def get_formatted_log(self) -> str:
        """Return formatted reasoning log as readable text."""
        output = []
        output.append("=" * 80)
        output.append("AGENT REASONING TRACE")
        output.append("=" * 80)
        output.append("")

        for line in self.reasoning_lines:
            output.append(line)

        output.append("")
        output.append("=" * 80)
        return "\n".join(output)


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
        self.reasoning_capture = ReasoningCapture()
        self.raw_output_capture = []  # Capture all stdout for reasoning trace

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

    def _merge_leads(self, existing_leads: List[Dict], new_leads: List[Dict]) -> List[Dict]:
        """Merge new leads with existing, avoiding duplicates by username."""
        seen = set()
        merged = []

        # First add existing leads
        for lead in existing_leads:
            key = lead.get('username', lead.get('name', ''))
            if key and key not in seen:
                seen.add(key)
                merged.append(lead)
            elif not key:
                merged.append(lead)

        # Then add new leads that aren't duplicates
        for lead in new_leads:
            key = lead.get('username', lead.get('name', ''))
            if key and key not in seen:
                seen.add(key)
                merged.append(lead)
            elif not key:
                merged.append(lead)

        return merged

    def _build_reasoning_trace(self, state: ProspectingState, leads: List[Dict]) -> str:
        """Build a human-readable reasoning trace for review."""
        lines = []
        lines.append("=" * 80)
        lines.append("PROSPECTING AGENT - EXECUTION TRACE")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Query: {state.product_description}")
        lines.append(f"Target: {state.target_leads} leads")
        lines.append(f"ICP: {state.icp_criteria}")
        lines.append("")

        # Add captured reasoning from agent
        lines.append("-" * 80)
        lines.append("AGENT REASONING & ACTIONS")
        lines.append("-" * 80)
        for line in self.reasoning_capture.reasoning_lines:
            lines.append(line)

        lines.append("")
        lines.append("-" * 80)
        lines.append("RESULTS SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Platforms searched: {', '.join(state.platforms_searched)}")
        lines.append(f"Strategies used: {', '.join(state.strategies_used)}")
        lines.append(f"Total leads found: {len(leads)}")
        lines.append(f"Hot leads (score >= 80): {len([l for l in leads if l.get('intent_score', 0) >= 80])}")
        lines.append(f"Warm leads (score 60-79): {len([l for l in leads if 60 <= l.get('intent_score', 0) < 80])}")
        lines.append("")

        # Add lead details
        lines.append("-" * 80)
        lines.append("LEADS FOUND")
        lines.append("-" * 80)
        for i, lead in enumerate(leads, 1):
            lines.append("")
            lines.append(f"Lead #{i}: {lead.get('name', 'Unknown')}")
            lines.append(f"  Title: {lead.get('title', 'N/A')}")
            lines.append(f"  Company: {lead.get('company', 'N/A')}")
            lines.append(f"  Platform: {lead.get('source_platform', 'unknown')}")
            lines.append(f"  Score: {lead.get('intent_score', 0)} ({lead.get('priority', 'unknown').upper()})")
            lines.append(f"  Intent Signal: {lead.get('intent_signal', 'N/A')}")
            lines.append(f"  Scoring Reasoning: {lead.get('scoring_reasoning', 'N/A')}")
            lines.append(f"  Source: {lead.get('source_url', 'N/A')}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF TRACE")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _execute_orchestrator(self, state: ProspectingState) -> bool:
        """Execute the orchestrator crew once. Returns True on success."""
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
            # Capture stdout during execution to get reasoning trace
            import sys
            from io import StringIO

            class TeeOutput:
                """Capture output while still printing to console."""
                def __init__(self, original):
                    self.original = original
                    self.captured = StringIO()

                def write(self, text):
                    self.original.write(text)
                    self.captured.write(text)

                def flush(self):
                    self.original.flush()

            # Capture stdout
            tee = TeeOutput(sys.stdout)
            old_stdout = sys.stdout
            sys.stdout = tee

            try:
                # Execute orchestrator crew
                result = self.orchestrator_crew.crew().kickoff(inputs={
                    "product_description": state.product_description,
                    "target_leads": state.target_leads,
                    "icp_criteria": state.icp_criteria
                })
            finally:
                # Restore stdout and capture the output
                sys.stdout = old_stdout
                captured_output = tee.captured.getvalue()
                self.raw_output_capture.append(captured_output)
                self.reasoning_capture.parse_output(captured_output)

            # Parse structured output
            output: ProspectingOutput = result.pydantic

            # MERGE new leads with existing (don't overwrite!)
            new_leads = [lead.model_dump() for lead in output.leads]
            state.leads = self._merge_leads(state.leads, new_leads)

            # Update other state
            state.hot_leads = len([l for l in state.leads if l.get('intent_score', 0) >= 80])
            state.warm_leads = len([l for l in state.leads if 60 <= l.get('intent_score', 0) < 80])

            # Merge platforms and strategies
            for platform in output.platforms_searched:
                if platform not in state.platforms_searched:
                    state.platforms_searched.append(platform)
            for strategy in output.strategies_used:
                if strategy not in state.strategies_used:
                    state.strategies_used.append(strategy)

            # Log results
            self.logger.log_tool_result(
                "OrchestratorCrew",
                f"Found {len(new_leads)} new leads (total: {len(state.leads)}) from {output.platforms_searched}",
                count=len(new_leads),
                success=True
            )

            # Log each new lead found
            for lead_data in new_leads:
                self.logger.log_lead_found(lead_data)

            self.emit_event("agent_completed", f"Found {len(new_leads)} new leads (total: {len(state.leads)})")
            self.emit_event("thought", output.summary)

            self.logger.log_phase("Orchestrator Agent Execution", status="completed")
            return True

        except Exception as e:
            state.error = str(e)
            self.logger.log_error("orchestrator_error", str(e))
            self.emit_event("error", f"Orchestrator Agent failed: {str(e)}")
            return False

    @listen(initialize)
    def run_orchestrator_with_retries(self, state: ProspectingState):
        """
        Run the Orchestrator Agent with built-in retry logic.

        Handles retries internally to avoid flow routing issues.
        """
        max_retries = 2
        strategies = ["auto", "intent_signals", "company_triggers"]

        while state.retries <= max_retries:
            # Execute orchestrator
            success = self._execute_orchestrator(state)

            if not success:
                # Error occurred
                if state.retries < max_retries:
                    state.retries += 1
                    self.emit_event("thought", f"Retry {state.retries} due to error...")
                    self.logger.log_retry(
                        reason=f"Error: {state.error}",
                        new_strategy=strategies[min(state.retries, len(strategies)-1)]
                    )
                    state.error = ""  # Clear error for retry
                    continue
                else:
                    # Max retries reached with error
                    return "failed"

            # Check if we have enough leads
            qualified_count = len([l for l in state.leads if l.get('intent_score', 0) >= 60])
            target_half = state.target_leads * 0.5

            self.emit_event("thought", f"Progress: {qualified_count} qualified leads (target: {state.target_leads}, need {int(target_half)})")

            if qualified_count >= target_half:
                return "success"

            # Not enough leads - retry if we can
            if state.retries < max_retries:
                state.retries += 1
                old_strategy = state.current_strategy or "auto"

                # Rotate strategy
                if state.retries < len(strategies):
                    state.current_strategy = strategies[state.retries]
                else:
                    state.current_strategy = strategies[-1]

                self.emit_event("thought", f"Retry {state.retries}: Only {qualified_count} qualified leads found")
                self.emit_event("thought", f"Switching strategy from {old_strategy} to {state.current_strategy}")

                self.logger.log_retry(
                    reason=f"Only {qualified_count} qualified leads found (target: {state.target_leads})",
                    new_strategy=f"Switching from {old_strategy} to {state.current_strategy}"
                )
            else:
                # Max retries reached
                return "partial"

        return "partial"

    @router(run_orchestrator_with_retries)
    def route_to_finalize(self, result: str):
        """Route to appropriate finalization based on result."""
        return result

    @listen("success")
    def finalize_success(self, _route_result):
        """Complete with full results and export logs/leads."""
        state = self.state  # Use self.state instead of parameter
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
        reasoning_path = os.path.join(self.output_dir, f"agent_reasoning_{timestamp}.txt")

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

        # Export reasoning trace to readable txt file
        reasoning_content = self._build_reasoning_trace(state, qualified_leads)
        with open(reasoning_path, 'w', encoding='utf-8') as f:
            f.write(reasoning_content)
        print(f"\n[EXPORT] Reasoning trace saved to {reasoning_path}")

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
    def finalize_partial(self, _route_result):
        """Complete with partial results after retries exhausted."""
        state = self.state  # Use self.state instead of parameter
        self.logger.log_phase("Finalization (Partial)")

        qualified_leads = [l for l in state.leads if l.get('intent_score', 0) >= 60]

        state.status = ProspectingStatus.PARTIAL

        # Still export what we have
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        json_path = os.path.join(self.output_dir, f"leads_partial_{timestamp}.json")
        csv_path = os.path.join(self.output_dir, f"leads_partial_{timestamp}.csv")
        log_path = os.path.join(self.output_dir, f"agent_run_log_{timestamp}.json")
        reasoning_path = os.path.join(self.output_dir, f"agent_reasoning_{timestamp}.txt")

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

        # Export reasoning trace
        reasoning_content = self._build_reasoning_trace(state, qualified_leads)
        with open(reasoning_path, 'w', encoding='utf-8') as f:
            f.write(reasoning_content)
        print(f"\n[EXPORT] Reasoning trace saved to {reasoning_path}")

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
    def finalize_failed(self, _route_result):
        """Handle complete failure."""
        state = self.state  # Use self.state instead of parameter
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
