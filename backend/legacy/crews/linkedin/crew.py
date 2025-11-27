"""LinkedIn prospecting crew."""
import os
from pathlib import Path
from typing import List, Optional
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM
from pydantic import BaseModel, Field

# Import LinkedIn tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from tools.apify_linkedin_leads import LinkedInLeadExtractionTool


# Pydantic models for structured task outputs
class PostResult(BaseModel):
    """A single LinkedIn post with intent signal."""
    author_name: str = Field(description="Name of the poster")
    author_title: str = Field(description="Job title/headline")
    author_url: str = Field(description="LinkedIn profile URL")
    post_content: str = Field(description="Post text (max 300 chars)")
    post_url: str = Field(description="URL to the post")
    likes: int = Field(description="Number of likes")
    comments: int = Field(description="Number of comments")
    intent_score: int = Field(description="Intent score 0-100")
    intent_signal: str = Field(description="Why this shows buying intent")


class Task1Output(BaseModel):
    """Output from Task 1: List of top posts."""
    posts: List[PostResult] = Field(description="List of top posts with intent signals")


class LeadResult(BaseModel):
    """A single LinkedIn lead with buying intent."""
    name: str = Field(description="Full name")
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    linkedin_url: str = Field(description="Profile URL")
    intent_signal: str = Field(description="Quote showing intent (max 100 chars)")
    intent_score: int = Field(description="Intent score 0-100")
    fit_reasoning: str = Field(description="Why they're a good lead")
    source_post_url: str = Field(description="Where they were found")


class Task2Output(BaseModel):
    """Output from Task 2: List of leads with buying intent."""
    leads: List[LeadResult] = Field(description="List of qualified leads")


@CrewBase
class LinkedInProspectingCrew:
    """LinkedIn lead prospecting crew."""

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        """Initialize the crew with GPT-4o-mini configuration."""
        self.llm = LLM(
            model="gpt-5-nano",
            temperature=0.5,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    @agent
    def linkedin_intelligence_agent(self) -> Agent:
        """Create LinkedIn intelligence agent with posts search tool."""
        return Agent(
            config=self.agents_config['linkedin_intelligence_agent'],
            tools=[ApifyLinkedInPostsSearchTool()],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @agent
    def lead_extraction_agent(self) -> Agent:
        """Create lead extraction agent with lead extraction tool."""
        return Agent(
            config=self.agents_config['lead_extraction_agent'],
            tools=[LinkedInLeadExtractionTool()],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def search_linkedin_posts(self) -> Task:
        """Create LinkedIn posts search task with structured output."""
        return Task(
            config=self.tasks_config['search_linkedin_posts'],
            agent=self.linkedin_intelligence_agent(),
            output_pydantic=Task1Output  # Force structured output
        )

    @task
    def extract_linkedin_leads(self) -> Task:
        """Create LinkedIn lead extraction task with structured output."""
        return Task(
            config=self.tasks_config['extract_linkedin_leads'],
            agent=self.lead_extraction_agent(),
            context=[self.search_linkedin_posts()],  # Explicitly receive Task 1 output
            output_pydantic=Task2Output  # Force structured output
        )

    @crew
    def crew(self) -> Crew:
        """Create the LinkedIn prospecting crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10
        )
