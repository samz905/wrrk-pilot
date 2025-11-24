"""Qualification crew for scoring and prioritizing leads."""
import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM

# Import qualification tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.icp_matcher import ICPMatcherTool
from tools.lead_scorer import LeadScorerTool


@CrewBase
class QualificationCrew:
    """Lead qualification and scoring crew."""

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        """Initialize the crew with GPT-4o-mini configuration."""
        self.llm = LLM(
            model="gpt-4o-mini",
            temperature=0.3,  # Lower temperature for consistent scoring
            api_key=os.getenv("OPENAI_API_KEY")
        )

    @agent
    def qualification_specialist(self) -> Agent:
        """Create qualification agent with scoring tools."""
        return Agent(
            config=self.agents_config['qualification_specialist'],
            tools=[
                ICPMatcherTool(),      # Score against ICP
                LeadScorerTool()       # Calculate final score
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def qualify_and_score_leads(self) -> Task:
        """Create lead qualification task."""
        return Task(
            config=self.tasks_config['qualify_and_score_leads'],
            agent=self.qualification_specialist()
        )

    @crew
    def crew(self) -> Crew:
        """Create the qualification crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Rate limiting for cost control
        )
