"""
Orchestrator Crew - Multi-Task Sequential Architecture (v3.4).

This crew uses 5 focused agents with task chaining:
1. strategy_planner -> Analyze query, create prospecting plan
2. reddit_specialist -> Execute Reddit strategy
3. techcrunch_specialist -> Execute TechCrunch strategy (SERP-based)
4. competitor_specialist -> Execute competitor displacement strategy
5. lead_aggregator -> Combine and filter final leads

Tasks pass data via context=[previous_task] for sequential execution.
"""
import os
from pathlib import Path
from typing import List, Optional
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Centralized config for models
from app.core.config import settings

# Import tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# === STEPPED TOOLS (Agent reasons after each step) ===
# Reddit stepped tools
from tools.stepped.reddit_tools import (
    RedditSearchSteppedTool,
    RedditScoreTool,
    RedditExtractTool
)

# TechCrunch stepped tools (funding signals)
from tools.stepped.techcrunch_tools import (
    TechCrunchFetchTool,
    TechCrunchFetchParallelTool,  # v3.4: Parallel page fetching
    TechCrunchSelectArticlesTool,
    TechCrunchExtractCompaniesTool,
    TechCrunchSelectDecisionMakersTool,
    TechCrunchSerpDecisionMakersTool  # v3.4: SERP-based decision makers
)

# Competitor displacement tools (v3.4)
from tools.stepped.competitor_tools import (
    CompetitorIdentifyTool,
    CompetitorScrapeTool
)

# Seller filter (reusable utility)
from tools.stepped.filter_sellers import FilterSellersTool

# === ATOMIC TOOLS (for creative exploration) ===
# Google/Web tools (CrewAI native - Serper for search, ScrapeWebsite for content)
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

# Search-based tools (keep for backup/creative use)
from tools.apify_reddit import ApifyRedditSearchTool
from tools.apify_twitter import ApifyTwitterSearchTool

# Funding signals
from tools.apify_crunchbase import ApifyCrunchbaseTool

# Enrichment-only tools (LinkedIn)
from tools.apify_linkedin_employees import LinkedInEmployeesSearchTool, LinkedInEmployeesBatchSearchTool
from tools.apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool
from tools.apify_linkedin_post_comments import LinkedInPostCommentsTool
from tools.apify_linkedin_company_search import LinkedInCompanySearchTool, LinkedInCompanyBatchSearchTool


# =============================================================================
# PYDANTIC OUTPUT MODELS - Structured outputs for each task
# =============================================================================

class LeadPriority(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class StrategyPlan(BaseModel):
    """Output from Task 1: Strategy planning."""
    product_category: str = Field(description="Type of product")
    competitors: List[str] = Field(description="Likely competitors")
    reddit_queries: List[str] = Field(description="2-3 Reddit search queries")
    techcrunch_focus: str = Field(description="Industry and funding stage focus")
    target_titles: List[str] = Field(description="Decision maker titles to target")
    lead_distribution: str = Field(description="How to split leads between sources")


class Lead(BaseModel):
    """Individual lead with all data."""
    name: str = Field(description="Full name of the lead")
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    email: Optional[str] = Field(default=None, description="Email address if available")

    # Intent signals
    intent_signal: str = Field(description="Quote showing buying intent")
    intent_score: int = Field(ge=0, le=100, description="Intent score 0-100")

    # Source tracking
    source_platform: str = Field(description="Platform where found")
    source_url: str = Field(description="Original post/discussion URL")

    # Scoring
    priority: LeadPriority = Field(description="Lead priority: hot, warm, or cold")
    scoring_reasoning: str = Field(description="Why this lead scores this way")

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v):
        """Normalize LLM priority responses to valid enum values."""
        if isinstance(v, str):
            v = v.lower().strip()
            mapping = {
                'medium': 'warm',
                'high': 'hot',
                'low': 'cold',
            }
            v = mapping.get(v, v)
        return v

    @field_validator('source_url', mode='before')
    @classmethod
    def normalize_source_url(cls, v):
        """Handle None source_url by providing a default."""
        if v is None:
            return "No URL available"
        return v


class RedditLeads(BaseModel):
    """Output from Task 2: Reddit prospecting."""
    leads: List[Lead] = Field(description="Buyer leads from Reddit")
    count: int = Field(description="Number of leads found")
    queries_used: List[str] = Field(description="Search queries that worked")
    workflow_trace: str = Field(description="Reasoning at each step")


