"""
Apify Cost Tracking Utility

Tracks costs across Apify actor runs for a prospecting job.
Costs are accumulated and can be saved to the database when the job completes.
"""

import os
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from apify_client import ApifyClient


@dataclass
class CostTracker:
    """Thread-safe cost tracker for a single prospecting job."""

    job_id: str
    total_cost_usd: float = 0.0
    actor_costs: Dict[str, float] = field(default_factory=dict)
    run_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add_cost(self, actor_id: str, cost_usd: float) -> None:
        """Add cost from an Apify actor run."""
        with self._lock:
            self.total_cost_usd += cost_usd
            self.run_count += 1
            if actor_id not in self.actor_costs:
                self.actor_costs[actor_id] = 0.0
            self.actor_costs[actor_id] += cost_usd

    def get_summary(self) -> Dict[str, Any]:
        """Get cost summary."""
        with self._lock:
            return {
                "job_id": self.job_id,
                "total_cost_usd": round(self.total_cost_usd, 6),
                "run_count": self.run_count,
                "by_actor": {k: round(v, 6) for k, v in self.actor_costs.items()}
            }


# Global registry of active cost trackers (job_id -> CostTracker)
_active_trackers: Dict[str, CostTracker] = {}
_registry_lock = threading.Lock()


def get_tracker(job_id: str) -> CostTracker:
    """Get or create a cost tracker for a job."""
    with _registry_lock:
        if job_id not in _active_trackers:
            _active_trackers[job_id] = CostTracker(job_id=job_id)
        return _active_trackers[job_id]


def remove_tracker(job_id: str) -> Optional[CostTracker]:
    """Remove and return a cost tracker (call when job completes)."""
    with _registry_lock:
        return _active_trackers.pop(job_id, None)


def run_actor_with_cost_tracking(
    actor_id: str,
    run_input: Dict[str, Any],
    job_id: Optional[str] = None,
    apify_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run an Apify actor and track its cost.

    Args:
        actor_id: The Apify actor ID (e.g., "TwqHBuZZPHJxiQrTU" or "username/actor-name")
        run_input: Input parameters for the actor
        job_id: Optional job ID for cost tracking (if None, cost is not tracked)
        apify_token: Optional Apify token (uses env var if not provided)

    Returns:
        The run result dict from Apify (includes defaultDatasetId, status, etc.)
    """
    token = apify_token or os.getenv("APIFY_API_TOKEN")
    if not token:
        raise ValueError("APIFY_API_TOKEN not found")

    client = ApifyClient(token)

    # Run the actor
    run = client.actor(actor_id).call(run_input=run_input)

    # Extract cost from the run
    cost_usd = 0.0

    # Try to get usageTotalUsd directly
    if "usageTotalUsd" in run:
        cost_usd = float(run["usageTotalUsd"])
    elif "usage" in run:
        # Fallback: calculate from compute units (~$0.40 per CU)
        usage = run["usage"]
        compute_units = usage.get("ACTOR_COMPUTE_UNITS", 0)
        cost_usd = compute_units * 0.40

    # Track cost if job_id provided
    if job_id and cost_usd > 0:
        tracker = get_tracker(job_id)
        tracker.add_cost(actor_id, cost_usd)
        print(f"[COST] Actor {actor_id}: ${cost_usd:.6f} (Job total: ${tracker.total_cost_usd:.6f})")

    return run


# Actor ID to friendly name mapping
ACTOR_NAMES = {
    "TwqHBuZZPHJxiQrTU": "Reddit Scraper",
    "VhxlqQXRwhW8H5hNV": "LinkedIn Profile Detail",
    "cIdqlEvw6afc1do1p": "LinkedIn Employees",
    "apimaestro/linkedin-companies-search-scraper": "LinkedIn Company Search",
    "apimaestro/linkedin-post-comments-replies-engagements-scraper-no-cookies": "LinkedIn Post Comments",
    "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest": "Twitter Scraper",
    "harvestapi/linkedin-company-posts": "LinkedIn Company Posts",
    "curious_coder/crunchbase-scraper": "Crunchbase Scraper",
}


def get_actor_name(actor_id: str) -> str:
    """Get friendly name for an actor."""
    return ACTOR_NAMES.get(actor_id, actor_id)


def track_apify_cost(actor_id: str, run_result: Dict[str, Any]) -> float:
    """
    Track cost from an Apify run result.

    Call this after each client.actor(...).call() to track costs.
    Uses CURRENT_JOB_ID environment variable to find the tracker.

    Args:
        actor_id: The Apify actor ID
        run_result: The run result dict from Apify

    Returns:
        The cost in USD (0 if no tracking or no cost data)
    """
    job_id = os.getenv("CURRENT_JOB_ID")
    if not job_id:
        return 0.0

    # Extract cost from the run
    cost_usd = 0.0

    # Try to get usageTotalUsd directly (pay-per-result actors)
    if run_result.get("usageTotalUsd", 0) > 0:
        cost_usd = float(run_result["usageTotalUsd"])
    # Fallback: check stats.computeUnits (platform compute billing)
    elif "stats" in run_result and run_result["stats"].get("computeUnits", 0) > 0:
        compute_units = run_result["stats"]["computeUnits"]
        cost_usd = compute_units * 0.40  # ~$0.40 per compute unit
    # Fallback: check usage.ACTOR_COMPUTE_UNITS
    elif "usage" in run_result:
        compute_units = run_result["usage"].get("ACTOR_COMPUTE_UNITS", 0)
        cost_usd = compute_units * 0.40

    # Track cost
    if cost_usd > 0:
        tracker = get_tracker(job_id)
        tracker.add_cost(actor_id, cost_usd)
        actor_name = get_actor_name(actor_id)
        print(f"[COST] {actor_name}: ${cost_usd:.6f} (Job total: ${tracker.total_cost_usd:.6f})")

    return cost_usd
