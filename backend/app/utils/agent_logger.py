"""Agent Logger - Captures full execution trace for debugging and transparency."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4


class AgentLogger:
    """
    Captures the complete execution trace of the prospecting agent.

    Logs:
    - Agent reasoning and decisions
    - Tool calls with inputs
    - Tool results with summaries
    - Retries and adaptations
    - Lead extraction results

    Usage:
        logger = AgentLogger(run_id="prospecting-2024-01-01")
        logger.log_reasoning("Starting with Reddit search for design tools")
        logger.log_tool_call("Reddit Discussion Search", {"query": "design tools"})
        logger.log_tool_result("Reddit Discussion Search", "Found 30 posts", count=30)
        logger.log_lead_found({"username": "john_doe", "intent_score": 85})
        logger.export_log("agent_run_log.json")
    """

    def __init__(self, run_id: Optional[str] = None):
        """Initialize the agent logger.

        Args:
            run_id: Unique identifier for this run. Auto-generated if not provided.
        """
        self.run_id = run_id or f"run-{uuid4().hex[:8]}"
        self.start_time = datetime.now()
        self.logs: List[Dict] = []
        self.leads_found: List[Dict] = []
        self.tools_used: Dict[str, int] = {}  # Track tool usage counts
        self.errors: List[Dict] = []

        # Add initial log entry
        self._log("run_start", {
            "run_id": self.run_id,
            "started_at": self.start_time.isoformat()
        })

    def _log(self, log_type: str, content: Dict[str, Any]) -> None:
        """Internal method to add a log entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds(),
            "type": log_type,
            **content
        }
        self.logs.append(entry)

    def log_reasoning(self, thought: str, context: Optional[str] = None) -> None:
        """Log agent reasoning or decision-making.

        Args:
            thought: The agent's reasoning or decision
            context: Optional additional context
        """
        self._log("reasoning", {
            "thought": thought,
            "context": context
        })
        print(f"[REASONING] {thought}")

    def log_tool_call(self, tool_name: str, inputs: Dict[str, Any]) -> None:
        """Log when a tool is called.

        Args:
            tool_name: Name of the tool being called
            inputs: Input parameters for the tool
        """
        # Track tool usage
        self.tools_used[tool_name] = self.tools_used.get(tool_name, 0) + 1

        self._log("tool_call", {
            "tool": tool_name,
            "inputs": inputs,
            "call_number": self.tools_used[tool_name]
        })
        print(f"[TOOL CALL] {tool_name}: {json.dumps(inputs, default=str)[:200]}...")

    def log_tool_result(
        self,
        tool_name: str,
        result_summary: str,
        count: Optional[int] = None,
        success: bool = True
    ) -> None:
        """Log the result of a tool call.

        Args:
            tool_name: Name of the tool
            result_summary: Brief summary of what was found/achieved
            count: Optional count of items found/processed
            success: Whether the tool call was successful
        """
        self._log("tool_result", {
            "tool": tool_name,
            "summary": result_summary,
            "count": count,
            "success": success
        })

        status = "OK" if success else "FAILED"
        count_str = f" ({count} items)" if count is not None else ""
        print(f"[TOOL RESULT] [{status}] {tool_name}: {result_summary}{count_str}")

    def log_retry(self, reason: str, new_strategy: str) -> None:
        """Log when the agent retries with a different strategy.

        Args:
            reason: Why the previous attempt failed
            new_strategy: What the agent will try next
        """
        self._log("retry", {
            "reason": reason,
            "new_strategy": new_strategy
        })
        print(f"[RETRY] Reason: {reason}")
        print(f"[RETRY] New strategy: {new_strategy}")

    def log_lead_found(self, lead: Dict[str, Any]) -> None:
        """Log when a lead is found.

        Args:
            lead: Lead data dictionary
        """
        self.leads_found.append(lead)

        self._log("lead_found", {
            "lead_number": len(self.leads_found),
            "username": lead.get("username", "Unknown"),
            "intent_score": lead.get("intent_score", 0),
            "platform": lead.get("source_platform", lead.get("platform", "unknown")),
            "user_type": lead.get("user_type", "unknown")
        })

        score = lead.get("intent_score", 0)
        name = lead.get("username", lead.get("name", "Unknown"))
        print(f"[LEAD #{len(self.leads_found)}] {name} (Score: {score})")

    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None) -> None:
        """Log an error that occurred.

        Args:
            error_type: Type of error (e.g., "api_error", "parsing_error")
            message: Error message
            details: Optional additional details
        """
        error_entry = {
            "type": error_type,
            "message": message,
            "details": details
        }
        self.errors.append(error_entry)

        self._log("error", error_entry)
        print(f"[ERROR] {error_type}: {message}")

    def log_phase(self, phase_name: str, status: str = "started") -> None:
        """Log a major phase transition.

        Args:
            phase_name: Name of the phase
            status: "started" or "completed"
        """
        self._log("phase", {
            "phase": phase_name,
            "status": status
        })
        print(f"\n{'='*60}")
        print(f"[PHASE] {phase_name.upper()} - {status.upper()}")
        print(f"{'='*60}\n")

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the run."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        # Count lead priorities
        hot_leads = sum(1 for l in self.leads_found if l.get("intent_score", 0) >= 80)
        warm_leads = sum(1 for l in self.leads_found if 60 <= l.get("intent_score", 0) < 80)
        cold_leads = sum(1 for l in self.leads_found if l.get("intent_score", 0) < 60)

        # Count by platform
        platforms = {}
        for lead in self.leads_found:
            platform = lead.get("source_platform", lead.get("platform", "unknown"))
            platforms[platform] = platforms.get(platform, 0) + 1

        return {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "total_leads": len(self.leads_found),
            "hot_leads": hot_leads,
            "warm_leads": warm_leads,
            "cold_leads": cold_leads,
            "leads_by_platform": platforms,
            "tools_used": self.tools_used,
            "total_tool_calls": sum(self.tools_used.values()),
            "errors_count": len(self.errors),
            "log_entries_count": len(self.logs)
        }

    def export_log(self, filepath: str) -> str:
        """Export the complete log to a JSON file.

        Args:
            filepath: Path to save the log file

        Returns:
            The filepath where the log was saved
        """
        output = {
            "summary": self.get_summary(),
            "logs": self.logs,
            "leads": self.leads_found,
            "errors": self.errors
        }

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n[LOG EXPORTED] {filepath}")
        return filepath

    def print_summary(self) -> None:
        """Print a summary of the run to console."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("AGENT RUN SUMMARY")
        print("="*60)
        print(f"Run ID: {summary['run_id']}")
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"\nLeads Found: {summary['total_leads']}")
        print(f"  - Hot (80+):  {summary['hot_leads']}")
        print(f"  - Warm (60-79): {summary['warm_leads']}")
        print(f"  - Cold (<60): {summary['cold_leads']}")
        print(f"\nLeads by Platform:")
        for platform, count in summary['leads_by_platform'].items():
            print(f"  - {platform}: {count}")
        print(f"\nTools Used: {summary['total_tool_calls']} calls")
        for tool, count in summary['tools_used'].items():
            print(f"  - {tool}: {count}")
        print(f"\nErrors: {summary['errors_count']}")
        print("="*60)