class TechCrunchLeads(BaseModel):
    """Output from Task 3: TechCrunch prospecting."""
    leads: List[Lead] = Field(description="Decision-maker leads from TechCrunch")
    count: int = Field(description="Number of leads found")
    companies_found: List[str] = Field(description="Companies with recent funding")
    workflow_trace: str = Field(description="Reasoning at each step")


class CompetitorLeads(BaseModel):
    """Output from Task 4: Competitor displacement prospecting."""
    leads: List[Lead] = Field(description="Leads from competitor engagement")
    count: int = Field(description="Number of leads found")
    competitors_scraped: List[str] = Field(description="Competitor companies scraped")
    workflow_trace: str = Field(description="Reasoning at each step")


class ProspectingOutput(BaseModel):
    """Output from Task 5: Final aggregated leads."""
    leads: List[Lead] = Field(description="List of qualified leads")
    total_leads: int = Field(description="Total number of leads found")
    hot_leads: int = Field(description="Number of hot leads (score >= 80)")
    warm_leads: int = Field(description="Number of warm leads (score 60-79)")
    reddit_leads_count: int = Field(default=0, description="Leads from Reddit")
    techcrunch_leads_count: int = Field(default=0, description="Leads from TechCrunch")
    competitor_leads_count: int = Field(default=0, description="Leads from competitor displacement")
    sellers_removed: int = Field(default=0, description="Sellers filtered out")
    duplicates_removed: int = Field(default=0, description="Duplicates removed")
    platforms_searched: List[str] = Field(description="Platforms that were searched")
    strategies_used: List[str] = Field(description="Strategies employed")
    summary: str = Field(description="Summary of the prospecting session")


# =============================================================================
# ORCHESTRATOR CREW - 5 Agents, 5 Tasks, Sequential Process (v3.4)
# =============================================================================

