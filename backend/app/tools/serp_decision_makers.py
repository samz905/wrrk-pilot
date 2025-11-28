"""
SERP-Based Decision Maker Finder

Uses Google SERP (via SerperDevTool) to find founders and decision makers
for companies. Much faster than LinkedIn employee scraping (~30-60s vs 6-8 min).

v3.4: Replaces slow LinkedIn employee search for TechCrunch prospecting.
"""
import os
import json
import re
from typing import Type, Optional, List, Dict
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from openai import OpenAI

# Import settings
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings


class SerpDecisionMakersInput(BaseModel):
    """Input schema for SERP decision maker search."""
    company: str = Field(..., description="Company name to search for")
    product_context: str = Field(default="", description="Product context for role targeting (e.g., 'sales tool', 'dev tool')")
    funding_info: str = Field(default="", description="Funding info from TechCrunch (optional)")


class SerpDecisionMakersTool(BaseTool):
    """
    Find founders and decision makers using Google SERP.

    Strategy:
    1. Search "[Company] founders site:linkedin.com" - Get ALL founders
    2. Search "[Company] [role] site:linkedin.com" - Role-specific titles
    3. Parse LinkedIn URLs and names from SERP results
    4. Return decision makers without slow LinkedIn API calls

    Time: ~30-60s vs 6-8 min with LinkedIn employee scraping
    """

    name: str = "serp_decision_makers"
    description: str = """
    Find founders and decision makers using Google SERP. Much faster than LinkedIn.

    Parameters:
    - company: Company name (e.g., "Capsule AI")
    - product_context: Product type for role targeting (e.g., "sales tool", "dev tool")
    - funding_info: Optional funding info for context

    Returns JSON with:
    - decision_makers: Array of {name, title, linkedin_url, company}
    - count: Number found
    """
    args_schema: Type[BaseModel] = SerpDecisionMakersInput

    def _run(
        self,
        company: str,
        product_context: str = "",
        funding_info: str = ""
    ) -> str:
        """
        Find decision makers using SERP queries.
        """
        print(f"\n[SERP_DECISION_MAKERS] Searching for decision makers at {company}...")

        serper_api_key = os.getenv("SERPER_API_KEY")
        if not serper_api_key:
            return json.dumps({
                "error": "SERPER_API_KEY not found",
                "decision_makers": [],
                "count": 0
            })

        # Generate smart queries based on product context
        queries = self._generate_queries(company, product_context)

        all_results = []
        seen_urls = set()

        # Execute SERP queries
        for query in queries:
            try:
                results = self._serp_search(query, serper_api_key)
                for result in results:
                    url = result.get('link', '')
                    if url and 'linkedin.com/in/' in url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(result)
            except Exception as e:
                print(f"[SERP] Query failed: {query} - {e}")
                continue

        # Parse LinkedIn profiles from results
        decision_makers = self._parse_linkedin_results(all_results, company)

        print(f"[SERP_DECISION_MAKERS] Found {len(decision_makers)} decision makers for {company}")

        return json.dumps({
            "decision_makers": decision_makers,
            "count": len(decision_makers),
            "company": company,
            "queries_used": queries
        }, indent=2)

    def _generate_queries(self, company: str, product_context: str) -> List[str]:
        """
        Generate smart SERP queries based on product context.

        Always targets ALL founders + role-specific titles.
        """
        queries = [
            f'"{company}" founder site:linkedin.com/in/',
            f'"{company}" CEO site:linkedin.com/in/',
            f'"{company}" co-founder site:linkedin.com/in/',
        ]

        # Add role-specific queries based on product context
        context_lower = product_context.lower()

        if any(word in context_lower for word in ['sales', 'crm', 'revenue', 'outbound']):
            queries.extend([
                f'"{company}" "head of sales" site:linkedin.com/in/',
                f'"{company}" "VP sales" site:linkedin.com/in/',
            ])
        elif any(word in context_lower for word in ['dev', 'engineering', 'platform', 'api', 'code']):
            queries.extend([
                f'"{company}" CTO site:linkedin.com/in/',
                f'"{company}" "VP engineering" site:linkedin.com/in/',
            ])
        elif any(word in context_lower for word in ['marketing', 'growth', 'brand']):
            queries.extend([
                f'"{company}" CMO site:linkedin.com/in/',
                f'"{company}" "head of marketing" site:linkedin.com/in/',
            ])
        elif any(word in context_lower for word in ['hr', 'people', 'talent', 'recruit']):
            queries.extend([
                f'"{company}" "head of people" site:linkedin.com/in/',
                f'"{company}" "VP HR" site:linkedin.com/in/',
            ])
        else:
            # Default: add COO and general decision makers
            queries.extend([
                f'"{company}" COO site:linkedin.com/in/',
                f'"{company}" CTO site:linkedin.com/in/',
            ])

        return queries[:6]  # Limit to 6 queries to keep it fast

    def _serp_search(self, query: str, api_key: str) -> List[Dict]:
        """
        Execute a SERP search via Serper.dev API.
        """
        import requests

        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": 5  # Get top 5 results per query
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        return data.get("organic", [])

    def _parse_linkedin_results(self, results: List[Dict], company: str) -> List[Dict]:
        """
        Parse LinkedIn profile info from SERP results.
        """
        decision_makers = []
        seen_names = set()

        for result in results:
            url = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')

            if 'linkedin.com/in/' not in url:
                continue

            # Extract name from title (usually "Name - Title - Company | LinkedIn")
            name = self._extract_name_from_title(title)
            if not name or name in seen_names:
                continue

            seen_names.add(name)

            # Extract title from snippet or title
            role = self._extract_role(title, snippet)

            decision_makers.append({
                "name": name,
                "title": role,
                "linkedin_url": url,
                "company": company,
                "source": "serp"
            })

        return decision_makers

    def _extract_name_from_title(self, title: str) -> Optional[str]:
        """
        Extract name from LinkedIn SERP title.
        Format is usually: "Name - Title - Company | LinkedIn"
        """
        if not title:
            return None

        # Remove "| LinkedIn" suffix
        title = title.replace("| LinkedIn", "").replace("- LinkedIn", "").strip()

        # Split by " - " and take first part as name
        parts = title.split(" - ")
        if parts:
            name = parts[0].strip()
            # Basic validation: name should be 2-4 words
            words = name.split()
            if 1 <= len(words) <= 4:
                return name

        return None

    def _extract_role(self, title: str, snippet: str) -> str:
        """
        Extract role/title from SERP result.
        """
        # Try to extract from title first
        title = title.replace("| LinkedIn", "").strip()
        parts = title.split(" - ")

        if len(parts) >= 2:
            role = parts[1].strip()
            if role and len(role) < 100:
                return role

        # Fallback: try to extract from snippet
        role_patterns = [
            r'(CEO|CTO|COO|CFO|CMO|Founder|Co-Founder|Head of \w+|VP \w+|Director)',
        ]
        for pattern in role_patterns:
            match = re.search(pattern, snippet, re.IGNORECASE)
            if match:
                return match.group(1)

        return "Decision Maker"


