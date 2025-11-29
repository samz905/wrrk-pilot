"""
Reddit Worker - Python function for Reddit prospecting.

Workflow:
1. reddit_search(query) - Get posts matching queries
2. reddit_score(posts) - Score posts for buying intent
3. reddit_extract(posts) - Extract author info as leads
4. filter_sellers(leads) - Remove sellers/promoters

Returns raw leads for orchestrator to review.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.stepped.reddit_tools import (
    RedditSearchSteppedTool,
    RedditScoreTool,
    RedditExtractTool
)
from tools.stepped.filter_sellers import FilterSellersTool


@dataclass
class WorkerResult:
    """Result from a worker step or full execution."""
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    step: str = ""
    step_number: int = 0
    leads_count: int = 0
    trace: List[str] = field(default_factory=list)


class RedditWorker:
    """
    Reddit prospecting worker.

    Executes the Reddit workflow step by step:
    1. Search Reddit for posts
    2. Score posts for intent
    3. Extract leads from high-scoring posts
    4. Filter out sellers

    Each step can be reviewed by the orchestrator before proceeding.
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize Reddit worker.

        Args:
            log_callback: Optional callback for logging (level, message)
        """
        self.log_callback = log_callback or self._default_log

        # Initialize tools
        self.search_tool = RedditSearchSteppedTool()
        self.score_tool = RedditScoreTool()
        self.extract_tool = RedditExtractTool()
        self.filter_tool = FilterSellersTool()

        self.trace: List[str] = []

    def _default_log(self, level: str, message: str):
        """Default logging to stdout."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [REDDIT] [{level}] {message}")

    def _log(self, level: str, message: str):
        """Log a message."""
        self.trace.append(f"[{level}] {message}")
        self.log_callback(level, message)

    def run(self, queries: List[str], target_leads: int = 20) -> WorkerResult:
        """
        Execute full Reddit workflow.

        Args:
            queries: List of search queries from strategy plan
            target_leads: Target number of leads to find

        Returns:
            WorkerResult with leads or error
        """
        self._log("START", f"Reddit worker started with {len(queries)} queries, target: {target_leads}")
        self.trace = []

        all_leads = []

        for query in queries:
            # Step 1: Search
            step1_result = self.step_search(query)
            if not step1_result.success:
                self._log("ERROR", f"Search failed for '{query}': {step1_result.error}")
                continue

            posts = step1_result.data
            if not posts:
                self._log("WARNING", f"No posts found for '{query}'")
                continue

            self._log("STEP", f"Search returned {len(posts)} posts")

            # Step 2: Score (pass query for context)
            step2_result = self.step_score(posts, query)
            if not step2_result.success:
                self._log("ERROR", f"Scoring failed: {step2_result.error}")
                continue

            scored_posts = step2_result.data
            high_intent = [p for p in scored_posts if p.get('intent_score', 0) >= 50]
            self._log("STEP", f"Scored {len(scored_posts)} posts, {len(high_intent)} with score >= 50")

            if not high_intent:
                self._log("WARNING", f"No high-intent posts for '{query}'")
                continue

            # Step 3: Extract
            step3_result = self.step_extract(high_intent)
            if not step3_result.success:
                self._log("ERROR", f"Extraction failed: {step3_result.error}")
                continue

            leads = step3_result.data
            self._log("STEP", f"Extracted {len(leads)} leads")

            # Step 4: Filter sellers
            step4_result = self.step_filter_sellers(leads)
            if not step4_result.success:
                self._log("ERROR", f"Filter failed: {step4_result.error}")
                # Use unfiltered leads
                all_leads.extend(leads)
            else:
                buyer_leads = step4_result.data
                self._log("STEP", f"Filtered to {len(buyer_leads)} buyer leads")
                all_leads.extend(buyer_leads)

            # Check if we have enough leads
            if len(all_leads) >= target_leads:
                self._log("INFO", f"Target reached: {len(all_leads)} leads")
                break

        self._log("COMPLETE", f"Reddit worker finished with {len(all_leads)} leads")

        return WorkerResult(
            success=len(all_leads) > 0,
            data=all_leads,
            error=None if all_leads else "No leads found",
            step="complete",
            step_number=4,
            leads_count=len(all_leads),
            trace=self.trace.copy()
        )

    def step_search(self, query: str, limit: int = 50) -> WorkerResult:
        """
        Step 1: Search Reddit for posts.

        Args:
            query: Search query
            limit: Maximum posts to return

        Returns:
            WorkerResult with posts data
        """
        self._log("STEP", f"Searching Reddit for: '{query}'")

        try:
            result = self.search_tool._run(query=query, limit=limit, time_filter="month")
            data = json.loads(result) if isinstance(result, str) else result

            posts = data.get('posts', [])
            quality = data.get('quality', 'UNKNOWN')

            return WorkerResult(
                success=True,
                data=posts,
                step="search",
                step_number=1,
                trace=[f"Search returned {len(posts)} posts, quality: {quality}"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="search",
                step_number=1
            )

    def step_score(self, posts: List[Dict], query: str) -> WorkerResult:
        """
        Step 2: Score posts for buying intent.

        Args:
            posts: List of posts from search
            query: Original search query for context

        Returns:
            WorkerResult with scored posts
        """
        self._log("STEP", f"Scoring {len(posts)} posts for intent")

        try:
            result = self.score_tool._run(posts=posts, query=query)
            data = json.loads(result) if isinstance(result, str) else result

            scored_posts = data.get('scored_posts', data.get('posts', []))

            return WorkerResult(
                success=True,
                data=scored_posts,
                step="score",
                step_number=2,
                trace=[f"Scored {len(scored_posts)} posts"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="score",
                step_number=2
            )

    def step_extract(self, posts: List[Dict]) -> WorkerResult:
        """
        Step 3: Extract leads from high-scoring posts.

        Args:
            posts: List of scored posts (score >= 50)

        Returns:
            WorkerResult with extracted leads
        """
        self._log("STEP", f"Extracting leads from {len(posts)} posts")

        try:
            result = self.extract_tool._run(posts=posts)
            data = json.loads(result) if isinstance(result, str) else result

            leads = data.get('leads', [])

            # Add source platform to each lead
            for lead in leads:
                lead['source_platform'] = 'reddit'

            return WorkerResult(
                success=True,
                data=leads,
                step="extract",
                step_number=3,
                leads_count=len(leads),
                trace=[f"Extracted {len(leads)} leads"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="extract",
                step_number=3
            )

    def step_filter_sellers(self, leads: List[Dict]) -> WorkerResult:
        """
        Step 4: Filter out sellers/promoters.

        Args:
            leads: List of extracted leads

        Returns:
            WorkerResult with buyer leads only
        """
        self._log("STEP", f"Filtering {len(leads)} leads for sellers")

        try:
            result = self.filter_tool._run(leads=leads)
            data = json.loads(result) if isinstance(result, str) else result

            buyer_leads = data.get('buyer_leads', data.get('leads', []))
            sellers_removed = data.get('sellers_removed', 0)

            return WorkerResult(
                success=True,
                data=buyer_leads,
                step="filter",
                step_number=4,
                leads_count=len(buyer_leads),
                trace=[f"Filtered to {len(buyer_leads)} buyers, removed {sellers_removed} sellers"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="filter",
                step_number=4
            )


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("REDDIT WORKER TEST")
    print("=" * 70)

    worker = RedditWorker()
    result = worker.run(
        queries=["CRM software recommendations", "alternative to Salesforce"],
        target_leads=10
    )

    print(f"\nResult: success={result.success}, leads={result.leads_count}")
    print(f"Error: {result.error}")
    print(f"\nTrace:")
    for line in result.trace:
        print(f"  {line}")
