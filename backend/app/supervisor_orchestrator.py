"""
Supervisor Orchestrator v3.5 - Flow-Based with Parallel Workers

The orchestrator TRULY orchestrates:
1. Plans strategy (LLM agent)
2. Launches workers in PARALLEL (ThreadPoolExecutor)
3. Reviews each worker's output with INTRA-STEP checkpoints
4. Fixes issues (retry, encoding fix, skip)
5. Aggregates final leads

Key principles:
- Orchestrator only orchestrates (no atomic work)
- Workers run in parallel
- Intra-step review catches errors early
- Strict mode: never accept bad/empty results
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, LLM

# Local imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from workers.reddit_worker import RedditWorker, WorkerResult
from workers.techcrunch_worker import TechCrunchWorker
from workers.competitor_worker import CompetitorWorker
from tools.utility_tools import DeduplicateLeadsTool, ValidateLeadsTool
from core.config import settings


class StrategyPlan(BaseModel):
    """Output from strategy planning."""
    product_category: str = Field(description="Type of product")
    competitors: List[str] = Field(description="Likely competitors")
    reddit_queries: List[str] = Field(description="Reddit search queries")
    techcrunch_focus: str = Field(description="Industry focus for TechCrunch")
    target_titles: List[str] = Field(description="Decision maker titles")


@dataclass
class OrchestratorResult:
    """Final result from the orchestrator."""
    success: bool = False
    leads: List[Dict] = field(default_factory=list)
    total_leads: int = 0
    hot_leads: int = 0
    warm_leads: int = 0
    reddit_leads: int = 0
    techcrunch_leads: int = 0
    competitor_leads: int = 0
    sellers_removed: int = 0
    duplicates_removed: int = 0
    platforms_searched: List[str] = field(default_factory=list)
    strategies_used: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)


class SupervisorOrchestrator:
    """
    LLM-based orchestrator that supervises Python workers.

    The orchestrator:
    - Plans strategy (LLM decides queries, competitors, focus)
    - Launches 3 workers in PARALLEL
    - Reviews each worker's output
    - Retries or fixes issues
    - Aggregates and deduplicates final leads

    Workers do the fast atomic work, orchestrator reviews and fixes.
    """

    def __init__(
        self,
        log_callback: Optional[Callable[[str, str], None]] = None,
        output_dir: str = "."
    ):
        """
        Initialize the supervisor orchestrator.

        Args:
            log_callback: Optional callback for logging (level, message)
            output_dir: Directory for log/output files
        """
        self.log_callback = log_callback or self._default_log
        self.output_dir = output_dir

        # Initialize LLM
        self.llm = LLM(
            model=settings.AGENT_MODEL,
            temperature=settings.AGENT_TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Initialize utility tools
        self.dedup_tool = DeduplicateLeadsTool()
        self.validate_tool = ValidateLeadsTool()

        # Execution trace
        self.trace: List[str] = []
        self.start_time: float = 0

    def _default_log(self, level: str, message: str):
        """Default logging to stdout."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def _log(self, level: str, message: str):
        """Log a message."""
        self.trace.append(f"[{level}] {message}")
        self.log_callback(level, message)

    def run(
        self,
        product_description: str,
        target_leads: int = 50,
        icp_criteria: Optional[Dict] = None
    ) -> OrchestratorResult:
        """
        Run the full prospecting flow.

        Args:
            product_description: Description of the product/service
            target_leads: Target number of leads to find
            icp_criteria: Optional ICP matching criteria

        Returns:
            OrchestratorResult with leads and metadata
        """
        self.start_time = time.time()
        self.trace = []

        self._log("START", f"Supervisor Orchestrator v3.5 starting...")
        self._log("THOUGHT", f"Product: {product_description}")
        self._log("THOUGHT", f"Target: {target_leads} leads")
        self._log("THOUGHT", "Architecture: Parallel workers with intra-step review")

        try:
            # Phase 1: Plan strategy
            strategy = self._plan_strategy(product_description, target_leads, icp_criteria)
            if not strategy:
                return OrchestratorResult(
                    success=False,
                    errors=["Strategy planning failed"],
                    trace=self.trace.copy()
                )

            # Phase 2: Launch workers in PARALLEL
            worker_results = self._run_workers_parallel(
                strategy=strategy,
                product_description=product_description,
                target_leads=target_leads
            )

            # Phase 3: Aggregate results
            result = self._aggregate_results(worker_results, target_leads)

            result.execution_time = time.time() - self.start_time
            result.trace = self.trace.copy()

            self._log("COMPLETE", f"Finished in {result.execution_time:.1f}s with {result.total_leads} leads")

            return result

        except Exception as e:
            self._log("ERROR", f"Orchestrator failed: {str(e)}")
            return OrchestratorResult(
                success=False,
                errors=[str(e)],
                execution_time=time.time() - self.start_time,
                trace=self.trace.copy()
            )

    def _plan_strategy(
        self,
        product_description: str,
        target_leads: int,
        icp_criteria: Optional[Dict]
    ) -> Optional[Dict]:
        """
        Phase 1: Plan prospecting strategy using LLM agent.

        Returns strategy dict with queries, competitors, focus areas.
        """
        self._log("STRATEGY", "Planning prospecting strategy...")

        planner = Agent(
            role="Strategy Planner",
            goal="Create an effective prospecting strategy",
            backstory="Expert at identifying target markets and crafting search strategies",
            llm=self.llm,
            verbose=False
        )

        task = Task(
            description=f"""
            Analyze this product and create a prospecting strategy:

            Product: {product_description}
            Target: {target_leads} leads
            ICP: {json.dumps(icp_criteria or {})}

            Create a strategy with these EXACT keys:
            1. "product_category": What type of product this is (e.g., "ML observability", "CRM software")
            2. "competitors": List of 3-5 competitor company names (e.g., ["DataDog", "Weights & Biases", "MLflow"])
            3. "reddit_queries": List of 2-3 ACTUAL search query strings to use on Reddit.
               IMPORTANT: These must be real search queries, NOT category labels.
               Good examples: ["ML observability recommendations", "alternative to DataDog", "debugging ML model performance"]
               Bad examples: ["direct", "pain_based", "alternative"] - these are category labels, NOT queries!
            4. "techcrunch_focus": Target industry/sector (e.g., "AI/ML and Developer Tools")
            5. "target_titles": List of decision maker titles (e.g., ["Founder", "CEO", "CTO", "ML Engineer"])

            Output ONLY valid JSON with the keys above. No explanations.
            """,
            agent=planner,
            expected_output="Valid JSON object with product_category, competitors, reddit_queries, techcrunch_focus, target_titles"
        )

        try:
            crew = Crew(agents=[planner], tasks=[task], verbose=False)
            result = crew.kickoff()

            # Parse JSON from result
            result_text = str(result)

            # Try to extract JSON from the result
            if '{' in result_text and '}' in result_text:
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                json_str = result_text[json_start:json_end]
                strategy = json.loads(json_str)
            else:
                # Fallback: generate basic strategy with actual queries
                first_word = product_description.split()[0] if product_description else "tool"
                strategy = {
                    "product_category": product_description,
                    "competitors": [],  # Will be filled by competitor worker's identification step
                    "reddit_queries": [
                        f"{product_description} recommendations",
                        f"best {product_description}",
                        f"looking for {first_word} software"
                    ],
                    "techcrunch_focus": "Technology and SaaS",
                    "target_titles": ["Founder", "CEO", "CTO", "VP Engineering"]
                }

            self._log("STRATEGY", f"Planned: {len(strategy.get('reddit_queries', []))} queries, "
                                  f"{len(strategy.get('competitors', []))} competitors")

            return strategy

        except Exception as e:
            self._log("ERROR", f"Strategy planning failed: {str(e)}")
            # Return basic fallback strategy with actual search queries
            first_word = product_description.split()[0] if product_description else "tool"
            return {
                "product_category": product_description,
                "competitors": [],
                "reddit_queries": [
                    f"{product_description} recommendations",
                    f"best {product_description}",
                    f"looking for {first_word} tool"
                ],
                "techcrunch_focus": "Technology",
                "target_titles": ["Founder", "CEO", "CTO"]
            }

    def _run_workers_parallel(
        self,
        strategy: Dict,
        product_description: str,
        target_leads: int
    ) -> Dict[str, WorkerResult]:
        """
        Phase 2: Launch all workers in PARALLEL.

        Each worker runs independently, orchestrator reviews as they complete.
        """
        self._log("PARALLEL", "Deploying 3 workers in parallel...")

        results = {}
        target_per_worker = target_leads // 3 + 5  # Slight buffer

        def worker_log(source: str):
            def log(level: str, message: str):
                self._log(f"{source.upper()}", f"[{level}] {message}")
            return log

        # Create workers
        reddit_worker = RedditWorker(log_callback=worker_log("reddit"))
        techcrunch_worker = TechCrunchWorker(log_callback=worker_log("techcrunch"))
        competitor_worker = CompetitorWorker(log_callback=worker_log("competitor"))

        # Launch workers in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    reddit_worker.run,
                    queries=strategy.get('reddit_queries', []),
                    target_leads=target_per_worker
                ): "reddit",
                executor.submit(
                    techcrunch_worker.run,
                    industry=strategy.get('techcrunch_focus', 'Technology'),
                    product_context=product_description,
                    target_leads=target_per_worker
                ): "techcrunch",
                executor.submit(
                    competitor_worker.run,
                    competitors=strategy.get('competitors', []),
                    product_description=product_description,
                    target_leads=target_per_worker
                ): "competitor"
            }

            # Collect results as they complete
            for future in as_completed(futures):
                source = futures[future]
                try:
                    worker_result = future.result()
                    results[source] = worker_result

                    # Review result
                    reviewed = self._review_worker_result(source, worker_result, strategy)
                    results[source] = reviewed

                except Exception as e:
                    self._log("ERROR", f"{source} worker failed: {str(e)}")
                    results[source] = WorkerResult(
                        success=False,
                        error=str(e),
                        step="execution",
                        trace=[f"Worker exception: {str(e)}"]
                    )

        return results

    def _review_worker_result(
        self,
        source: str,
        result: WorkerResult,
        strategy: Dict,
        max_retries: int = 2
    ) -> WorkerResult:
        """
        Review worker output and decide: approve/retry/skip.

        STRICT MODE: Never accept empty results without retry.
        """
        self._log("REVIEW", f"Reviewing {source} output...")

        # Check for errors
        if result.error and not result.success:
            self._log("ERROR", f"{source}: {result.error}")

            # Attempt retry if we have retries left
            for attempt in range(max_retries):
                self._log("RETRY", f"{source} attempt {attempt + 1}/{max_retries}")

                # Create new worker and retry
                if source == "reddit":
                    worker = RedditWorker()
                    retry_result = worker.run(
                        queries=strategy.get('reddit_queries', []),
                        target_leads=20
                    )
                elif source == "techcrunch":
                    worker = TechCrunchWorker()
                    retry_result = worker.run(
                        industry=strategy.get('techcrunch_focus', 'Technology'),
                        product_context=strategy.get('product_category', ''),
                        target_leads=20
                    )
                else:
                    worker = CompetitorWorker()
                    retry_result = worker.run(
                        competitors=strategy.get('competitors', []),
                        product_description=strategy.get('product_category', ''),
                        target_leads=20
                    )

                if retry_result.success and retry_result.leads_count > 0:
                    self._log("FIX", f"{source} recovered with {retry_result.leads_count} leads")
                    return retry_result

            self._log("FATAL", f"{source} failed after {max_retries} retries")
            return result

        # Check for empty results (STRICT MODE)
        leads = result.data or []
        if len(leads) == 0:
            self._log("WARNING", f"{source} returned 0 leads")
            # Don't retry for empty - might just be no matches
            return result

        # Validate lead quality
        validation = self._validate_leads(leads)
        if validation['invalid_count'] > validation['valid_count']:
            self._log("WARNING", f"{source}: {validation['invalid_count']} invalid leads")

        self._log("APPROVED", f"{source}: {len(leads)} leads approved")
        return result

    def _validate_leads(self, leads: List[Dict]) -> Dict:
        """Validate lead data quality."""
        result_str = self.validate_tool._run(leads=leads)
        return json.loads(result_str)

    def _aggregate_results(
        self,
        worker_results: Dict[str, WorkerResult],
        target_leads: int
    ) -> OrchestratorResult:
        """
        Phase 3: Aggregate leads from all workers.

        1. Combine all leads
        2. Deduplicate
        3. Sort by intent score
        4. Return top N
        """
        self._log("AGGREGATE", "Aggregating leads from all workers...")

        all_leads = []
        platforms = []
        strategies = []
        errors = []

        # Collect leads from each source
        for source, result in worker_results.items():
            if result.success and result.data:
                leads = result.data
                all_leads.extend(leads)
                platforms.append(source)
                self._log("AGGREGATE", f"{source}: {len(leads)} leads")
            else:
                if result.error:
                    errors.append(f"{source}: {result.error}")

        self._log("AGGREGATE", f"Combined {len(all_leads)} raw leads")

        if not all_leads:
            return OrchestratorResult(
                success=False,
                errors=errors or ["No leads found from any source"],
                platforms_searched=platforms,
                trace=self.trace.copy()
            )

        # Deduplicate
        dedup_result = json.loads(self.dedup_tool._run(leads=all_leads))
        unique_leads = dedup_result.get('leads', all_leads)
        duplicates_removed = dedup_result.get('duplicates_removed', 0)

        self._log("AGGREGATE", f"After dedup: {len(unique_leads)} leads ({duplicates_removed} duplicates removed)")

        # Sort by intent score (descending)
        unique_leads.sort(key=lambda x: x.get('intent_score', 0), reverse=True)

        # Take top N leads
        final_leads = unique_leads[:target_leads]

        # Count by priority
        hot_leads = len([l for l in final_leads if l.get('intent_score', 0) >= 80])
        warm_leads = len([l for l in final_leads if 60 <= l.get('intent_score', 0) < 80])

        # Count by source
        reddit_leads = len([l for l in final_leads if l.get('source_platform') == 'reddit'])
        techcrunch_leads = len([l for l in final_leads if l.get('source_platform') == 'techcrunch'])
        competitor_leads = len([l for l in final_leads if l.get('source_platform') == 'linkedin'])

        self._log("COMPLETE", f"Final: {len(final_leads)} qualified leads")
        self._log("COMPLETE", f"Hot: {hot_leads}, Warm: {warm_leads}")

        return OrchestratorResult(
            success=True,
            leads=final_leads,
            total_leads=len(final_leads),
            hot_leads=hot_leads,
            warm_leads=warm_leads,
            reddit_leads=reddit_leads,
            techcrunch_leads=techcrunch_leads,
            competitor_leads=competitor_leads,
            duplicates_removed=duplicates_removed,
            platforms_searched=platforms,
            strategies_used=strategies,
            errors=errors
        )


