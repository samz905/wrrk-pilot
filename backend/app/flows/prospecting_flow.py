"""
ProspectingFlow - Master orchestration for lead prospecting.

This flow coordinates intelligent multi-platform prospecting by orchestrating
specialized crews (LinkedIn, Reddit, Twitter) and streaming real-time updates.
"""
import os
from typing import List, Dict, Any, Callable
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start

# Import all crews
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crews.linkedin.crew import LinkedInProspectingCrew
from crews.reddit.crew import RedditProspectingCrew
from crews.twitter.crew import TwitterProspectingCrew


class ProspectingState(BaseModel):
    """State management for prospecting flow."""
    query: str = ""
    max_leads: int = 100
    leads: List[Dict[str, Any]] = []
    crew_results: Dict[str, Any] = {}
    status: str = "initializing"  # initializing, searching, processing, completed, failed
    error: str = ""


class ProspectingFlow(Flow[ProspectingState]):
    """
    Master prospecting flow that orchestrates specialized crews.

    The flow coordinates:
    1. Reddit Crew - Finds intent signals in discussions
    2. LinkedIn Crew - Identifies decision-makers and enriches profiles
    3. Twitter Crew - Discovers conversations and pain points

    Each crew runs independently and results are aggregated.
    Real-time events are streamed via SSE for UI visibility.
    """

    def __init__(self, event_callback: Callable[[Dict], None] = None):
        """
        Initialize flow with optional event callback for SSE streaming.

        Args:
            event_callback: Function to call with events for real-time updates
        """
        super().__init__()
        self.event_callback = event_callback

    def emit_event(self, event_type: str, data: Any):
        """Emit event for SSE streaming."""
        if self.event_callback:
            self.event_callback({"type": event_type, "data": data})

    @start()
    def initialize(self):
        """Initialize prospecting session."""
        self.emit_event("thought", "Initializing intelligent prospecting flow...")
        self.emit_event("thought", f"Search query: {self.state.query}")
        self.emit_event("thought", f"Target: {self.state.max_leads} high-quality leads")
        self.emit_event("thought", "Will orchestrate LinkedIn, Reddit, and Twitter crews")

        self.state.status = "searching"
        return self.state

    @listen(initialize)
    def reddit_prospecting(self, state: ProspectingState):
        """
        Run Reddit crew to find intent signals.

        Reddit is great for finding:
        - Pain points and complaints
        - Feature requests
        - Competitor discussions
        """
        self.emit_event("crew_started", "Reddit Crew - Searching for intent signals...")

        try:
            # Initialize Reddit crew
            reddit_crew = RedditProspectingCrew()

            # Prepare inputs for the crew
            inputs = {
                "search_query": state.query,
                "max_results": 50  # Get more raw data, we'll filter
            }

            self.emit_event("thought", f"Reddit Crew analyzing discussions about: {state.query}")

            # Execute Reddit crew
            result = reddit_crew.crew().kickoff(inputs=inputs)

            # Store results
            state.crew_results["reddit"] = {
                "raw_output": str(result),
                "status": "completed"
            }

            self.emit_event("crew_completed", f"Reddit Crew finished - Found discussions")
            return state

        except Exception as e:
            state.crew_results["reddit"] = {
                "error": str(e),
                "status": "failed"
            }
            self.emit_event("error", f"Reddit Crew failed: {str(e)}")
            return state

    @listen(reddit_prospecting)
    def linkedin_prospecting(self, state: ProspectingState):
        """
        Run LinkedIn crew to find decision-makers.

        LinkedIn finds:
        - Decision-makers by title
        - Intent signals from posts
        - Contact enrichment
        """
        self.emit_event("crew_started", "LinkedIn Crew - Finding decision-makers...")

        try:
            # Initialize LinkedIn crew
            linkedin_crew = LinkedInProspectingCrew()

            # Prepare inputs
            inputs = {
                "search_query": state.query,
                "max_results": state.max_leads
            }

            self.emit_event("thought", f"LinkedIn Crew searching for: {state.query}")

            # Execute LinkedIn crew
            result = linkedin_crew.crew().kickoff(inputs=inputs)

            # Store results
            state.crew_results["linkedin"] = {
                "raw_output": str(result),
                "status": "completed"
            }

            self.emit_event("crew_completed", f"LinkedIn Crew finished - Found decision-makers")
            return state

        except Exception as e:
            state.crew_results["linkedin"] = {
                "error": str(e),
                "status": "failed"
            }
            self.emit_event("error", f"LinkedIn Crew failed: {str(e)}")
            return state

    @listen(linkedin_prospecting)
    def twitter_prospecting(self, state: ProspectingState):
        """
        Run Twitter crew to find conversations.

        Twitter discovers:
        - Real-time conversations
        - Product mentions
        - Competitor discussions
        """
        self.emit_event("crew_started", "Twitter Crew - Discovering conversations...")

        try:
            # Initialize Twitter crew
            twitter_crew = TwitterProspectingCrew()

            # Prepare inputs
            inputs = {
                "search_query": state.query,
                "max_results": 50
            }

            self.emit_event("thought", f"Twitter Crew analyzing tweets about: {state.query}")

            # Execute Twitter crew
            result = twitter_crew.crew().kickoff(inputs=inputs)

            # Store results
            state.crew_results["twitter"] = {
                "raw_output": str(result),
                "status": "completed"
            }

            self.emit_event("crew_completed", f"Twitter Crew finished - Found conversations")
            return state

        except Exception as e:
            state.crew_results["twitter"] = {
                "error": str(e),
                "status": "failed"
            }
            self.emit_event("error", f"Twitter Crew failed: {str(e)}")
            return state

    @listen(twitter_prospecting)
    def aggregate_results(self, state: ProspectingState):
        """
        Aggregate results from all crews.

        Combines leads from LinkedIn, Reddit, and Twitter into
        a unified lead list with scoring.
        """
        self.emit_event("thought", "Aggregating results from all crews...")

        try:
            # TODO: Parse crew outputs and extract structured leads
            # For now, store raw results
            state.leads = [{
                "reddit": state.crew_results.get("reddit", {}).get("raw_output", ""),
                "linkedin": state.crew_results.get("linkedin", {}).get("raw_output", ""),
                "twitter": state.crew_results.get("twitter", {}).get("raw_output", ""),
                "timestamp": "now"
            }]

            state.status = "completed"
            self.emit_event("thought", f"Prospecting complete! Aggregated results from all crews.")

            return state

        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            self.emit_event("error", f"Error aggregating results: {str(e)}")
            return state
