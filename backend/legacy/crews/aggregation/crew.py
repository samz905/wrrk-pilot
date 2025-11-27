"""Aggregation crew for deduplicating and merging leads."""
import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai import LLM

# Import aggregation tools
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.fuzzy_matcher import FuzzyMatcherTool
from tools.domain_extractor import DomainExtractorTool


@CrewBase
class AggregationCrew:
    """Lead aggregation and deduplication crew."""

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    def __init__(self):
        """Initialize the crew with GPT-4o-mini configuration."""
        self.llm = LLM(
            model="gpt-5-nano",
            temperature=0.3,  # Lower temperature for consistent deduplication
            api_key=os.getenv("OPENAI_API_KEY")
        )

    @agent
    def aggregation_specialist(self) -> Agent:
        """Create aggregation agent with deduplication tools."""
        return Agent(
            config=self.agents_config['aggregation_specialist'],
            tools=[
                FuzzyMatcherTool(),      # Match names and companies
                DomainExtractorTool()    # Extract company domains
            ],
            llm=self.llm,
            verbose=True,
            max_retry_limit=2
        )

    @task
    def merge_and_deduplicate(self) -> Task:
        """Create deduplication task."""
        return Task(
            config=self.tasks_config['merge_and_deduplicate_leads'],
            agent=self.aggregation_specialist()
        )

    @crew
    def crew(self) -> Crew:
        """Create the aggregation crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=10  # Rate limiting for cost control
        )
