"""LinkedIn Company Search tool - Find company LinkedIn URLs reliably."""
import os
import json
from typing import Type, List, Dict, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
from openai import OpenAI


# === Structured Output Models ===

class CompanyMatch(BaseModel):
    """A matched company from search results."""
    company_name: str = Field(description="Original company name searched")
    linkedin_url: str = Field(description="LinkedIn company URL")
    matched_name: str = Field(description="Name as it appears on LinkedIn")
    confidence: str = Field(description="high, medium, or low")
    reason: str = Field(description="Why this match was selected")


class CompanyMatchList(BaseModel):
    """List of matched companies."""
    matches: List[CompanyMatch]


class LinkedInCompanySearchInput(BaseModel):
    """Input schema for LinkedIn company search."""
    company_name: str = Field(..., description="Company name to search for")
    context: str = Field(default="", description="Additional context (e.g., 'AI startup', 'recently funded')")


class LinkedInCompanyBatchSearchInput(BaseModel):
    """Input schema for batch LinkedIn company search."""
    companies: List[Dict] = Field(..., description="List of companies with 'name' and optional 'context' fields")


class LinkedInCompanySearchTool(BaseTool):
    """
    Search LinkedIn for a company by name and return the best matching URL.

    Uses Apify's LinkedIn company search to find candidates,
    then LLM to select the best match based on description.
    """

    name: str = "linkedin_company_search"
    description: str = """
    Find a company's LinkedIn URL by searching LinkedIn.

    More reliable than guessing URLs - actually searches LinkedIn!

    Parameters:
    - company_name: Name of the company to find
    - context: Optional context (e.g., "fintech startup", "AI company")

    Returns the best matching LinkedIn company URL.
    """
    args_schema: Type[BaseModel] = LinkedInCompanySearchInput

    def _run(self, company_name: str, context: str = "") -> str:
        """Search for a single company on LinkedIn."""
        result = self._search_single_company(company_name, context)
        return json.dumps(result)

    def _search_single_company(self, company_name: str, context: str = "") -> Dict:
        """
        Search LinkedIn for a company and return best match.

        Args:
            company_name: Company name to search
            context: Additional context for matching

        Returns:
            Dict with linkedin_url, matched_name, confidence, reason
        """
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return {"linkedin_url": None, "error": "APIFY_API_TOKEN not found"}

        print(f"\n[LINKEDIN_SEARCH] Searching for: '{company_name}'")

        try:
            # Search LinkedIn using Apify
            client = ApifyClient(apify_token)

            run_input = {
                "keyword": company_name,
                "limit": 5  # Get top 5 results to choose from
            }

            print(f"[LINKEDIN_SEARCH] Calling Apify actor apimaestro/linkedin-companies-search-scraper...")
            run = client.actor("apimaestro/linkedin-companies-search-scraper").call(run_input=run_input)

            # Fetch results
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[LINKEDIN_SEARCH] Found {len(results)} candidates")

            if not results:
                return {
                    "company_name": company_name,
                    "linkedin_url": None,
                    "matched_name": None,
                    "confidence": "none",
                    "reason": "No results found on LinkedIn"
                }

            # Use LLM to select best match
            best_match = self._select_best_match(company_name, context, results)
            return best_match

        except Exception as e:
            print(f"[LINKEDIN_SEARCH] Error: {e}")
            return {
                "company_name": company_name,
                "linkedin_url": None,
                "error": str(e)
            }

    def _select_best_match(
        self,
        company_name: str,
        context: str,
        candidates: List[Dict]
    ) -> Dict:
        """
        Use LLM to select the best matching company from candidates.

        Args:
            company_name: Original company name
            context: Additional context
            candidates: List of LinkedIn search results

        Returns:
            Best matching company info
        """
        # Build candidates table for LLM
        candidates_text = ""
        for i, c in enumerate(candidates, 1):
            name = c.get("name", c.get("title", "Unknown"))
            url = c.get("company_url", c.get("url", c.get("linkedinUrl", "")))
            desc = c.get("description", c.get("headline", "No description"))[:200]
            industry = c.get("industry", "")
            location = c.get("location", "")

            candidates_text += f"\n{i}. {name}"
            candidates_text += f"\n   URL: {url}"
            candidates_text += f"\n   Industry: {industry}"
            candidates_text += f"\n   Location: {location}"
            candidates_text += f"\n   Description: {desc}\n"

        context_str = f" (Context: {context})" if context else ""

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You match company names to LinkedIn search results. Select the best match or indicate if no good match exists."},
                    {"role": "user", "content": f"""Find the best LinkedIn match for: "{company_name}"{context_str}

CANDIDATES:
{candidates_text}

Select the BEST match. Consider:
- Name similarity (exact or close match)
- Description relevance to context
- Industry alignment

If no good match (confidence < 50%), return linkedin_url as empty string."""}
                ],
                response_format=CompanyMatch,
                temperature=0.2
            )

            result = response.choices[0].message.parsed

            print(f"[LINKEDIN_SEARCH] Selected: {result.matched_name} ({result.confidence})")

            return {
                "company_name": company_name,
                "linkedin_url": result.linkedin_url if result.confidence != "low" else None,
                "matched_name": result.matched_name,
                "confidence": result.confidence,
                "reason": result.reason
            }

        except Exception as e:
            print(f"[LINKEDIN_SEARCH] LLM selection error: {e}")
            # Fallback: return first result if name is similar
            if candidates:
                first = candidates[0]
                return {
                    "company_name": company_name,
                    "linkedin_url": first.get("company_url", first.get("url", first.get("linkedinUrl"))),
                    "matched_name": first.get("name", first.get("title")),
                    "confidence": "low",
                    "reason": "Fallback to first result (LLM failed)"
                }
            return {"company_name": company_name, "linkedin_url": None, "error": str(e)}


