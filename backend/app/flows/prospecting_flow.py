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
from crews.google.crew import GoogleProspectingCrew
from crews.aggregation.crew import AggregationCrew
from crews.qualification.crew import QualificationCrew


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
    4. Google Crew - Finds company triggers (funding, leadership changes)
    5. Aggregation Crew - Deduplicates and merges leads across platforms
    6. Qualification Crew - Scores and prioritizes leads, returns top 10

    Platform crews run sequentially, then Aggregation consolidates,
    and finally Qualification scores and ranks the top 10 leads.
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
        self.emit_event("thought", "Will orchestrate 6 crews: Reddit > LinkedIn > Twitter > Google > Aggregation > Qualification")

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
    def google_prospecting(self, state: ProspectingState):
        """
        Run Google crew to find company triggers.

        Google discovers:
        - Funding announcements
        - Leadership changes
        - Company expansions
        - Problem announcements
        """
        self.emit_event("crew_started", "Google Crew - Finding company triggers...")

        try:
            # Initialize Google crew
            google_crew = GoogleProspectingCrew()

            # Prepare inputs
            inputs = {
                "search_query": state.query,
                "max_results": 30
            }

            self.emit_event("thought", f"Google Crew researching company triggers for: {state.query}")

            # Execute Google crew
            result = google_crew.crew().kickoff(inputs=inputs)

            # Store results
            state.crew_results["google"] = {
                "raw_output": str(result),
                "status": "completed"
            }

            self.emit_event("crew_completed", f"Google Crew finished - Found company triggers")
            return state

        except Exception as e:
            state.crew_results["google"] = {
                "error": str(e),
                "status": "failed"
            }
            self.emit_event("error", f"Google Crew failed: {str(e)}")
            return state

    @listen(google_prospecting)
    def aggregate_results(self, state: ProspectingState):
        """
        Run Aggregation Crew to deduplicate and merge leads.

        Takes raw outputs from all 4 platform crews (LinkedIn, Reddit, Twitter, Google)
        and uses the Aggregation Crew to:
        - Deduplicate leads across platforms
        - Merge duplicate records with consolidated intent signals
        - Categorize leads by tier (1/2/3 based on # of platforms found)
        - Extract company domains
        - Filter low-quality leads
        """
        self.emit_event("crew_started", "Aggregation Crew - Deduplicating and merging leads...")

        try:
            # Initialize Aggregation crew
            aggregation_crew = AggregationCrew()

            # Prepare inputs from all platform crews
            inputs = {
                "linkedin_leads": state.crew_results.get("linkedin", {}).get("raw_output", "No LinkedIn results"),
                "reddit_leads": state.crew_results.get("reddit", {}).get("raw_output", "No Reddit results"),
                "twitter_leads": state.crew_results.get("twitter", {}).get("raw_output", "No Twitter results"),
                "google_leads": state.crew_results.get("google", {}).get("raw_output", "No Google results")
            }

            self.emit_event("thought", "Running deduplication across all platform results...")

            # Execute Aggregation crew
            result = aggregation_crew.crew().kickoff(inputs=inputs)

            # Store deduplicated results
            state.crew_results["aggregation"] = {
                "deduplicated_output": str(result),
                "status": "completed"
            }

            # Parse the aggregated output into structured leads
            # For now, store the full aggregation output as a single "lead" entry
            state.leads = [{
                "aggregated_results": str(result),
                "raw_platform_data": {
                    "reddit": state.crew_results.get("reddit", {}).get("raw_output", ""),
                    "linkedin": state.crew_results.get("linkedin", {}).get("raw_output", ""),
                    "twitter": state.crew_results.get("twitter", {}).get("raw_output", ""),
                    "google": state.crew_results.get("google", {}).get("raw_output", "")
                },
                "timestamp": "now"
            }]

            state.status = "processing"
            self.emit_event("crew_completed", "Aggregation Crew finished - Leads deduplicated")
            self.emit_event("thought", "Moving to qualification...")

            return state

        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            state.crew_results["aggregation"] = {
                "error": str(e),
                "status": "failed"
            }
            self.emit_event("error", f"Aggregation Crew failed: {str(e)}")
            return state

    @listen(aggregate_results)
    def qualify_leads(self, state: ProspectingState):
        """
        Run Qualification Crew to score and prioritize leads.

        Takes deduplicated leads from Aggregation Crew and:
        - Scores each lead against ICP (Ideal Customer Profile)
        - Calculates final quality score (0-100)
        - Prioritizes leads (hot/warm/cold/disqualified)
        - Returns top 10 highest-quality leads
        """
        self.emit_event("crew_started", "Qualification Crew - Scoring and prioritizing leads...")

        try:
            # Initialize Qualification crew
            qualification_crew = QualificationCrew()

            # Prepare inputs from aggregation results
            inputs = {
                "deduplicated_leads": state.crew_results.get("aggregation", {}).get("deduplicated_output", "No deduplicated leads")
            }

            self.emit_event("thought", "Scoring leads against ICP and calculating quality scores...")

            # Execute Qualification crew
            result = qualification_crew.crew().kickoff(inputs=inputs)

            # Store qualified results
            state.crew_results["qualification"] = {
                "qualified_output": str(result),
                "status": "completed"
            }

            # Update leads with qualified results
            state.leads = [{
                "qualified_leads": str(result),
                "aggregated_results": state.crew_results.get("aggregation", {}).get("deduplicated_output", ""),
                "raw_platform_data": state.leads[0].get("raw_platform_data", {}) if state.leads else {},
                "timestamp": "now"
            }]

            state.status = "completed"
            self.emit_event("crew_completed", "Qualification Crew finished - Top 10 leads identified")
            self.emit_event("thought", "Prospecting complete! All 6 crews executed successfully.")
            self.emit_event("thought", "Final pipeline: Reddit > LinkedIn > Twitter > Google > Aggregation > Qualification")

            return state

        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            state.crew_results["qualification"] = {
                "error": str(e),
                "status": "failed"
            }
            self.emit_event("error", f"Qualification Crew failed: {str(e)}")
            return state
