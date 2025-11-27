"""
DecisionMakerFinderTool - Find decision makers at target companies.

This composite tool searches LinkedIn for decision makers at specified companies,
then enriches the profiles with relevant details.
"""
import os
import json
from typing import Type, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Import atomic tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apify_linkedin_employees import LinkedInEmployeesSearchTool


# Default decision-maker titles (defined outside class to avoid Pydantic issues)
DEFAULT_DECISION_MAKER_TITLES = [
    "CEO", "CTO", "CFO", "COO", "CMO",
    "VP", "Vice President",
    "Director",
    "Head of",
    "Chief",
    "Founder", "Co-Founder",
    "Owner", "Partner"
]


class DecisionMakerFinderInput(BaseModel):
    """Input schema for decision maker finding."""
    companies: List[str] = Field(..., description="List of company names or LinkedIn company URLs to search")
    titles: Optional[List[str]] = Field(
        default=None,
        description="Job titles to search for (e.g., ['CEO', 'VP Sales', 'CTO']). Default: common decision-maker titles"
    )
    max_per_company: int = Field(default=10, description="Maximum decision makers per company (default: 10)")


class DecisionMakerFinderTool(BaseTool):
    """
    Find decision makers at target companies using LinkedIn.

    This tool:
    1. Searches LinkedIn for employees at each company
    2. Filters by decision-maker titles (VP, Director, C-level, Head of)
    3. Returns enriched profiles with contact details
    4. Supports parallel search across multiple companies

    Use after CompanyTriggerScannerTool to find contacts at promising companies.
    """

    name: str = "Decision Maker Finder"
    description: str = """
    Find decision makers at target companies using LinkedIn.

    This composite tool:
    1. Searches LinkedIn employees at specified companies
    2. Filters by decision-maker titles (VP, Director, C-level)
    3. Returns detailed profiles for outreach
    4. Processes multiple companies in PARALLEL for speed

    Input parameters:
    - companies: List of company names or LinkedIn URLs
    - titles: Job titles to search (default: decision-maker titles)
    - max_per_company: Max results per company (default: 10)

    Returns for each decision maker:
    - Name, title, company
    - LinkedIn profile URL
    - Location and experience
    - Connection degree

    WORKFLOW: Use after CompanyTriggerScannerTool to find contacts at hot companies.
    """
    args_schema: Type[BaseModel] = DecisionMakerFinderInput

    def _run(
        self,
        companies: List[str],
        titles: Optional[List[str]] = None,
        max_per_company: int = 10
    ) -> str:
        """
        Execute decision maker search across companies.
        """
        print(f"\n[INFO] Decision Maker Finder starting for {len(companies)} companies")

        if titles is None:
            titles = DEFAULT_DECISION_MAKER_TITLES

        print(f"[INFO] Target titles: {titles[:5]}...")
        print(f"[INFO] Max per company: {max_per_company}")

        # Create tool instance on demand
        linkedin_employees_tool = LinkedInEmployeesSearchTool()

        def search_company_employees(company: str, titles: List[str], max_results: int) -> str:
            """Search for employees at a specific company."""
            # Build title filter for search query
            title_filter = " OR ".join(titles[:5])  # Limit to 5 for query length

            # If company is not a LinkedIn URL, construct one
            if "linkedin.com" in company.lower():
                company_url = company
            else:
                # Construct LinkedIn company URL from name
                company_slug = company.lower().replace(" ", "-").replace(",", "")
                company_url = f"https://www.linkedin.com/company/{company_slug}/"

            return linkedin_employees_tool._run(
                company_url=company_url,
                query=title_filter,
                max_employees=max_results
            )

        # Execute parallel searches (up to 3 concurrent)
        all_results = {}
        errors = []

        with ThreadPoolExecutor(max_workers=min(3, len(companies))) as executor:
            futures = {}

            for company in companies:
                futures[executor.submit(
                    search_company_employees,
                    company,
                    titles,
                    max_per_company
                )] = company

            # Collect results
            for future in as_completed(futures):
                company = futures[future]
                try:
                    result = future.result()
                    all_results[company] = result
                    print(f"[OK] {company} search completed")
                except Exception as e:
                    errors.append(f"{company}: {str(e)}")
                    print(f"[ERROR] {company} search failed: {str(e)}")

        # Format combined results
        return self._format_combined_results(all_results, errors, titles)

    def _format_combined_results(
        self,
        results: Dict[str, str],
        errors: List[str],
        titles: List[str]
    ) -> str:
        """
        Format combined decision maker results.
        """
        output = []
        output.append("=" * 70)
        output.append("DECISION MAKERS FOUND")
        output.append("=" * 70)
        output.append(f"\nCompanies searched: {len(results) + len(errors)}")
        output.append(f"Successful: {len(results)}")
        if errors:
            output.append(f"Failed: {len(errors)}")
            for error in errors:
                output.append(f"  - {error}")
        output.append("")

        # Add results from each company
        for company, result in results.items():
            output.append(f"\n{'='*30} {company.upper()[:30]} {'='*30}")
            output.append(result)
            output.append("")

        output.append("=" * 70)
        output.append("\nOUTREACH RECOMMENDATIONS:")
        output.append("1. Prioritize C-level and VP contacts")
        output.append("2. Check for shared connections")
        output.append("3. Review recent activity for conversation starters")
        output.append("4. Use LeadScorerTool to prioritize contacts")
        output.append("=" * 70)

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DECISION MAKER FINDER TEST")
    print("=" * 70)

    tool = DecisionMakerFinderTool()

    # Test with a company
    result = tool._run(
        companies=["Anthropic"],
        titles=["CEO", "CTO", "VP Engineering"],
        max_per_company=5
    )

    print("\n" + result)
