"""
G2 Stepped Tools - Agent reasons after each step.

Uses LLM reasoning - no hardcoded competitor maps needed.
The LLM knows who competes with whom.
"""
import os
import json
from typing import Type, Optional, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from openai import OpenAI

# Import CrewAI scraper
from crewai_tools import ScrapeWebsiteTool

# Import LinkedIn company search for reliable URL lookup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from apify_linkedin_company_search import LinkedInCompanyBatchSearchTool


# === Structured Output Models ===

class CompetitorIdentification(BaseModel):
    """Identified competitor product."""
    competitor: str = Field(description="G2-friendly product slug (lowercase, hyphens)")
    reasoning: str = Field(description="Why this competitor was chosen")


class G2Reviewer(BaseModel):
    """A reviewer extracted from G2."""
    name: str = Field(default="Unknown")
    title: str = Field(default="Not specified")
    company: str = Field(default="Not specified")
    complaint: str = Field(description="Main complaint or frustration")


class G2ReviewersList(BaseModel):
    """List of reviewers extracted from G2."""
    leads: List[G2Reviewer]


class IdentifyCompetitorInput(BaseModel):
    """Input schema for competitor identification."""
    query: str = Field(..., description="Product description (e.g., 'AI design tool for startups')")


class G2FetchReviewsInput(BaseModel):
    """Input schema for G2 review fetching."""
    competitor: str = Field(..., description="Competitor product name (e.g., 'figma', 'asana')")


class ExtractReviewersInput(BaseModel):
    """Input schema for reviewer extraction."""
    content: str = Field(..., description="HTML/text content from g2_fetch_reviews")
    competitor: str = Field(..., description="Competitor name for context")


class IdentifyCompetitorTool(BaseTool):
    """
    Identify competitor products from a query using LLM reasoning.
    """

    name: str = "identify_competitor"
    description: str = """
    Identify competitor products from a query using LLM.

    The LLM knows the competitive landscape - just ask it.

    Parameters:
    - query: Product description

    Returns JSON with competitor name and recommendation.
    """
    args_schema: Type[BaseModel] = IdentifyCompetitorInput

    def _run(self, query: str) -> str:
        """Identify competitor using LLM reasoning with structured outputs."""
        print(f"\n[IDENTIFY_COMPETITOR] Analyzing: '{query}'")

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.beta.chat.completions.parse(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "You identify competitor products. Return the G2-friendly product slug (lowercase, hyphens)."},
                    {"role": "user", "content": f"What's the main competitor for: {query}"}
                ],
                response_format=CompetitorIdentification,
                temperature=0.3
            )

            result = response.choices[0].message.parsed
            competitor = result.competitor.lower().replace(" ", "-") if result.competitor else None

            if competitor:
                print(f"[IDENTIFY_COMPETITOR] Found: {competitor}")
                return json.dumps({
                    "competitor": competitor,
                    "found": True,
                    "reasoning": result.reasoning,
                    "recommendation": f"Proceed to g2_fetch_reviews with competitor='{competitor}'"
                })
            else:
                return json.dumps({
                    "competitor": None,
                    "found": False,
                    "recommendation": "No competitor found. Skip G2 strategy."
                })

        except Exception as e:
            print(f"[IDENTIFY_COMPETITOR] Error: {e}")
            return json.dumps({"competitor": None, "found": False, "error": str(e)})


class G2FetchReviewsTool(BaseTool):
    """
    Fetch low-rated reviews from G2 for a competitor.
    """

    name: str = "g2_fetch_reviews"
    description: str = """
    Fetch low-rated reviews from G2. Frustrated users = HIGH INTENT leads!

    Parameters:
    - competitor: Product name (e.g., 'figma')

    Returns review content for extraction.
    """
    args_schema: Type[BaseModel] = G2FetchReviewsInput

    def _run(self, competitor: str) -> str:
        """Fetch G2 reviews."""
        competitor_slug = competitor.lower().replace(" ", "-")
        url = f"https://www.g2.com/products/{competitor_slug}/reviews?order=lowest_rated"

        print(f"\n[G2_FETCH] Fetching reviews for: {competitor}")

        try:
            scraper = ScrapeWebsiteTool(website_url=url)
            content = scraper.run()

            if content and len(content) > 100:
                print(f"[G2_FETCH] Got {len(content)} chars")
                return json.dumps({
                    "content": content[:10000],
                    "competitor": competitor,
                    "source_url": url,
                    "success": True,
                    "recommendation": "Proceed to extract_reviewers"
                })
            else:
                return json.dumps({
                    "content": "",
                    "success": False,
                    "recommendation": "No content. Skip G2."
                })

        except Exception as e:
            print(f"[G2_FETCH] Error: {e}")
            return json.dumps({"content": "", "success": False, "error": str(e)})