class SerpDecisionMakersBatchTool(BaseTool):
    """
    Find decision makers for multiple companies in batch.

    More efficient when processing multiple TechCrunch companies.
    """

    name: str = "serp_decision_makers_batch"
    description: str = """
    Find decision makers for multiple companies in batch.

    Parameters:
    - companies: List of {name, funding, description} dicts
    - product_context: Product type for role targeting

    Returns JSON with decision_makers grouped by company.
    """
    args_schema: Type[BaseModel] = BaseModel  # Will accept any dict

    def _run(self, companies: List[Dict], product_context: str = "") -> str:
        """
        Find decision makers for multiple companies.
        """
        if not companies:
            return json.dumps({
                "error": "No companies provided",
                "results": {}
            })

        print(f"\n[SERP_BATCH] Finding decision makers for {len(companies)} companies...")

        single_tool = SerpDecisionMakersTool()
        results = {}

        for company_data in companies:
            company_name = company_data.get('name', company_data.get('company', ''))
            if not company_name:
                continue

            funding = company_data.get('funding', '')
            description = company_data.get('description', '')

            result_str = single_tool._run(
                company=company_name,
                product_context=product_context,
                funding_info=funding
            )

            result = json.loads(result_str)
            results[company_name] = result.get('decision_makers', [])

        total_found = sum(len(dms) for dms in results.values())
        print(f"[SERP_BATCH] Found {total_found} total decision makers across {len(companies)} companies")

        return json.dumps({
            "results": results,
            "total_decision_makers": total_found,
            "companies_searched": len(companies)
        }, indent=2)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SERP DECISION MAKERS TEST")
    print("=" * 70)

    tool = SerpDecisionMakersTool()
    result = tool._run(
        company="Capsule AI",
        product_context="video editor tool",
        funding_info="$12M Series A"
    )
    print("\nResult:")
    print(result)
