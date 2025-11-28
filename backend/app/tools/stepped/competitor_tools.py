"""
Competitor Displacement Stepped Tools - v3.4

Find leads by scraping competitor LinkedIn company posts.
People who engage with competitors = interested in this space!

Strategy:
1. Identify competitor LinkedIn pages via SERP search
2. Scrape their recent posts
3. Extract commenters/engagers
4. Filter sellers, return qualified leads
"""
import os
import json
import re
import requests
from typing import Type, Optional, List, Dict
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Import the underlying tool
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_linkedin_company_posts import LinkedInCompanyPostsTool, LinkedInCompanyPostsBatchTool


class CompetitorIdentifyInput(BaseModel):
    """Input schema for competitor identification."""
    product_description: str = Field(..., description="Description of your product")
    competitors: List[str] = Field(default=[], description="Known competitor names (optional)")


class CompetitorScrapeInput(BaseModel):
    """Input schema for competitor posts scraping."""
    competitor_urls: List[str] = Field(..., description="LinkedIn company URLs to scrape")
    max_posts_per_company: int = Field(default=5, description="Max posts per company (default: 5)")


class CompetitorIdentifyTool(BaseTool):
    """
    Step 1: Identify competitor LinkedIn URLs via SERP search.

    Takes product description and optional competitor names.
    Uses Google SERP to find actual LinkedIn company page URLs.
    """

    name: str = "competitor_identify"
    description: str = """
    Identify competitor LinkedIn company page URLs via SERP search.

    Takes your product and known competitors.
    Uses Google search to find verified LinkedIn company URLs.

    Parameters:
    - product_description: What your product does
    - competitors: Known competitor names (optional)

    Returns JSON with:
    - competitor_urls: Array of verified LinkedIn company URLs
    - count: Number of competitors identified
    - recommendation: Next step
    """
    args_schema: Type[BaseModel] = CompetitorIdentifyInput

    def _run(
        self,
        product_description: str,
        competitors: List[str] = []
    ) -> str:
        """
        Find competitor LinkedIn URLs via SERP search.
        """
        print(f"\n[COMPETITOR_IDENTIFY] Identifying competitors for: {product_description[:50]}...")

        # If no competitors provided, suggest common patterns
        if not competitors:
            return json.dumps({
                "competitor_urls": [],
                "count": 0,
                "recommendation": "No competitors provided. Use strategy plan to identify 2-3 competitors, then call competitor_scrape with their LinkedIn URLs."
            })

        serper_api_key = os.getenv("SERPER_API_KEY")
        if not serper_api_key:
            # Fallback to slug-based URLs if no API key
            print("[COMPETITOR_IDENTIFY] Warning: SERPER_API_KEY not found, using slug fallback")
            return self._fallback_slug_urls(competitors)

        # Find LinkedIn company URLs via SERP
        competitor_urls = []
        for competitor in competitors:
            url = self._find_company_linkedin_url(competitor, serper_api_key)
            if url:
                competitor_urls.append({
                    "name": competitor,
                    "url": url,
                    "method": "serp"
                })
            else:
                # Fallback to slug if SERP fails for this company
                clean_name = competitor.lower().strip().replace(' ', '-').replace('.', '')
                fallback_url = f"https://www.linkedin.com/company/{clean_name}/"
                competitor_urls.append({
                    "name": competitor,
                    "url": fallback_url,
                    "method": "slug_fallback"
                })
                print(f"[COMPETITOR_IDENTIFY] SERP failed for {competitor}, using slug fallback")

        print(f"[COMPETITOR_IDENTIFY] Found {len(competitor_urls)} competitor URLs via SERP")

        return json.dumps({
            "competitors": competitor_urls,
            "urls": [c["url"] for c in competitor_urls],
            "count": len(competitor_urls),
            "recommendation": f"Found {len(competitor_urls)} competitor URLs. Use competitor_scrape to fetch their posts."
        }, indent=2)

    def _find_company_linkedin_url(self, company_name: str, api_key: str) -> Optional[str]:
        """
        Find a company's LinkedIn URL via Google SERP.

        Searches: "CompanyName" site:linkedin.com/company/
        """
        query = f'"{company_name}" site:linkedin.com/company/'

        try:
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": 5
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            organic_results = data.get("organic", [])

            # Find the first valid LinkedIn company URL
            for result in organic_results:
                link = result.get('link', '')
                if 'linkedin.com/company/' in link:
                    # Clean and validate the URL
                    linkedin_url = self._extract_company_url(link)
                    if linkedin_url:
                        print(f"[COMPETITOR_IDENTIFY] Found {company_name}: {linkedin_url}")
                        return linkedin_url

        except Exception as e:
            print(f"[COMPETITOR_IDENTIFY] SERP search failed for {company_name}: {e}")

        return None

    def _extract_company_url(self, url: str) -> Optional[str]:
        """
        Extract clean LinkedIn company URL from SERP result.

        Input: https://www.linkedin.com/company/figma/about
        Output: https://www.linkedin.com/company/figma/
        """
        # Match LinkedIn company URL pattern
        match = re.search(r'(https?://(?:www\.)?linkedin\.com/company/[^/]+)', url)
        if match:
            return match.group(1) + "/"
        return None

    def _fallback_slug_urls(self, competitors: List[str]) -> str:
        """
        Fallback: Generate URLs from company name slugs.
        Used when SERPER_API_KEY is not available.
        """
        competitor_urls = []
        for competitor in competitors:
            clean_name = competitor.lower().strip().replace(' ', '-').replace('.', '')
            url = f"https://www.linkedin.com/company/{clean_name}/"
            competitor_urls.append({
                "name": competitor,
                "url": url,
                "method": "slug_fallback"
            })

        return json.dumps({
            "competitors": competitor_urls,
            "urls": [c["url"] for c in competitor_urls],
            "count": len(competitor_urls),
            "warning": "Using slug-based URLs (SERPER_API_KEY not found). URLs may not be accurate.",
            "recommendation": f"Found {len(competitor_urls)} competitor URLs. Use competitor_scrape to fetch their posts."
        }, indent=2)