class ExtractReviewersTool(BaseTool):
    """
    Extract reviewer info from G2 content using LLM.
    Enriches with company LinkedIn URLs for decision maker discovery.
    """

    name: str = "extract_reviewers"
    description: str = """
    Extract frustrated reviewers from G2 content.

    These are HIGH INTENT leads - they're unhappy with the competitor!
    Includes company LinkedIn URLs for finding decision makers.

    Parameters:
    - content: Content from g2_fetch_reviews
    - competitor: Competitor name

    Returns leads with company_linkedin_url for use with linkedin_employees_search.
    """
    args_schema: Type[BaseModel] = ExtractReviewersInput

    def _run(self, content: str, competitor: str) -> str:
        """Extract reviewers using LLM with structured outputs, then enrich with LinkedIn company URLs."""
        if not content or len(content) < 100:
            return json.dumps({"leads": [], "count": 0, "error": "No content"})

        print(f"\n[EXTRACT_REVIEWERS] Extracting from {len(content)} chars")

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.beta.chat.completions.parse(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "Extract reviewer info from G2 reviews. These are frustrated users seeking alternatives."},
                    {"role": "user", "content": f"Extract reviewers frustrated with {competitor} from:\n\n{content[:8000]}"}
                ],
                response_format=G2ReviewersList,
                temperature=0.3
            )

            result = response.choices[0].message.parsed

            # Collect unique company names for batch LinkedIn search
            unique_companies = list(set(
                lead.company for lead in result.leads
                if lead.company and lead.company != "Not specified"
            ))

            # Batch lookup company LinkedIn URLs
            url_map = {}
            if unique_companies:
                print(f"[EXTRACT_REVIEWERS] Looking up LinkedIn URLs for {len(unique_companies)} companies...")
                linkedin_search = LinkedInCompanyBatchSearchTool()
                search_result = linkedin_search._run(companies=[
                    {"name": c, "context": f"company where {competitor} user works"}
                    for c in unique_companies[:10]  # Limit to 10 for cost efficiency
                ])
                search_data = json.loads(search_result)

                # Build URL map
                for match in search_data.get("matches", []):
                    if match.get("linkedin_url"):
                        url_map[match["company_name"]] = match["linkedin_url"]

                print(f"[EXTRACT_REVIEWERS] Found LinkedIn URLs for {len(url_map)}/{len(unique_companies)} companies")

            # Enrich leads with company LinkedIn URLs
            leads = []
            for lead in result.leads:
                leads.append({
                    "name": lead.name,
                    "title": lead.title,
                    "company": lead.company,
                    "company_linkedin_url": url_map.get(lead.company),
                    "intent_signal": f"Frustrated with {competitor}: {lead.complaint}",
                    "intent_score": 80,
                    "source_platform": "g2",
                    "source_url": f"https://www.g2.com/products/{competitor}/reviews",
                    "priority": "hot",
                    "scoring_reasoning": f"Frustrated {competitor} user"
                })

            print(f"[EXTRACT_REVIEWERS] Found {len(leads)} leads")

            companies_with_urls = len([l for l in leads if l.get("company_linkedin_url")])
            return json.dumps({
                "leads": leads,
                "count": len(leads),
                "companies_with_linkedin": companies_with_urls,
                "source": "g2_reviews",
                "recommendation": f"Got {len(leads)} frustrated users from G2. {companies_with_urls} have company LinkedIn URLs - use linkedin_employees_search to find decision makers."
            })

        except Exception as e:
            print(f"[EXTRACT_REVIEWERS] Error: {e}")
            return json.dumps({"leads": [], "count": 0, "error": str(e)})