@CrewBase
class OrchestratorCrew:
    """
    Multi-task orchestrator crew for modular prospecting.

    Architecture:
    - 4 focused agents, each handling one task
    - Tasks chained via context=[previous_task]
    - Structured outputs with Pydantic models
    - Each agent reasons independently
    """

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        """Initialize the orchestrator crew with LLM configuration."""
        self.llm = LLM(
            model=settings.AGENT_MODEL,
            temperature=settings.AGENT_TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    # =========================================================================
    # AGENTS - 4 focused agents
    # =========================================================================

    @agent
    def strategy_planner(self) -> Agent:
        """Agent 1: Analyze product and create prospecting strategy."""
        return Agent(
            config=self.agents_config['strategy_planner'],
            tools=[
                # Planning agent doesn't need tools - just analyzes input
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @agent
    def reddit_specialist(self) -> Agent:
        """Agent 2: Execute Reddit stepped workflow."""
        return Agent(
            config=self.agents_config['reddit_specialist'],
            tools=[
                # Reddit stepped tools
                RedditSearchSteppedTool(),
                RedditScoreTool(),
                RedditExtractTool(),
                FilterSellersTool(),
            ],
            llm=self.llm,
            verbose=True,
            max_iter=25,
            max_retry_limit=3,
            memory=True
        )

    @agent
    def techcrunch_specialist(self) -> Agent:
        """Agent 3: Execute TechCrunch workflow with SERP-based decision makers."""
        return Agent(
            config=self.agents_config['techcrunch_specialist'],
            tools=[
                # TechCrunch stepped tools (v3.4)
                TechCrunchFetchTool(),
                TechCrunchFetchParallelTool(),  # Parallel page fetching
                TechCrunchSelectArticlesTool(),
                TechCrunchExtractCompaniesTool(),
                TechCrunchSelectDecisionMakersTool(),
                TechCrunchSerpDecisionMakersTool(),  # SERP-based decision makers (fast!)

                # LinkedIn tools (backup/enrichment only)
                LinkedInCompanySearchTool(),
                LinkedInCompanyBatchSearchTool(),
                LinkedInEmployeesSearchTool(),
                LinkedInEmployeesBatchSearchTool(),

                # Seller filter
                FilterSellersTool(),
            ],
            llm=self.llm,
            verbose=True,
            max_iter=30,
            max_retry_limit=3,
            memory=True
        )

    @agent
    def competitor_specialist(self) -> Agent:
        """Agent 4: Execute competitor displacement strategy."""
        return Agent(
            config=self.agents_config['competitor_specialist'],
            tools=[
                # Competitor displacement tools (v3.4)
                CompetitorIdentifyTool(),
                CompetitorScrapeTool(),

                # Seller filter
                FilterSellersTool(),
            ],
            llm=self.llm,
            verbose=True,
            max_iter=20,
            max_retry_limit=3,
            memory=True
        )

    @agent
    def lead_aggregator(self) -> Agent:
        """Agent 5: Combine, deduplicate, and rank final leads."""
        return Agent(
            config=self.agents_config['lead_aggregator'],
            tools=[
                FilterSellersTool(),  # Final seller check
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    # =========================================================================
    # TASKS - 5 chained tasks with context passing (v3.4)
    # =========================================================================

    @task
    def plan_strategy(self) -> Task:
        """Task 1: Create prospecting strategy plan."""
        return Task(
            config=self.tasks_config['plan_strategy'],
            agent=self.strategy_planner(),
            output_pydantic=StrategyPlan
        )

    @task
    def reddit_prospecting(self) -> Task:
        """Task 2: Execute Reddit strategy using plan from Task 1."""
        return Task(
            config=self.tasks_config['reddit_prospecting'],
            agent=self.reddit_specialist(),
            context=[self.plan_strategy()],  # Receives strategy plan
            output_pydantic=RedditLeads
        )

    @task
    def techcrunch_prospecting(self) -> Task:
        """Task 3: Execute TechCrunch strategy using plan from Task 1."""
        return Task(
            config=self.tasks_config['techcrunch_prospecting'],
            agent=self.techcrunch_specialist(),
            context=[self.plan_strategy()],  # Receives strategy plan
            output_pydantic=TechCrunchLeads
        )

    @task
    def competitor_prospecting(self) -> Task:
        """Task 4: Execute competitor displacement strategy using plan from Task 1."""
        return Task(
            config=self.tasks_config['competitor_prospecting'],
            agent=self.competitor_specialist(),
            context=[self.plan_strategy()],  # Receives strategy plan
            output_pydantic=CompetitorLeads
        )

    @task
    def aggregate_leads(self) -> Task:
        """Task 5: Combine leads from Tasks 2, 3 & 4 into final output."""
        return Task(
            config=self.tasks_config['aggregate_leads'],
            agent=self.lead_aggregator(),
            context=[
                self.reddit_prospecting(),       # Receives Reddit leads
                self.techcrunch_prospecting(),   # Receives TechCrunch leads
                self.competitor_prospecting()    # Receives competitor leads
            ],
            output_pydantic=ProspectingOutput
        )

    @crew
    def crew(self) -> Crew:
        """
        Create the orchestrator crew with 5 agents and sequential tasks.
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def run_prospecting(
    product_description: str,
    target_leads: int = 100,
    icp_criteria: dict = None
) -> ProspectingOutput:
    """
    Run the orchestrator crew to find leads.

    Args:
        product_description: Description of the product/service
        target_leads: Target number of leads to find (default: 100)
        icp_criteria: Optional ICP matching criteria

    Returns:
        ProspectingOutput with qualified leads
    """
    crew = OrchestratorCrew()

    result = crew.crew().kickoff(inputs={
        "product_description": product_description,
        "target_leads": target_leads,
        "icp_criteria": icp_criteria or {}
    })

    return result.pydantic


# =============================================================================
# TEST FUNCTION
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ORCHESTRATOR CREW TEST - Multi-Task Architecture")
    print("=" * 70)

    result = run_prospecting(
        product_description="AI design agent that helps startups ship UI faster",
        target_leads=10,
        icp_criteria={
            "titles": ["Founder", "CEO", "Head of Product"],
            "company_size": "1-50",
            "industries": ["SaaS", "Technology"]
        }
    )

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total leads: {result.total_leads}")
    print(f"Hot leads: {result.hot_leads}")
    print(f"Warm leads: {result.warm_leads}")
    print(f"Reddit leads: {result.reddit_leads_count}")
    print(f"TechCrunch leads: {result.techcrunch_leads_count}")
    print(f"Competitor leads: {result.competitor_leads_count}")
    print(f"Sellers removed: {result.sellers_removed}")
    print(f"Duplicates removed: {result.duplicates_removed}")
    print(f"Platforms: {result.platforms_searched}")
    print(f"Strategies: {result.strategies_used}")
    print(f"\nSummary: {result.summary}")
    print("=" * 70)
