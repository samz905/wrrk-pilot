"""Apify LinkedIn scraping tools."""
from typing import Type, Optional, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
import os


class LinkedInSearchInput(BaseModel):
    """Input schema for LinkedIn profile search."""
    keywords: str = Field(..., description="Search keywords (job titles, skills, pain points)")
    location: Optional[str] = Field(None, description="Geographic location filter")
    max_results: int = Field(default=50, description="Maximum profiles to return (max 100)")


class ApifyLinkedInSearchTool(BaseTool):
    """Search LinkedIn for profiles matching specific criteria."""

    name: str = "LinkedIn Profile Search"
    description: str = """
    Search LinkedIn for professionals matching specific criteria.
    Use this when you need to find decision-makers in target companies or
    people discussing specific topics/pain points. Returns LinkedIn profile
    URLs and basic information (name, title, company).

    Example usage:
    - keywords: "VP Sales new hire"
    - keywords: "CTO posted about CRM problems"
    - keywords: "Marketing Director looking for analytics"
    """
    args_schema: Type[BaseModel] = LinkedInSearchInput

    def _run(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_results: int = 50
    ) -> str:
        """Execute LinkedIn search via Apify."""
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token:
                return "Error: APIFY_API_TOKEN not found in environment"

            print(f"\n[INFO] Starting LinkedIn search for: '{keywords}' in {location or 'Worldwide'}")

            # Initialize Apify client
            client = ApifyClient(apify_token)

            # Prepare Actor input according to harvestapi/linkedin-profile-search docs
            run_input = {
                "profileScraperMode": "Full",
                "searchQuery": keywords,
                "maxItems": min(max_results, 100),
                "locations": [location] if location else [],
                "currentCompanies": [],
                "pastCompanies": [],
                "schools": [],
                "currentJobTitles": [],
                "pastJobTitles": [],
                "startPage": 1,
            }

            print(f"[INFO] Calling Apify actor M2FMdjRVeF1HPGFcc...")

            # Run the Actor and wait for it to finish
            run = client.actor("M2FMdjRVeF1HPGFcc").call(run_input=run_input)

            print(f"[INFO] Actor run completed. Fetching results...")

            # Fetch results from the run's dataset
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[INFO] Found {len(results)} profiles")

            # Debug: Print first result to see actual field names
            if results:
                print(f"\n[DEBUG] First result keys: {list(results[0].keys())}\n")

            return self._format_results(results)

        except Exception as e:
            return f"Error executing LinkedIn search: {str(e)}"

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format LinkedIn profile data into structured text."""
        if not results:
            return "No profiles found matching the search criteria."

        formatted_leads = []

        for idx, profile in enumerate(results, 1):
            # Extract name
            first_name = profile.get('firstName', '')
            last_name = profile.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip() or 'N/A'

            # Extract location
            location_data = profile.get('location', {})
            if isinstance(location_data, dict):
                location = location_data.get('linkedinText', 'N/A')
            else:
                location = 'N/A'

            # Extract company from currentPosition
            current_position = profile.get('currentPosition', {})
            company = current_position.get('companyName', 'N/A') if isinstance(current_position, dict) else 'N/A'

            # Extract summary (first 200 chars)
            about = profile.get('about', '')
            summary = (about[:200] + '...') if about and len(about) > 200 else (about or 'N/A')

            lead = f"""
Lead #{idx}:
- Name: {full_name}
- Title: {profile.get('headline', 'N/A')}
- Company: {company}
- Location: {location}
- LinkedIn URL: {profile.get('linkedinUrl', 'N/A')}
- Connections: {profile.get('connectionsCount', 'N/A')}
- Summary: {summary}
"""
            formatted_leads.append(lead.strip())

        summary = f"Found {len(results)} LinkedIn profiles:\n\n"
        summary += "\n\n".join(formatted_leads)

        return summary