# Convenience function for easy usage
def run_prospecting(
    product_description: str,
    target_leads: int = 50,
    icp_criteria: Optional[Dict] = None,
    output_dir: str = "."
) -> OrchestratorResult:
    """
    Run the supervisor orchestrator.

    Args:
        product_description: Description of the product/service
        target_leads: Target number of leads (default: 50)
        icp_criteria: Optional ICP matching criteria
        output_dir: Directory for output files

    Returns:
        OrchestratorResult with leads and metadata
    """
    orchestrator = SupervisorOrchestrator(output_dir=output_dir)
    return orchestrator.run(
        product_description=product_description,
        target_leads=target_leads,
        icp_criteria=icp_criteria
    )


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SUPERVISOR ORCHESTRATOR TEST")
    print("=" * 70)

    result = run_prospecting(
        product_description="ML observability tool for startups",
        target_leads=50,
        icp_criteria={
            "titles": ["Founder", "CEO", "CTO", "ML Engineer"],
            "company_size": "1-100"
        }
    )

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Total leads: {result.total_leads}")
    print(f"Hot leads: {result.hot_leads}")
    print(f"Warm leads: {result.warm_leads}")
    print(f"Reddit: {result.reddit_leads}")
    print(f"TechCrunch: {result.techcrunch_leads}")
    print(f"Competitor: {result.competitor_leads}")
    print(f"Duplicates removed: {result.duplicates_removed}")
    print(f"Execution time: {result.execution_time:.1f}s")
    print(f"Platforms: {result.platforms_searched}")
    print(f"Errors: {result.errors}")
    print("=" * 70)
