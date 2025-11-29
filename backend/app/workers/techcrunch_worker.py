"""
TechCrunch Worker - Python function for TechCrunch prospecting.

Workflow:
1. techcrunch_fetch_parallel(pages) - Get funding articles
2. techcrunch_select_articles(articles) - Filter by industry
3. techcrunch_extract_companies(articles) - Get company details
4. techcrunch_serp_decision_makers(companies) - Find founders via SERP

Returns raw leads for orchestrator to review.
TechCrunch leads are pre-qualified (funded = confirmed budget).
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.stepped.techcrunch_tools import (
    TechCrunchFetchParallelTool,
    TechCrunchSelectArticlesTool,
    TechCrunchExtractCompaniesTool,
    TechCrunchSerpDecisionMakersTool
)


@dataclass
class WorkerResult:
    """Result from a worker step or full execution."""
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    step: str = ""
    step_number: int = 0
    leads_count: int = 0
    companies_found: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)


class TechCrunchWorker:
    """
    TechCrunch prospecting worker.

    Executes the TechCrunch workflow step by step:
    1. Fetch funding articles from TechCrunch
    2. Select articles relevant to target industry
    3. Extract company details from articles
    4. Find decision makers via SERP (fast, parallel)

    TechCrunch leads = funded companies = confirmed budget
    No seller filtering needed (these are buyers with money).
    """

    def __init__(self, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize TechCrunch worker.

        Args:
            log_callback: Optional callback for logging (level, message)
        """
        self.log_callback = log_callback or self._default_log

        # Initialize tools
        self.fetch_tool = TechCrunchFetchParallelTool()
        self.select_tool = TechCrunchSelectArticlesTool()
        self.extract_tool = TechCrunchExtractCompaniesTool()
        self.serp_tool = TechCrunchSerpDecisionMakersTool()

        self.trace: List[str] = []

    def _default_log(self, level: str, message: str):
        """Default logging to stdout."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [TECHCRUNCH] [{level}] {message}")

    def _log(self, level: str, message: str):
        """Log a message."""
        self.trace.append(f"[{level}] {message}")
        self.log_callback(level, message)

    def run(self, industry: str, product_context: str, target_leads: int = 20) -> WorkerResult:
        """
        Execute full TechCrunch workflow.

        Args:
            industry: Target industry from strategy plan
            product_context: Product description for role targeting
            target_leads: Target number of leads to find

        Returns:
            WorkerResult with leads or error
        """
        self._log("START", f"TechCrunch worker started: industry={industry}, target={target_leads}")
        self.trace = []

        # Step 1: Fetch articles
        step1_result = self.step_fetch_articles(pages=[1, 2])
        if not step1_result.success:
            self._log("ERROR", f"Fetch failed: {step1_result.error}")
            return WorkerResult(
                success=False,
                error=step1_result.error,
                step="fetch",
                step_number=1,
                trace=self.trace.copy()
            )

        articles = step1_result.data
        if not articles:
            self._log("ERROR", "No articles found")
            return WorkerResult(
                success=False,
                error="No articles found on TechCrunch",
                step="fetch",
                step_number=1,
                trace=self.trace.copy()
            )

        self._log("STEP", f"Fetched {len(articles)} articles")

        # Use product_context as the query for all steps
        query = product_context if product_context else industry

        # Step 2: Select relevant articles
        step2_result = self.step_select_articles(articles, query)
        if not step2_result.success:
            self._log("WARNING", f"Selection failed: {step2_result.error}")
            # Use all articles as fallback
            relevant_articles = articles[:10]
        else:
            relevant_articles = step2_result.data

        if not relevant_articles:
            self._log("WARNING", "No relevant articles, using top 10")
            relevant_articles = articles[:10]

        self._log("STEP", f"Selected {len(relevant_articles)} relevant articles")

        # Step 3: Extract companies
        step3_result = self.step_extract_companies(relevant_articles, query)
        if not step3_result.success:
            self._log("ERROR", f"Company extraction failed: {step3_result.error}")
            return WorkerResult(
                success=False,
                error=step3_result.error,
                step="extract",
                step_number=3,
                trace=self.trace.copy()
            )

        companies = step3_result.data
        if not companies:
            self._log("ERROR", "No companies extracted")
            return WorkerResult(
                success=False,
                error="No companies could be extracted from articles",
                step="extract",
                step_number=3,
                trace=self.trace.copy()
            )

        self._log("STEP", f"Extracted {len(companies)} companies")

        # Step 4: Find decision makers via SERP
        step4_result = self.step_find_decision_makers(companies, query)
        if not step4_result.success:
            self._log("ERROR", f"Decision maker search failed: {step4_result.error}")
            return WorkerResult(
                success=False,
                error=step4_result.error,
                step="serp",
                step_number=4,
                companies_found=[c.get('name', 'Unknown') for c in companies],
                trace=self.trace.copy()
            )

        leads = step4_result.data
        self._log("COMPLETE", f"TechCrunch worker finished with {len(leads)} leads")

        return WorkerResult(
            success=len(leads) > 0,
            data=leads,
            error=None if leads else "No decision makers found",
            step="complete",
            step_number=4,
            leads_count=len(leads),
            companies_found=[c.get('name', 'Unknown') for c in companies],
            trace=self.trace.copy()
        )

    def step_fetch_articles(self, pages: List[int] = [1, 2]) -> WorkerResult:
        """
        Step 1: Fetch funding articles from TechCrunch.

        Args:
            pages: Page numbers to fetch (parallel)

        Returns:
            WorkerResult with articles data
        """
        self._log("STEP", f"Fetching TechCrunch pages {pages}")

        try:
            result = self.fetch_tool._run(pages=pages)
            data = json.loads(result) if isinstance(result, str) else result

            articles = data.get('articles', [])

            return WorkerResult(
                success=True,
                data=articles,
                step="fetch",
                step_number=1,
                trace=[f"Fetched {len(articles)} articles from pages {pages}"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="fetch",
                step_number=1
            )

    def step_select_articles(self, articles: List[Dict], query: str) -> WorkerResult:
        """
        Step 2: Select articles relevant to target industry/query.

        Args:
            articles: List of fetched articles
            query: Target industry or product query from strategy

        Returns:
            WorkerResult with filtered articles
        """
        self._log("STEP", f"Selecting articles for query: {query}")

        try:
            result = self.select_tool._run(articles=articles, query=query)
            data = json.loads(result) if isinstance(result, str) else result

            selected = data.get('selected_articles', data.get('articles', []))

            return WorkerResult(
                success=True,
                data=selected,
                step="select",
                step_number=2,
                trace=[f"Selected {len(selected)} relevant articles"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="select",
                step_number=2
            )

    def step_extract_companies(self, articles: List[Dict], query: str) -> WorkerResult:
        """
        Step 3: Extract company details from articles.

        Args:
            articles: List of selected articles
            query: Product/industry context for extraction

        Returns:
            WorkerResult with company data
        """
        self._log("STEP", f"Extracting companies from {len(articles)} articles")

        try:
            result = self.extract_tool._run(articles=articles, query=query)
            data = json.loads(result) if isinstance(result, str) else result

            companies = data.get('companies', [])

            return WorkerResult(
                success=True,
                data=companies,
                step="extract",
                step_number=3,
                companies_found=[c.get('name', 'Unknown') for c in companies],
                trace=[f"Extracted {len(companies)} companies"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="extract",
                step_number=3
            )

    def step_find_decision_makers(self, companies: List[Dict], query: str) -> WorkerResult:
        """
        Step 4: Find decision makers via SERP (fast, parallel).

        Args:
            companies: List of companies to search
            query: Product context for role targeting

        Returns:
            WorkerResult with decision maker leads
        """
        self._log("STEP", f"Finding decision makers for {len(companies)} companies (SERP)")

        try:
            result = self.serp_tool._run(companies=companies, query=query)
            data = json.loads(result) if isinstance(result, str) else result

            leads = data.get('leads', data.get('decision_makers', []))

            # Ensure each lead has proper source platform and intent signal
            for lead in leads:
                lead['source_platform'] = 'techcrunch'
                if not lead.get('intent_signal'):
                    company = lead.get('company', 'Unknown')
                    funding = lead.get('funding', 'recent funding')
                    lead['intent_signal'] = f"Decision maker at {company} with {funding}"

            return WorkerResult(
                success=True,
                data=leads,
                step="serp",
                step_number=4,
                leads_count=len(leads),
                trace=[f"Found {len(leads)} decision makers via SERP"]
            )

        except Exception as e:
            return WorkerResult(
                success=False,
                error=str(e),
                step="serp",
                step_number=4
            )


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TECHCRUNCH WORKER TEST")
    print("=" * 70)

    worker = TechCrunchWorker()
    result = worker.run(
        industry="SaaS and Technology",
        product_context="CRM software for sales teams",
        target_leads=10
    )

    print(f"\nResult: success={result.success}, leads={result.leads_count}")
    print(f"Companies: {result.companies_found}")
    print(f"Error: {result.error}")
    print(f"\nTrace:")
    for line in result.trace:
        print(f"  {line}")