class LinkedInCompanyBatchSearchTool(BaseTool):
    """
    Batch search for multiple companies on LinkedIn.

    More efficient than individual searches - batches LLM calls
    to save on API costs.
    """

    name: str = "linkedin_company_batch_search"
    description: str = """
    Find LinkedIn URLs for multiple companies in one call.

    More efficient than searching one at a time!
    Batches searches and LLM selection to save costs.

    Parameters:
    - companies: List of dicts with 'name' and optional 'context' fields
      Example: [{"name": "Serval", "context": "AI IT management"}, {"name": "Finout"}]

    Returns list of matches with LinkedIn URLs.
    """
    args_schema: Type[BaseModel] = LinkedInCompanyBatchSearchInput

    def _run(self, companies: List[Dict]) -> str:
        """Search for multiple companies on LinkedIn."""
        if not companies:
            return json.dumps({"matches": [], "count": 0})

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return json.dumps({"matches": [], "error": "APIFY_API_TOKEN not found"})

        print(f"\n[LINKEDIN_BATCH] Searching for {len(companies)} companies...")

        # Step 1: Search LinkedIn for each company
        all_candidates = {}
        client = ApifyClient(apify_token)

        for company in companies:
            name = company.get("name", "")
            if not name:
                continue

            print(f"[LINKEDIN_BATCH] Searching: {name}")

            try:
                run_input = {
                    "keyword": name,
                    "limit": 5
                }
                run = client.actor("apimaestro/linkedin-companies-search-scraper").call(run_input=run_input)

                results = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    results.append(item)

                all_candidates[name] = {
                    "context": company.get("context", ""),
                    "candidates": results
                }
                print(f"[LINKEDIN_BATCH] Found {len(results)} candidates for {name}")

            except Exception as e:
                print(f"[LINKEDIN_BATCH] Error searching {name}: {e}")
                all_candidates[name] = {"context": "", "candidates": [], "error": str(e)}

        # Step 2: Batch LLM selection for all companies
        matches = self._batch_select_matches(all_candidates)

        return json.dumps({
            "matches": matches,
            "count": len([m for m in matches if m.get("linkedin_url")])
        })

    def _batch_select_matches(self, all_candidates: Dict) -> List[Dict]:
        """
        Use single LLM call to select best matches for all companies.

        Args:
            all_candidates: Dict of {company_name: {context, candidates}}

        Returns:
            List of match results
        """
        if not all_candidates:
            return []

        # Build combined prompt for all companies
        companies_text = ""
        company_list = []

        for company_name, data in all_candidates.items():
            if data.get("error") or not data.get("candidates"):
                company_list.append({
                    "company_name": company_name,
                    "linkedin_url": None,
                    "matched_name": None,
                    "confidence": "none",
                    "reason": data.get("error", "No candidates found")
                })
                continue

            context = data.get("context", "")
            candidates = data.get("candidates", [])
            context_str = f" (Context: {context})" if context else ""

            companies_text += f"\n\n=== COMPANY: {company_name}{context_str} ===\n"
            companies_text += "CANDIDATES:\n"

            for i, c in enumerate(candidates, 1):
                name = c.get("name", c.get("title", "Unknown"))
                url = c.get("company_url", c.get("url", c.get("linkedinUrl", "")))
                desc = c.get("description", c.get("headline", "No description"))[:150]
                industry = c.get("industry", "")

                companies_text += f"{i}. {name} | {url} | {industry} | {desc}\n"

        if not companies_text:
            return company_list

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You match company names to LinkedIn search results. For each company, select the best match or indicate no match."},
                    {"role": "user", "content": f"""Match each company to its best LinkedIn result:
{companies_text}

For EACH company, select the best matching LinkedIn URL.
Consider name similarity, description relevance, and industry.
If no good match exists, set linkedin_url to empty string."""}
                ],
                response_format=CompanyMatchList,
                temperature=0.2
            )

            result = response.choices[0].message.parsed

            # Convert to list of dicts
            for match in result.matches:
                company_list.append({
                    "company_name": match.company_name,
                    "linkedin_url": match.linkedin_url if match.linkedin_url else None,
                    "matched_name": match.matched_name,
                    "confidence": match.confidence,
                    "reason": match.reason
                })

            print(f"[LINKEDIN_BATCH] Matched {len([m for m in company_list if m.get('linkedin_url')])} companies")
            return company_list

        except Exception as e:
            print(f"[LINKEDIN_BATCH] Batch LLM selection error: {e}")
            # Return what we have
            return company_list


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LINKEDIN COMPANY SEARCH TOOL TEST")
    print("=" * 70)

    # Test single search
    tool = LinkedInCompanySearchTool()
    result = tool._run(
        company_name="Finout",
        context="cloud cost management startup"
    )
    print("\nSingle Search Result:")
    print(result)

    # Test batch search
    batch_tool = LinkedInCompanyBatchSearchTool()
    result = batch_tool._run(companies=[
        {"name": "Serval", "context": "AI IT management"},
        {"name": "Finout", "context": "cloud cost management"},
        {"name": "Substack", "context": "newsletter platform"}
    ])
    print("\nBatch Search Result:")
    print(result)