class CompetitorScrapeTool(BaseTool):
    """
    Step 2: Scrape competitor LinkedIn posts and extract engagers.

    Takes competitor URLs, returns engagers as leads.
    """

    name: str = "competitor_scrape"
    description: str = """
    Scrape LinkedIn posts from competitor company pages.

    Extracts engagers (commenters/likers) as leads.
    These people are interested in your product category!

    Parameters:
    - competitor_urls: Array of LinkedIn company URLs
    - max_posts_per_company: Max posts per company (default: 5)

    Returns JSON with:
    - leads: Array of engagers with name, title, linkedin_url
    - count: Number of leads found
    - recommendation: Next step (filter_sellers)
    """
    args_schema: Type[BaseModel] = CompetitorScrapeInput

    def _run(
        self,
        competitor_urls: List[str],
        max_posts_per_company: int = 5
    ) -> str:
        """
        Scrape posts and extract engagers.
        """
        if not competitor_urls:
            return json.dumps({
                "leads": [],
                "count": 0,
                "recommendation": "No competitor URLs provided. Use competitor_identify first."
            })

        print(f"\n[COMPETITOR_SCRAPE] Scraping {len(competitor_urls)} competitor pages...")

        # Use batch tool for efficiency
        batch_tool = LinkedInCompanyPostsBatchTool()
        result_str = batch_tool._run(
            company_urls=competitor_urls,
            max_posts_per_company=max_posts_per_company
        )

        result = json.loads(result_str)
        all_engagers = result.get('all_engagers', [])

        print(f"[COMPETITOR_SCRAPE] Found {len(all_engagers)} engagers")

        # Format as leads
        leads = []
        for engager in all_engagers:
            leads.append({
                "name": engager.get('name', 'Unknown'),
                "title": engager.get('title', 'LinkedIn User'),
                "company": engager.get('company', 'Not specified'),
                "linkedin_url": engager.get('linkedin_url'),
                "email": None,
                "intent_signal": engager.get('intent_signal', 'Engaged with competitor'),
                "intent_score": engager.get('intent_score', 60),
                "source_platform": "linkedin",
                "source_url": engager.get('source_url', ''),
                "priority": engager.get('priority', 'warm'),
                "scoring_reasoning": engager.get('scoring_reasoning', 'Engaged with competitor content')
            })

        return json.dumps({
            "leads": leads,
            "count": len(leads),
            "competitors_scraped": len(competitor_urls),
            "posts_fetched": sum(r.get('posts_fetched', 0) for r in result.get('results', {}).values()),
            "warning": "Run filter_sellers before final output to remove promoters!",
            "recommendation": f"Found {len(leads)} competitor engagers. Apply filter_sellers before aggregation."
        }, indent=2)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("COMPETITOR DISPLACEMENT TOOLS TEST")
    print("=" * 70)

    # Test identify
    identify_tool = CompetitorIdentifyTool()
    identify_result = identify_tool._run(
        product_description="AI design tool for startups",
        competitors=["Figma", "Canva"]
    )
    print("\nIdentify Result:")
    print(identify_result)
