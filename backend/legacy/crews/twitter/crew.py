"""Twitter prospecting crew."""
import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM

# Import Twitter tool
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_twitter import ApifyTwitterSearchTool


@CrewBase
class TwitterProspectingCrew:
    """Twitter lead prospecting crew."""

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
    def twitter_signal_hunter(self) -> Agent:
        """Create Twitter intent signal hunter agent."""
        return Agent(
            config=self.agents_config['twitter_signal_hunter'],
            tools=[
                ApifyTwitterSearchTool(),  # Find tweets by keywords
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def search_twitter_intent(self) -> Task:
        """Create Twitter intent search task."""
        return Task(
            config=self.tasks_config['search_twitter_intent'],
            agent=self.twitter_signal_hunter()
        )

    @crew
    def crew(self) -> Crew:
        """Create the Twitter prospecting crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Rate limiting for cost control
        )
