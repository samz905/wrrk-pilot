"""LinkedIn prospecting crew."""
import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM

# Import all LinkedIn tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_linkedin import ApifyLinkedInSearchTool
from tools.apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from tools.apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool


@CrewBase
class LinkedInProspectingCrew:
    """LinkedIn lead prospecting crew."""

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
    def linkedin_intelligence_agent(self) -> Agent:
        """Create LinkedIn intelligence agent with all 3 tools."""
        return Agent(
            config=self.agents_config['linkedin_intelligence_agent'],
            tools=[
                ApifyLinkedInSearchTool(),           # Find people by title
                ApifyLinkedInPostsSearchTool(),      # Find intent signals
                ApifyLinkedInProfileDetailTool()     # Enrich with email
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def search_linkedin_profiles(self) -> Task:
        """Create LinkedIn search task."""
        return Task(
            config=self.tasks_config['search_linkedin_profiles'],
            agent=self.linkedin_intelligence_agent()
        )

    @crew
    def crew(self) -> Crew:
        """Create the LinkedIn prospecting crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Rate limiting for cost control
        )
