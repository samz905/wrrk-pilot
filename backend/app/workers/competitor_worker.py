"""
Competitor Worker - Python function for competitor displacement prospecting.

Workflow:
1. competitor_identify(product, competitors) - Get competitor LinkedIn URLs
2. competitor_scrape(urls) - Scrape post engagers from competitor pages
3. filter_sellers(leads) - Remove sellers/competitor employees

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

from tools.stepped.competitor_tools import (
    CompetitorIdentifyTool,
    CompetitorScrapeTool
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
    competitors_scraped: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)


class CompetitorWorker:
    """
    Competitor displacement prospecting worker.

    Executes the competitor workflow step by step:
    1. Identify competitor LinkedIn company pages
    2. Scrape recent post engagers (commenters, likers)
    3. Filter out sellers and competitor employees

    People engaging with competitors = interested in this space.
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize Competitor worker.

        Args:
            log_callback: Optional callback for logging (level, message)
        """
        self.log_callback = log_callback or self._default_log

        # Initialize tools
        self.identify_tool = CompetitorIdentifyTool()
        self.scrape_tool = CompetitorScrapeTool()
        self.filter_tool = FilterSellersTool()

        self.trace: List[str] = []

    def _default_log(self, level: str, message: str):
        """Default logging to stdout."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [COMPETITOR] [{level}] {message}")

    def _log(self, level: str, message: str):
        """Log a message."""
        self.trace.append(f"[{level}] {message}")
        self.log_callback(level, message)

    def run(self, competitors: List[str], product_description: str, target_leads: int = 20) -> WorkerResult:
        """
        Execute full Competitor workflow.

        Args:
            competitors: List of competitor names from strategy plan
            product_description: Product description for context
            target_leads: Target number of leads to find

        Returns:
            WorkerResult with leads or error
        """
        self._log("START", f"Competitor worker started: {len(competitors)} competitors, target={target_leads}")
        self.trace = []

        if not competitors:
            self._log("ERROR", "No competitors provided")
            return WorkerResult(
                success=False,
                error="No competitors provided in strategy",
                step="identify",
                step_number=1,
                trace=self.trace.copy()
            )

        # Step 1: Identify competitor LinkedIn URLs
        step1_result = self.step_identify_competitors(product_description, competitors)
        if not step1_result.success:
            self._log("ERROR", f"Identification failed: {step1_result.error}")
            return WorkerResult(
                success=False,
                error=step1_result.error,
                step="identify",
                step_number=1,
                trace=self.trace.copy()
            )

        competitor_urls = step1_result.data
        if not competitor_urls:
            self._log("ERROR", "No competitor URLs found")
            return WorkerResult(
                success=False,
                error="Could not find LinkedIn pages for competitors",
                step="identify",
                step_number=1,
                trace=self.trace.copy()
            )

        self._log("STEP", f"Found {len(competitor_urls)} competitor LinkedIn URLs")

        # Step 2: Scrape post engagers
        step2_result = self.step_scrape_engagers(competitor_urls)
        if not step2_result.success:
            self._log("ERROR", f"Scraping failed: {step2_result.error}")
            return WorkerResult(
                success=False,
                error=step2_result.error,
                step="scrape",
                step_number=2,
                competitors_scraped=step1_result.competitors_scraped,
                trace=self.trace.copy()
            )

        leads = step2_result.data
        if not leads:
            self._log("WARNING", "No engagers found from competitor posts")
            return WorkerResult(
                success=False,
                error="No engagers found on competitor LinkedIn posts",
                step="scrape",
                step_number=2,
                competitors_scraped=step1_result.competitors_scraped,
                trace=self.trace.copy()
            )

        self._log("STEP", f"Scraped {len(leads)} engagers")

        # Step 3: Filter sellers
        step3_result = self.step_filter_sellers(leads)
        if not step3_result.success:
            self._log("WARNING", f"Filter failed: {step3_result.error}")
            # Use unfiltered leads
            final_leads = leads
        else:
            final_leads = step3_result.data
            self._log("STEP", f"Filtered to {len(final_leads)} buyer leads")

        self._log("COMPLETE", f"Competitor worker finished with {len(final_leads)} leads")

        return WorkerResult(
            success=len(final_leads) > 0,
            data=final_leads,
            error=None if final_leads else "No leads after filtering",
            step="complete",
            step_number=3,
            leads_count=len(final_leads),
            competitors_scraped=step1_result.competitors_scraped,
            trace=self.trace.copy()
        )

    def step_identify_competitors(self, product_description: str, competitors: List[str]) -> WorkerResult:
        """
        Step 1: Identify competitor LinkedIn company page URLs.

        Args:
            product_description: Product context
            competitors: List of competitor names

        Returns:
            WorkerResult with competitor URLs
        """
        self._log("STEP", f"Identifying LinkedIn URLs for {len(competitors)} competitors")

        try:
            result = self.identify_tool._run(
                product_description=product_description,
                competitors=competitors
            )
            data = json.loads(result) if isinstance(result, str) else result

            urls = data.get('competitor_urls', data.get('urls', []))
            found_competitors = data.get('competitors_found', competitors[:len(urls)])

            return WorkerResult(
                success=len(urls) > 0,
                data=urls,
                step="identify",
                step_number=1,
                competitors_scraped=found_competitors,
                trace=[f"Found {len(urls)} competitor URLs"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="identify",
                step_number=1
            )

    def step_scrape_engagers(self, competitor_urls: List[str]) -> WorkerResult:
        """
        Step 2: Scrape engagers from competitor LinkedIn posts.

        Args:
            competitor_urls: List of LinkedIn company page URLs

        Returns:
            WorkerResult with engager leads
        """
        self._log("STEP", f"Scraping engagers from {len(competitor_urls)} competitor pages")

        try:
            result = self.scrape_tool._run(competitor_urls=competitor_urls)
            data = json.loads(result) if isinstance(result, str) else result

            leads = data.get('leads', data.get('engagers', []))

            # Ensure each lead has proper source platform
            for lead in leads:
                lead['source_platform'] = 'linkedin'
                if not lead.get('intent_signal'):
                    competitor = lead.get('competitor_engaged', 'competitor')
                    lead['intent_signal'] = f"Engaged with {competitor} LinkedIn post"

            return WorkerResult(
                success=True,
                data=leads,
                step="scrape",
                step_number=2,
                leads_count=len(leads),
                trace=[f"Scraped {len(leads)} engagers from competitor posts"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="scrape",
                step_number=2
            )

    def step_filter_sellers(self, leads: List[Dict]) -> WorkerResult:
        """
        Step 3: Filter out sellers and competitor employees.

        Args:
            leads: List of engager leads

        Returns:
            WorkerResult with buyer leads only
        """
        self._log("STEP", f"Filtering {len(leads)} leads for sellers/employees")

        try:
            result = self.filter_tool._run(leads=leads)
            data = json.loads(result) if isinstance(result, str) else result

            buyer_leads = data.get('buyer_leads', data.get('leads', []))
            sellers_removed = data.get('sellers_removed', 0)

            return WorkerResult(
                success=True,
                data=buyer_leads,
                step="filter",
                step_number=3,
                leads_count=len(buyer_leads),
                trace=[f"Filtered to {len(buyer_leads)} buyers, removed {sellers_removed} sellers/employees"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="filter",
                step_number=3
            )


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("COMPETITOR WORKER TEST")
    print("=" * 70)

    worker = CompetitorWorker()
    result = worker.run(
        competitors=["Salesforce", "HubSpot", "Pipedrive"],
        product_description="CRM software for sales teams",
        target_leads=10
    )

    print(f"\nResult: success={result.success}, leads={result.leads_count}")
    print(f"Competitors scraped: {result.competitors_scraped}")
    print(f"Error: {result.error}")
    print(f"\nTrace:")
    for line in result.trace:
        print(f"  {line}")
