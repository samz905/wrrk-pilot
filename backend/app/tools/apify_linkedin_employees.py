"""LinkedIn Employees Search tool - Find decision makers at a company."""
import os
import json
from typing import Type, List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
from openai import OpenAI

# Centralized config for models
from app.core.config import settings


class LinkedInEmployeesSearchInput(BaseModel):
    """Input schema for LinkedIn employees search."""
    company_url: str = Field(..., description="LinkedIn company URL (e.g., 'https://www.linkedin.com/company/google/')")
    query: str = Field(..., description="Search context for finding relevant employees (e.g., 'engineering managers')")
    max_employees: int = Field(default=50, description="Maximum employees to fetch (max 100)")
    return_json: bool = Field(default=False, description="If True, return JSON instead of formatted text (for tool chaining)")


class LinkedInEmployeesSearchTool(BaseTool):
    """
    Find decision makers at a specific company based on search context.

    This tool fetches employees from a LinkedIn company page and filters
    them based on the query to find relevant decision makers.
    """

    name: str = "LinkedIn Decision Makers Search"
    description: str = """
    Find decision makers at a specific company based on search context.

    Input parameters:
    - company_url: LinkedIn company URL (e.g., "https://www.linkedin.com/company/google/")
    - query: Search context (e.g., "engineering managers", "VP of Sales", "CRM decision makers")
    - max_employees: Maximum employees to fetch (default: 50, max: 100)

    Returns list of decision makers with:
    - Name, title, and profile URL
    - Relevance score based on query match
    - Fit reasoning for the search context

    Use this when you have a company name/URL and want to find the right
    people to contact based on your search query.
    """
    args_schema: Type[BaseModel] = LinkedInEmployeesSearchInput

    def _run(
        self,
        company_url: str,
        query: str,
        max_employees: int = 50,
        return_json: bool = False
    ) -> str:
        """
        Execute LinkedIn employees search workflow.

        Args:
            company_url: LinkedIn company URL
            query: Search context for filtering employees
            max_employees: Maximum employees to fetch
            return_json: If True, return JSON instead of formatted text

        Returns:
            Formatted string or JSON with decision makers
        """
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            if return_json:
                return json.dumps({"employees": [], "error": "APIFY_API_TOKEN not found"})
            return "Error: APIFY_API_TOKEN not found in environment"

        print(f"\n[INFO] LinkedIn Decision Makers Search")
        print(f"[INFO] Company URL: {company_url}")
        print(f"[INFO] Search Context: '{query}'")
        print(f"[INFO] Max Employees: {max_employees}")

        try:
            # STEP 1: Fetch employees from company
            employees = self._fetch_company_employees(
                apify_token,
                company_url,
                max_employees
            )

            if not employees:
                if return_json:
                    return json.dumps({"employees": [], "count": 0, "company_url": company_url})
                return f"No employees found at company: {company_url}"

            print(f"[INFO] Fetched {len(employees)} employees from company")

            # STEP 2: Score and filter employees by relevance to query
            scored_employees = self._score_employees(query, employees)

            # STEP 3: Return results (JSON or formatted text)
            if return_json:
                return json.dumps({
                    "employees": scored_employees,
                    "count": len(scored_employees),
                    "company_url": company_url,
                    "query": query
                })
            return self._format_results(scored_employees, query, company_url)

        except Exception as e:
            error_msg = f"Error in LinkedIn employees search: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            if return_json:
                return json.dumps({"employees": [], "error": str(e)})
            return error_msg

    def _fetch_company_employees(
        self,
        apify_token: str,
        company_url: str,
        max_employees: int
    ) -> List[Dict]:
        """
        Fetch employees from a LinkedIn company page.

        Uses Apify actor cIdqlEvw6afc1do1p (harvestapi/linkedin-company-employees)

        Args:
            apify_token: Apify API token
            company_url: LinkedIn company URL
            max_employees: Maximum employees to fetch

        Returns:
            List of employee dictionaries
        """
        client = ApifyClient(apify_token)

        # Prepare actor input
        run_input = {
            "identifier": company_url,
            "max_employees": min(max_employees, 100),
            "job_title": "",  # Leave empty, we'll filter with LLM
        }

        # Debug logging
        print(f"[DEBUG] Apify run_input: {json.dumps(run_input, indent=2)}")
        print(f"[DEBUG] Calling Apify actor cIdqlEvw6afc1do1p (LinkedIn Company Employees)...")

        try:
            # Run the actor
            run = client.actor("cIdqlEvw6afc1do1p").call(run_input=run_input)
            print(f"[DEBUG] Apify run completed, dataset: {run.get('defaultDatasetId', 'N/A')}")

            # Fetch results
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[DEBUG] Apify returned {len(results)} employees")

            if results:
                print(f"[DEBUG] First employee keys: {list(results[0].keys())}")

            return results

        except Exception as e:
            print(f"[ERROR] Apify failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _score_employees(
        self,
        query: str,
        employees: List[Dict]
    ) -> List[Dict]:
        """
        Score employees by relevance to the search query.

        Uses structured outputs for guaranteed valid JSON response.

        Args:
            query: Search context
            employees: List of employee data

        Returns:
            List of scored employees (sorted by relevance)
        """
        if not employees:
            return []

        # Build employee list for LLM analysis
        employees_text = ""
        for i, emp in enumerate(employees, 1):
            name = emp.get('name', emp.get('firstName', '') + ' ' + emp.get('lastName', '')).strip() or 'Unknown'
            title = emp.get('headline', emp.get('title', emp.get('jobTitle', 'N/A')))
            profile_url = emp.get('linkedinUrl', emp.get('profileUrl', emp.get('url', 'N/A')))

            employees_text += f"\n{i}. Name: {name}"
            employees_text += f"\n   Title: {title}"
            employees_text += f"\n   URL: {profile_url}\n"

        prompt = f"""Analyze these LinkedIn employees and score them for relevance to: "{query}"

EMPLOYEES:
{employees_text}

For EACH employee, determine if they are a good match for the search context "{query}".

Consider:
1. Job title relevance - Do they have authority over the query topic?
2. Decision-making authority - Are they in a position to make buying decisions?
3. Seniority level - VP, Director, Manager roles are often decision makers

Scoring:
- 80-100: Perfect match (direct decision maker for the query topic)
- 60-79: Good match (related role with likely influence)
- 40-59: Possible match (could be involved in decisions)
- 20-39: Weak match (tangentially related)
- 0-19: No match (irrelevant role)

Return only the TOP 20 most relevant employees (score >= 40)."""

        # JSON schema for structured output
        json_schema = {
            "name": "employee_scores",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "employees": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "employee_number": {"type": "integer"},
                                "name": {"type": "string"},
                                "title": {"type": "string"},
                                "profile_url": {"type": "string"},
                                "relevance_score": {"type": "integer"},
                                "fit_reasoning": {"type": "string"}
                            },
                            "required": ["employee_number", "name", "title", "profile_url", "relevance_score", "fit_reasoning"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["employees"],
                "additionalProperties": False
            }
        }

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            print(f"[INFO] Scoring {len(employees)} employees with structured output...")

            response = client.chat.completions.create(
                model=settings.TOOL_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at identifying decision makers in organizations."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
                max_completion_tokens=3000
            )

            result = json.loads(response.choices[0].message.content)
            scored = result.get("employees", [])

            # Sort by relevance score
            scored.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            print(f"[INFO] Scored and filtered to {len(scored)} relevant decision makers (structured)")
            return scored

        except Exception as e:
            print(f"[ERROR] Structured employee scoring failed: {e}")
            import traceback
            traceback.print_exc()

            # Fallback: score based on title keywords
            print(f"[INFO] Using title-based fallback scoring...")
            fallback_scored = []
            decision_maker_keywords = ['founder', 'ceo', 'cto', 'coo', 'cfo', 'chief', 'president',
                                       'vp', 'vice president', 'director', 'head of', 'manager', 'lead']

            for i, emp in enumerate(employees, 1):
                name = emp.get('name', emp.get('firstName', '') + ' ' + emp.get('lastName', '')).strip() or 'Unknown'
                title = emp.get('headline', emp.get('title', emp.get('jobTitle', 'N/A'))).lower()
                profile_url = emp.get('linkedinUrl', emp.get('profileUrl', emp.get('url', 'N/A')))

                # Calculate score based on keywords
                score = 30  # Base score
                for keyword in decision_maker_keywords:
                    if keyword in title:
                        score = min(score + 20, 90)
                        break

                if score >= 40:
                    fallback_scored.append({
                        "employee_number": i,
                        "name": name,
                        "title": emp.get('headline', emp.get('title', emp.get('jobTitle', 'N/A'))),
                        "profile_url": profile_url,
                        "relevance_score": score,
                        "fit_reasoning": "[FALLBACK] Title contains decision-maker keywords"
                    })

            fallback_scored.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            print(f"[INFO] Fallback scoring found {len(fallback_scored)} potential decision makers")
            return fallback_scored[:20]

    def _format_results(
        self,
        employees: List[Dict],
        query: str,
        company_url: str
    ) -> str:
        """
        Format scored employees into readable output.

        Args:
            employees: List of scored employee dictionaries
            query: Search query
            company_url: Company URL

        Returns:
            Formatted string output
        """
        output = []
        output.append("=" * 70)
        output.append(f"LINKEDIN DECISION MAKERS: '{query}'")
        output.append(f"Company: {company_url}")
        output.append("=" * 70)

        if not employees:
            return "\n".join(output) + "\n\nNo relevant decision makers found for this query."

        output.append(f"\nFound {len(employees)} relevant decision makers:\n")

        for idx, emp in enumerate(employees, 1):
            score = emp.get('relevance_score', 0)
            score_emoji = self._get_score_emoji(score)

            output.append(f"DECISION MAKER #{idx}")
            output.append("-" * 70)
            output.append(f"Name: {emp.get('name', 'Unknown')}")
            output.append(f"Title: {emp.get('title', 'N/A')}")
            output.append(f"LinkedIn: {emp.get('profile_url', 'N/A')}")
            output.append(f"\nRelevance Score: {score}/100 {score_emoji}")
            output.append(f"\nFit Reasoning:")
            output.append(f"  {emp.get('fit_reasoning', 'N/A')}")
            output.append("")

        output.append("=" * 70)
        output.append("\nINSIGHTS:")
        output.append(f"- Total decision makers found: {len(employees)}")
        avg_score = sum(emp.get('relevance_score', 0) for emp in employees) / len(employees) if employees else 0
        output.append(f"- Average relevance score: {avg_score:.1f}/100")

        # Count high-relevance (>= 80)
        high_relevance = sum(1 for emp in employees if emp.get('relevance_score', 0) >= 80)
        output.append(f"- High-relevance (>=80): {high_relevance}")

        output.append("=" * 70)

        return "\n".join(output)

    def _get_score_emoji(self, score: int) -> str:
        """Get emoji for relevance score level."""
        if score >= 80:
            return "🎯"
        elif score >= 60:
            return "🟢"
        elif score >= 40:
            return "🟡"
        else:
            return "🔵"


