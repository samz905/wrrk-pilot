"""
Orchestrator Crew - Single agent with all tools for autonomous prospecting.

This crew uses one intelligent agent with reasoning capabilities to:
1. Analyze the prospecting query
2. Choose the best tools and strategies
3. Execute searches across platforms
4. Reflect on results and adapt
5. Enrich and score leads
6. Return qualified leads
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
    TechCrunchSelectArticlesTool,
    TechCrunchExtractCompaniesTool,
    TechCrunchSelectDecisionMakersTool
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


# Pydantic models for structured output
class LeadPriority(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


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
            # Map common LLM variations to valid enum values
            mapping = {
                'medium': 'warm',
                'high': 'hot',
                'low': 'cold',
            }
            v = mapping.get(v, v)
        return v


class ProspectingOutput(BaseModel):
    """Structured output from prospecting task."""
    leads: List[Lead] = Field(description="List of qualified leads")
    total_leads: int = Field(description="Total number of leads found")
    hot_leads: int = Field(description="Number of hot leads (score >= 80)")
    warm_leads: int = Field(description="Number of warm leads (score 60-79)")
    platforms_searched: List[str] = Field(description="Platforms that were searched")
    strategies_used: List[str] = Field(description="Strategies employed")
    summary: str = Field(description="Summary of the prospecting session")


@CrewBase
class OrchestratorCrew:
    """
    Single-agent orchestrator crew for autonomous prospecting.

    This crew uses one powerful agent with:
    - All atomic and composite tools
    - Reasoning enabled for planning
    - Reflection and retry capabilities
    - Memory for context across tool calls
    """

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        """Initialize the orchestrator crew with LLM configuration."""
        # Use centralized config for model settings
        self.llm = LLM(
            model=settings.AGENT_MODEL,
            temperature=settings.AGENT_TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    @agent
    def orchestrator(self) -> Agent:
        """
        Create the orchestrator agent with stepped tools for reasoning at each checkpoint.

        STEPPED TOOLS (primary - agent reasons after each):
        - Reddit: search -> score -> extract -> filter_sellers
        - TechCrunch: fetch -> select -> extract -> decision_makers

        ATOMIC TOOLS (secondary - for creative exploration):
        - Direct crawling, search, enrichment
        """
        return Agent(
            config=self.agents_config['orchestrator'],
            tools=[
                # === STEPPED TOOLS (Primary - Agent reasons after each) ===

                # REDDIT STRATEGY: search -> score -> extract
                RedditSearchSteppedTool(),   # Step 1: Search, review quality
                RedditScoreTool(),           # Step 2: Score, review results
                RedditExtractTool(),         # Step 3: Extract leads

                # TECHCRUNCH STRATEGY: fetch -> select -> extract -> decision makers
                TechCrunchFetchTool(),           # Step 1: Get funding articles
                TechCrunchSelectArticlesTool(),  # Step 2: Select relevant articles
                TechCrunchExtractCompaniesTool(), # Step 3: Extract company info
                TechCrunchSelectDecisionMakersTool(), # Step 4: Pick decision makers

                # SELLER FILTER (Reusable utility - ALWAYS use before finalizing)
                FilterSellersTool(),

                # === ATOMIC TOOLS (Secondary - For creative exploration) ===

                # LinkedIn - for enrichment ONLY (use after finding leads)
                LinkedInCompanySearchTool(),    # Find company LinkedIn URL by name
                LinkedInCompanyBatchSearchTool(), # Batch search for multiple companies
                LinkedInEmployeesSearchTool(),  # Find decision makers at ONE company
                LinkedInEmployeesBatchSearchTool(), # Find decision makers at MULTIPLE companies (PARALLEL - use this!)
                ApifyLinkedInProfileDetailTool(),

                # Google/Web tools - for creative exploration
                SerperDevTool(),        # SERP search (HackerNews, forums, etc.)
                ScrapeWebsiteTool(),    # Extract content from URLs

                # Search tools - backup/creative use
                ApifyTwitterSearchTool(),
            ],
            llm=self.llm,
            verbose=True,

            # Agentic behavior parameters
            max_iter=50,                # Allow extensive iteration
            max_retry_limit=3,          # Retry failed tool calls
            memory=True,                # Maintain context across calls
            allow_delegation=False,     # Single agent for simplicity

            # Resource management
            max_rpm=10,                 # Prevent API throttling
            max_execution_time=900,     # 15 minute max
            respect_context_window=True # Auto-summarize if needed
        )

    @task
    def prospect_leads(self) -> Task:
        """
        Create the main prospecting task with structured output.
        """
        return Task(
            config=self.tasks_config['prospect_leads'],
            agent=self.orchestrator(),
            output_pydantic=ProspectingOutput
        )

    @crew
    def crew(self) -> Crew:
        """
        Create the orchestrator crew with single agent and task.
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10
            # Removed planning=True - was causing agent to "narrate" instead of execute tools
        )


# Convenience function to run the orchestrator
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


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ORCHESTRATOR CREW TEST")
    print("=" * 70)

    # Test with a simple query
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
    print(f"Platforms: {result.platforms_searched}")
    print(f"Strategies: {result.strategies_used}")
    print(f"\nSummary: {result.summary}")
    print("=" * 70)
