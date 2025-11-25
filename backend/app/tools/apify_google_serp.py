"""Google SERP scraping tool using Apify - Find companies discussing problems."""
import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class ApifyGoogleSERPInput(BaseModel):
    """Input schema for Google SERP search."""
    query: str = Field(..., description="Search query (e.g., 'companies complaining about CRM', 'businesses need better analytics')")
    max_results: int = Field(default=10, description="Maximum search results to return (1-100)")
    country: str = Field(default="US", description="Country code for search location (e.g., 'US', 'UK', 'CA')")


class ApifyGoogleSERPTool(BaseTool):
    """
    Search Google for companies and discussions showing intent signals.

    This tool finds:
    - Articles about companies complaining about tools
    - Blog posts discussing problems and pain points
    - Forums where businesses discuss challenges
    - Industry reports about tool limitations

    Returns: Title, URL, description snippet for each result
    """

    name: str = "Google SERP Search"
    description: str = """
    Search Google to find articles, blog posts, and discussions about companies
    experiencing problems or looking for solutions.

    Use this to discover:
    - Industry articles about common pain points
    - Blog posts where companies share their struggles
    - Forum discussions about tool limitations
    - Case studies about switching from competitors

    Input parameters:
    - query: Search keywords (e.g., "companies frustrated with Salesforce")
    - max_results: Number of results to return (default: 10)
    - country: Country for search location (default: "US")

    Returns for each result:
    - Title of the page
    - URL to visit
    - Description snippet showing relevance
    - Position in search results
    """
    args_schema: Type[BaseModel] = ApifyGoogleSERPInput

    def _run(
        self,
        query: str,
        max_results: int = 10,
        country: str = "US"
    ) -> str:
        """Execute Google SERP search and return formatted results."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        print(f"\n[INFO] Searching Google for: '{query}'")
        print(f"[INFO] Max results: {max_results}, Country: {country}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Prepare actor input (apify/google-search-scraper)
        # Schema: queries (newline-separated), resultsPerPage, maxPagesPerQuery, aiMode, etc.
        run_input = {
            "queries": query,  # Single query string (can be newline-separated for multiple)
            "resultsPerPage": min(max_results, 100),
            "maxPagesPerQuery": 1,
            "aiMode": "aiModeOff",
            "forceExactMatch": False
        }

        try:
            # Run the actor
            print("[INFO] Running Google SERP actor...")
            run = client.actor("563JCPLOqM1kMmbbP").call(run_input=run_input)

            # Fetch results from dataset
            print("[INFO] Fetching results...")
            results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            if not results:
                return f"No Google search results found for query: '{query}'"

            # Extract organic results from the response
            all_organic_results = []
            for page in results:
                if 'results' in page and isinstance(page['results'], list):
                    all_organic_results.extend(page['results'])

            if not all_organic_results:
                return f"No organic search results found for query: '{query}'"

            print(f"[OK] Found {len(all_organic_results)} search results")

            # Format results
            formatted_output = []
            formatted_output.append(f"=== GOOGLE SEARCH RESULTS ===")
            formatted_output.append(f"Query: '{query}'")
            formatted_output.append(f"Found: {len(all_organic_results)} results\n")

            for result in all_organic_results[:max_results]:
                position = result.get('position', 'N/A')
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                description = result.get('description', 'No description')

                formatted_output.append(f"--- Result #{position} ---")
                formatted_output.append(f"Title: {title}")
                formatted_output.append(f"URL: {url}")
                formatted_output.append(f"Snippet: {description}")
                formatted_output.append("")

            return "\n".join(formatted_output)

        except Exception as e:
            error_msg = f"Error running Google SERP search: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
