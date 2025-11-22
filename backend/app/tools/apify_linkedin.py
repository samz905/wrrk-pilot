"""Apify LinkedIn scraping tools."""
from typing import Type, Optional, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx
import time
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

            # Build Apify input
            actor_input = {
                "startUrls": [],
                "searchKeywords": keywords,
                "maxResults": min(max_results, 100)  # Cap at 100 for MVP
            }

            if location:
                actor_input["locations"] = [location]

            # Start Apify actor run
            response = httpx.post(
                "https://api.apify.com/v2/acts/apify~linkedin-profile-scraper/runs",
                params={"token": apify_token},
                json=actor_input,
                timeout=30.0
            )

            if response.status_code != 201:
                return f"Error starting Apify actor: {response.text}"

            run_data = response.json()
            run_id = run_data["data"]["id"]

            # Poll for completion (max 5 minutes)
            max_polls = 60
            poll_count = 0

            while poll_count < max_polls:
                time.sleep(5)  # Wait 5 seconds between polls

                status_response = httpx.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    params={"token": apify_token},
                    timeout=10.0
                )

                if status_response.status_code != 200:
                    return f"Error checking run status: {status_response.text}"

                status_data = status_response.json()
                status = status_data["data"]["status"]

                if status == "SUCCEEDED":
                    # Fetch results
                    return self._fetch_results(run_id, apify_token)
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    return f"Apify actor run {status}: {status_data.get('data', {}).get('statusMessage', 'Unknown error')}"

                poll_count += 1

            return "Error: Apify actor run timed out after 5 minutes"

        except Exception as e:
            return f"Error executing LinkedIn search: {str(e)}"

    def _fetch_results(self, run_id: str, token: str) -> str:
        """Fetch and format results from completed Apify run."""
        try:
            results_response = httpx.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items",
                params={"token": token},
                timeout=30.0
            )

            if results_response.status_code != 200:
                return f"Error fetching results: {results_response.text}"

            results = results_response.json()
            return self._format_results(results)

        except Exception as e:
            return f"Error fetching results: {str(e)}"

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format LinkedIn profile data into structured text."""
        if not results:
            return "No profiles found matching the search criteria."

        formatted_leads = []

        for idx, profile in enumerate(results, 1):
            lead = f"""
Lead #{idx}:
- Name: {profile.get('fullName', 'N/A')}
- Title: {profile.get('title', 'N/A')}
- Company: {profile.get('company', 'N/A')}
- Location: {profile.get('location', 'N/A')}
- LinkedIn URL: {profile.get('url', 'N/A')}
- Connections: {profile.get('connectionsCount', 'N/A')}
"""
            formatted_leads.append(lead.strip())

        summary = f"Found {len(results)} LinkedIn profiles:\n\n"
        summary += "\n\n".join(formatted_leads)

        return summary
