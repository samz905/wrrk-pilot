"""Reddit prospecting crew."""
import os
from pathlib import Path
from typing import List
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM
from pydantic import BaseModel, Field

# Import Reddit tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_reddit import ApifyRedditSearchTool, RedditLeadExtractionTool


# Pydantic models for structured task outputs
class DiscussionResult(BaseModel):
    """A single Reddit discussion with intent signal."""
    title: str = Field(description="Post title")
    url: str = Field(description="Reddit post URL")
    subreddit: str = Field(description="Subreddit name without r/")
    upvotes: int = Field(description="Number of upvotes")
    num_comments: int = Field(description="Number of comments")
    intent_score: int = Field(description="Intent score 0-100")
    reasoning: str = Field(description="Why this discussion is relevant")


class Task1Output(BaseModel):
    """Output from Task 1: List of top discussions."""
    discussions: List[DiscussionResult] = Field(description="List of top relevant discussions")


class LeadResult(BaseModel):
    """A single Reddit lead with buying intent."""
    username: str = Field(description="Reddit username without u/")
    profile_url: str = Field(description="Reddit profile URL")
    buying_signal: str = Field(description="Quote showing buying intent")
    intent_score: int = Field(description="Intent score 0-100")
    fit_reasoning: str = Field(description="Why this user is a good lead")
    source_url: str = Field(description="Source discussion URL")
    source_subreddit: str = Field(description="Source subreddit")


class Task2Output(BaseModel):
    """Output from Task 2: List of leads with buying intent."""
    leads: List[LeadResult] = Field(description="List of Reddit users with buying intent")


@CrewBase
class RedditProspectingCrew:
    """Reddit lead prospecting crew."""

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        """Initialize the crew with GPT-4o-mini configuration."""
        self.llm = LLM(
            model="gpt-4o-mini",
            temperature=0.5,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    @agent
    def reddit_intelligence_agent(self) -> Agent:
        """Create Reddit intelligence agent with Reddit search tool."""
        return Agent(
            config=self.agents_config['reddit_detective'],
            tools=[
                ApifyRedditSearchTool(),  # Find discussions by keywords/subreddit
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @agent
    def lead_extraction_agent(self) -> Agent:
        """Create lead extraction agent with Reddit lead extraction tool."""
        return Agent(
            config=self.agents_config['lead_extractor'],
            tools=[
                RedditLeadExtractionTool(),  # Extract users with buying intent from discussions
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def search_reddit_discussions(self) -> Task:
        """Create Reddit search task with structured output."""
        return Task(
            config=self.tasks_config['search_reddit_discussions'],
            agent=self.reddit_intelligence_agent(),
            output_pydantic=Task1Output  # Force structured output
        )

    @task
    def extract_reddit_leads(self) -> Task:
        """Create Reddit lead extraction task with structured output."""
        return Task(
            config=self.tasks_config['extract_reddit_leads'],
            agent=self.lead_extraction_agent(),
            context=[self.search_reddit_discussions()],  # Explicitly receive Task 1 output
            output_pydantic=Task2Output  # Force structured output
        )

    @crew
    def crew(self) -> Crew:
        """Create the Reddit prospecting crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Rate limiting for cost control
        )
