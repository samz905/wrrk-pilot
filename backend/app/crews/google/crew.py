"""Google prospecting crew."""
import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM

# Import Google tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_google_serp import ApifyGoogleSERPTool
from tools.apify_website_crawler import ApifyWebsiteCrawlerTool


@CrewBase
class GoogleProspectingCrew:
    """Google company intelligence prospecting crew."""

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
    def google_research_agent(self) -> Agent:
        """Create Google research agent with SERP and crawler tools."""
        return Agent(
            config=self.agents_config['google_researcher'],
            tools=[
                ApifyGoogleSERPTool(),          # Find news/articles about companies
                ApifyWebsiteCrawlerTool()       # Extract full article content
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def search_company_triggers(self) -> Task:
        """Create Google company trigger search task."""
        return Task(
            config=self.tasks_config['search_company_triggers'],
            agent=self.google_research_agent()
        )

    @crew
    def crew(self) -> Crew:
        """Create the Google prospecting crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Rate limiting for cost control
        )
