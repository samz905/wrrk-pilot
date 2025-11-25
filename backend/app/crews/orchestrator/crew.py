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
from pydantic import BaseModel, Field
from enum import Enum

# Import tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Atomic tools
from tools.apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from tools.apify_linkedin_employees import LinkedInEmployeesSearchTool
from tools.apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool
from tools.apify_linkedin_post_comments import LinkedInPostCommentsTool
from tools.apify_reddit import ApifyRedditSearchTool
from tools.apify_twitter import ApifyTwitterSearchTool
from tools.apify_google_serp import ApifyGoogleSERPTool
from tools.apify_crunchbase import ApifyCrunchbaseTool

# Composite tools
from tools.composite.intent_signal_hunter import IntentSignalHunterTool
from tools.composite.company_trigger_scanner import CompanyTriggerScannerTool
from tools.composite.decision_maker_finder import DecisionMakerFinderTool


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
        # Use GPT-4o for better reasoning
        self.llm = LLM(
            model="gpt-4o",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    @agent
    def orchestrator(self) -> Agent:
        """
        Create the orchestrator agent with all tools and agentic capabilities.
        """
        return Agent(
            config=self.agents_config['orchestrator'],
            tools=[
                # Composite tools (preferred - handle parallelism internally)
                IntentSignalHunterTool(),
                CompanyTriggerScannerTool(),
                DecisionMakerFinderTool(),

                # Atomic tools (for fine-grained control when needed)
                ApifyLinkedInPostsSearchTool(),
                LinkedInEmployeesSearchTool(),
                ApifyLinkedInProfileDetailTool(),
                LinkedInPostCommentsTool(),
                ApifyRedditSearchTool(),
                ApifyTwitterSearchTool(),
                ApifyGoogleSERPTool(),
                ApifyCrunchbaseTool(),
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
            max_rpm=10,
            # Enable planning for complex tasks
            planning=True,
            planning_llm=self.llm
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
