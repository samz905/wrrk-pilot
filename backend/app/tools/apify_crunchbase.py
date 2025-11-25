"""Crunchbase scraping tool using Apify - Find company funding and growth signals."""
import os
from typing import Type, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class ApifyCrunchbaseInput(BaseModel):
    """Input schema for Crunchbase search."""
    keyword: str = Field(..., description="Search keyword (e.g., 'AI startup', 'Series A SaaS')")
    limit: int = Field(default=50, description="Maximum results to return (1-100)")


class ApifyCrunchbaseTool(BaseTool):
    """
    Search Crunchbase for companies with funding and growth signals.

    This tool finds:
    - Recently funded companies (Series A, B, C)
    - Companies in specific industries
    - Startups with growth signals
    - Company funding history and employee counts

    Use this to identify companies that:
    - Have budget (recently raised funding)
    - Are growing (hiring signals)
    - Match your target industry
    """

    name: str = "Crunchbase Company Search"
    description: str = """
    Search Crunchbase for companies with funding and growth signals.

    Use this to find:
    - Recently funded companies (potential budget)
    - Companies in target industries
    - Startups matching your ICP
    - Company funding history

    Input parameters:
    - keyword: Search keywords (e.g., "Series A SaaS", "AI startup funding")
    - limit: Maximum results (default: 50, max: 100)

    Returns for each company:
    - Company name and description
    - Funding information
    - Industry and employee count
    - Founder information (if available)

    Pair with LinkedInEmployeesTool to find decision makers at these companies.
    """
    args_schema: Type[BaseModel] = ApifyCrunchbaseInput

    def _run(
        self,
        keyword: str,
        limit: int = 50
    ) -> str:
        """Execute Crunchbase search and return formatted results."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        print(f"\n[INFO] Searching Crunchbase for: '{keyword}'")
        print(f"[INFO] Max results: {limit}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Check for Crunchbase cookie (required by actor)
        crunchbase_cookie = os.getenv("CRUNCHBASE_COOKIE")
        if not crunchbase_cookie:
            return """Error: CRUNCHBASE_COOKIE not found in environment.

To use the Crunchbase tool, you need to:
1. Log into Crunchbase in your browser
2. Open Developer Tools (F12) > Application > Cookies
3. Copy the full cookie string
4. Add it to your .env file as CRUNCHBASE_COOKIE=<cookie_string>

Alternatively, use Google SERP search for company funding information."""

        # Prepare actor input (curious_coder/crunchbase-scraper)
        # Schema: keyword, sort_type, page_number, date_filter, limit, cookie
        run_input = {
            "keyword": keyword,
            "sort_type": "relevance",
            "page_number": 1,
            "date_filter": "",
            "limit": min(limit, 100),
            "cookie": crunchbase_cookie
        }

        try:
            # Run the actor
            print("[INFO] Running Crunchbase scraper actor...")
            run = client.actor("curious_coder/crunchbase-scraper").call(run_input=run_input)

            # Fetch results from dataset
            print("[INFO] Fetching results...")
            results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            if not results:
                return f"No Crunchbase results found for: '{keyword}'"

            print(f"[OK] Found {len(results)} companies")

            # Format results
            return self._format_results(results, keyword)

        except Exception as e:
            error_msg = f"Error running Crunchbase search: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def _format_results(self, results: List[Dict[str, Any]], keyword: str) -> str:
        """Format Crunchbase results into structured text."""

        output = []
        output.append("=" * 70)
        output.append(f"CRUNCHBASE COMPANY SEARCH: '{keyword}'")
        output.append("=" * 70)
        output.append(f"\nFound {len(results)} companies:\n")

        for idx, company in enumerate(results, 1):
            # Extract company data (field names may vary)
            name = company.get('name', company.get('companyName', 'Unknown'))
            description = company.get('description', company.get('shortDescription', 'N/A'))
            if description and len(description) > 200:
                description = description[:200] + "..."

            industry = company.get('industry', company.get('categories', 'N/A'))
            if isinstance(industry, list):
                industry = ", ".join(industry[:3])

            funding = company.get('totalFunding', company.get('fundingTotal', 'N/A'))
            funding_rounds = company.get('fundingRounds', company.get('numFundingRounds', 'N/A'))
            last_funding = company.get('lastFundingType', company.get('lastFundingRound', 'N/A'))
            last_funding_date = company.get('lastFundingDate', 'N/A')

            employees = company.get('employeeCount', company.get('numEmployees', 'N/A'))
            founded = company.get('foundedYear', company.get('founded', 'N/A'))
            location = company.get('location', company.get('headquarters', 'N/A'))

            website = company.get('website', company.get('websiteUrl', 'N/A'))
            linkedin = company.get('linkedin', company.get('linkedinUrl', 'N/A'))

            output.append(f"Company #{idx}")
            output.append("-" * 70)
            output.append(f"Name: {name}")
            output.append(f"Description: {description}")
            output.append(f"Industry: {industry}")
            output.append(f"\nFunding:")
            output.append(f"  Total: {funding}")
            output.append(f"  Rounds: {funding_rounds}")
            output.append(f"  Last Round: {last_funding} ({last_funding_date})")
            output.append(f"\nCompany Info:")
            output.append(f"  Employees: {employees}")
            output.append(f"  Founded: {founded}")
            output.append(f"  Location: {location}")
            output.append(f"\nLinks:")
            output.append(f"  Website: {website}")
            output.append(f"  LinkedIn: {linkedin}")
            output.append("")

        output.append("=" * 70)
        output.append("\nINSIGHTS:")
        output.append(f"- Total companies found: {len(results)}")

        # Count by funding stage if available
        funded_companies = [c for c in results if c.get('totalFunding') or c.get('fundingTotal')]
        output.append(f"- Companies with funding data: {len(funded_companies)}")

        output.append("=" * 70)

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("CRUNCHBASE TOOL TEST")
    print("=" * 70)

    tool = ApifyCrunchbaseTool()

    # Test search
    result = tool._run(
        keyword="Series A SaaS",
        limit=5
    )

    print("\n" + result)
