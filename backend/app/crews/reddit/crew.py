"""Reddit prospecting crew."""
import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM

# Import Reddit tool
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_reddit import ApifyRedditSearchTool


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

    @task
    def search_reddit_discussions(self) -> Task:
        """Create Reddit search task."""
        return Task(
            config=self.tasks_config['search_reddit_discussions'],
            agent=self.reddit_intelligence_agent()
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