# === BATCH EMPLOYEES SEARCH (PARALLEL) ===

class LinkedInEmployeesBatchSearchInput(BaseModel):
    """Input schema for batch LinkedIn employees search."""
    companies: List[Dict] = Field(
        ...,
        description="List of companies with 'url' and 'name' keys"
    )
    query: str = Field(
        ...,
        description="Search context for finding relevant employees (e.g., 'Founder, CEO, CTO')"
    )
    max_employees_per_company: int = Field(
        default=10,
        description="Maximum employees to fetch per company"
    )


class LinkedInEmployeesBatchSearchTool(BaseTool):
    """
    Find decision makers at MULTIPLE companies in PARALLEL.

    This is much faster than calling linkedin_employees_search multiple times
    because it processes all companies concurrently.
    """

    name: str = "linkedin_employees_batch_search"
    description: str = """
    Find decision makers at MULTIPLE companies in PARALLEL.

    MUCH FASTER than calling linkedin_employees_search multiple times!
    Processes all companies concurrently (~2 min total vs ~2 min per company).

    Input parameters:
    - companies: List of dicts with 'url' and 'name' keys
      Example: [{"url": "https://linkedin.com/company/acme/", "name": "Acme Corp"}]
    - query: Search context (e.g., "Founder, CEO, CTO, Head of Product")
    - max_employees_per_company: Max employees per company (default: 10)

    Returns employees_by_company dict ready for techcrunch_select_decision_makers.

    USE THIS instead of calling linkedin_employees_search in a loop!
    """
    args_schema: Type[BaseModel] = LinkedInEmployeesBatchSearchInput

    def _run(
        self,
        companies: List[Dict],
        query: str,
        max_employees_per_company: int = 10
    ) -> str:
        """Execute parallel LinkedIn employees search for multiple companies."""
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return json.dumps({"employees_by_company": {}, "error": "APIFY_API_TOKEN not found"})

        print(f"\n[LINKEDIN_BATCH_EMPLOYEES] Searching {len(companies)} companies in PARALLEL...")

        # Use the single-company tool for actual fetching
        single_tool = LinkedInEmployeesSearchTool()

        employees_by_company = {}
        errors = []

        def fetch_company(company: Dict) -> tuple:
            """Fetch employees for a single company (runs in thread)."""
            url = company.get('url', '')
            name = company.get('name', 'Unknown')

            if not url:
                return name, [], f"No URL for {name}"

            try:
                result_json = single_tool._run(
                    company_url=url,
                    query=query,
                    max_employees=max_employees_per_company,
                    return_json=True
                )
                result = json.loads(result_json)
                employees = result.get('employees', [])
                return name, employees, None
            except Exception as e:
                return name, [], str(e)

        # Run all fetches in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_company, c): c for c in companies}

            for future in as_completed(futures):
                company = futures[future]
                try:
                    name, employees, error = future.result()
                    if error:
                        errors.append(f"{name}: {error}")
                        print(f"[LINKEDIN_BATCH_EMPLOYEES] Error for {name}: {error}")
                    else:
                        employees_by_company[name] = employees
                        print(f"[LINKEDIN_BATCH_EMPLOYEES] Got {len(employees)} employees from {name}")
                except Exception as e:
                    errors.append(f"{company.get('name', 'Unknown')}: {str(e)}")

        total_employees = sum(len(emps) for emps in employees_by_company.values())
        print(f"[LINKEDIN_BATCH_EMPLOYEES] Done. {total_employees} employees from {len(employees_by_company)} companies")

        return json.dumps({
            "employees_by_company": employees_by_company,
            "total_employees": total_employees,
            "companies_searched": len(employees_by_company),
            "errors": errors if errors else None,
            "done": f"Found {total_employees} employees across {len(employees_by_company)} companies",
            "next": "Call techcrunch_select_decision_makers with employees_by_company to pick the right contacts"
        })


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LINKEDIN DECISION MAKERS TOOL TEST")
    print("=" * 70)

    tool = LinkedInEmployeesSearchTool()

    # Test with a company
    result = tool._run(
        company_url="https://www.linkedin.com/company/google/",
        query="engineering managers",
        max_employees=20
    )

    print("\n" + result)
