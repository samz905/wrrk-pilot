"""Comprehensive LinkedIn prospecting tool - Orchestrates all LinkedIn capabilities."""
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Import all LinkedIn tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from apify_linkedin import ApifyLinkedInSearchTool
from apify_linkedin_posts import ApifyLinkedInPostsSearchTool
from apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool


class LinkedInComprehensiveInput(BaseModel):
    """Input schema for comprehensive LinkedIn prospecting."""
    action: str = Field(..., description="Action to perform: 'find_people', 'find_intent', or 'enrich_profile'")
    query: str = Field(..., description="Search query or profile URL depending on action")
    location: Optional[str] = Field(None, description="Location filter (for find_people only)")
    max_results: int = Field(default=20, description="Maximum results to return")


class LinkedInComprehensiveTool(BaseTool):
    """
    Comprehensive LinkedIn prospecting tool with 3 capabilities:

    1. find_people: Search for people by title/role (people search)
    2. find_intent: Search for posts showing buying signals (intent detection)
    3. enrich_profile: Get detailed profile data including email (enrichment)

    This orchestrates 3 Apify actors to provide complete lead intelligence.
    """

    name: str = "LinkedIn Comprehensive Prospecting"
    description: str = """
    Complete LinkedIn prospecting system with 3 modes:

    MODE 1: find_people
    - Find people by job title, company, location
    - Example: action='find_people', query='VP Sales', location='San Francisco'
    - Returns: Profile URLs and basic info

    MODE 2: find_intent
    - Find posts showing buying signals and problems
    - Example: action='find_intent', query='frustrated with Salesforce'
    - Returns: Posts with author info and intent signals

    MODE 3: enrich_profile
    - Deep scrape profile for email and detailed data
    - Example: action='enrich_profile', query='https://www.linkedin.com/in/john-smith'
    - Returns: Email, phone, full profile data

    Use MODE 2 (find_intent) for TRUE prospecting based on real problems.
    Use MODE 1 (find_people) to find decision-makers by title.
    Use MODE 3 (enrich_profile) to get contact info for high-priority leads.
    """
    args_schema: Type[BaseModel] = LinkedInComprehensiveInput

    def __init__(self):
        super().__init__()
        # Initialize the three underlying tools
        self.people_search = ApifyLinkedInSearchTool()
        self.posts_search = ApifyLinkedInPostsSearchTool()
        self.profile_detail = ApifyLinkedInProfileDetailTool()

    def _run(
        self,
        action: str,
        query: str,
        location: Optional[str] = None,
        max_results: int = 20
    ) -> str:
        """Execute the requested LinkedIn action."""

        print(f"\n[COMPREHENSIVE TOOL] Action: {action}, Query: {query}")

        if action == "find_people":
            # Use people search
            return self.people_search._run(
                keywords=query,
                location=location,
                max_results=max_results
            )

        elif action == "find_intent":
            # Use posts search for intent signals
            return self.posts_search._run(
                query=query,
                max_results=max_results
            )

        elif action == "enrich_profile":
            # Use profile detail scraper
            return self.profile_detail._run(
                profile_url=query
            )

        else:
            return f"Error: Unknown action '{action}'. Valid actions: 'find_people', 'find_intent', 'enrich_profile'"


# Export all tools for direct use
__all__ = [
    'LinkedInComprehensiveTool',
    'ApifyLinkedInSearchTool',
    'ApifyLinkedInPostsSearchTool',
    'ApifyLinkedInProfileDetailTool'
]
