"""
LinkedIn Company Posts Scraper - Competitor Displacement Strategy

Uses harvestapi/linkedin-company-posts Apify actor to find engagers
(commenters/likers) on competitor company posts.

v3.4: New strategy for competitor displacement leads.
"""
import os
import json
import time
from typing import Type, Optional, List, Dict
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient

# Import settings
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import settings


class LinkedInCompanyPostsInput(BaseModel):
    """Input schema for LinkedIn company posts search."""
    company_url: str = Field(..., description="LinkedIn company page URL (e.g., https://www.linkedin.com/company/asana/)")
    max_posts: int = Field(default=10, description="Max posts to fetch (default: 10)")


class LinkedInCompanyPostsBatchInput(BaseModel):
    """Input schema for batch LinkedIn company posts search."""
    company_urls: List[str] = Field(..., description="List of LinkedIn company page URLs")
    max_posts_per_company: int = Field(default=5, description="Max posts per company (default: 5)")


class LinkedInCompanyPostsTool(BaseTool):
    """
    Fetch posts from a LinkedIn company page and extract engagers.

    Strategy:
    1. Get recent posts from competitor company
    2. Extract commenters (name, title, linkedinUrl)
    3. Return as leads - people interested in this space!

    Time: ~30-60s per company
    """

    name: str = "linkedin_company_posts"
    description: str = """
    Fetch posts from a LinkedIn company page and extract engagers (commenters/likers).

    Use this for COMPETITOR DISPLACEMENT strategy:
    - Find people engaging with competitor content
    - They're already interested in this product category!

    Parameters:
    - company_url: LinkedIn company page URL (e.g., "https://www.linkedin.com/company/asana/")
    - max_posts: Max posts to fetch (default: 10)

    Returns JSON with:
    - posts: Array of posts with engagers
    - engagers: Extracted leads (name, title, linkedinUrl)
    - count: Number of engagers found
    """
    args_schema: Type[BaseModel] = LinkedInCompanyPostsInput

    def _run(
        self,
        company_url: str,
        max_posts: int = 10
    ) -> str:
        """
        Fetch company posts and extract engagers.
        """
        print(f"\n[LINKEDIN_COMPANY_POSTS] Fetching posts from {company_url}...")

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return json.dumps({
                "error": "APIFY_API_TOKEN not found",
                "posts": [],
                "engagers": [],
                "count": 0
            })

        try:
            client = ApifyClient(apify_token)

            # Clean company URL
            company_url = company_url.rstrip('/')
            if not company_url.startswith('http'):
                company_url = f"https://www.linkedin.com/company/{company_url}"

            # Run the actor with correct schema
            run_input = {
                "targetUrls": [company_url],
                "maxPosts": max_posts,
                "scrapeComments": True,
                "maxComments": 10,
                "scrapeReactions": False,
                "includeQuotePosts": True,
                "includeReposts": True
            }

            print(f"[LINKEDIN_COMPANY_POSTS] Running actor with maxPosts={max_posts}...")
            run = client.actor("harvestapi/linkedin-company-posts").call(
                run_input=run_input,
                timeout_secs=120
            )

            # Get results
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            print(f"[LINKEDIN_COMPANY_POSTS] Got {len(items)} posts")

            if not items:
                return json.dumps({
                    "posts": [],
                    "engagers": [],
                    "count": 0,
                    "company_url": company_url,
                    "recommendation": "No posts found. Try a different company or check URL."
                })

            # Extract engagers from posts
            engagers = self._extract_engagers(items, company_url)

            print(f"[LINKEDIN_COMPANY_POSTS] Extracted {len(engagers)} engagers")

            return json.dumps({
                "posts": items[:max_posts],
                "engagers": engagers,
                "count": len(engagers),
                "company_url": company_url,
                "posts_fetched": len(items),
                "recommendation": f"Found {len(engagers)} engagers. These are people interested in this space!"
            }, indent=2)

        except Exception as e:
            print(f"[LINKEDIN_COMPANY_POSTS] Error: {e}")
            return json.dumps({
                "error": str(e),
                "posts": [],
                "engagers": [],
                "count": 0,
                "company_url": company_url
            })

    def _extract_engagers(self, items: List[Dict], company_url: str) -> List[Dict]:
        """
        Extract engagers (commenters) from actor output.

        The actor returns:
        1. Posts (type="post") with embedded comments array
        2. Flat comment items (type="comment")

        Both have actor info with name, linkedinUrl, position.
        """
        engagers = []
        seen_urls = set()

        # Extract company name from URL
        company_name = company_url.split('/company/')[-1].rstrip('/').replace('-', ' ').title()

        for item in items:
            item_type = item.get('type', '')

            if item_type == 'post':
                # Extract from embedded comments array
                post_url = item.get('linkedinUrl', '')
                post_content = item.get('content', '')[:100]
                comments = item.get('comments', [])

                for comment in comments:
                    self._add_engager_from_comment(
                        comment, engagers, seen_urls, company_name, post_url, post_content
                    )

            elif item_type == 'comment':
                # Flat comment item
                post_url = item.get('query', {}).get('post', '')
                self._add_engager_from_comment(
                    item, engagers, seen_urls, company_name, post_url, ''
                )

        return engagers

    def _add_engager_from_comment(
        self,
        comment: Dict,
        engagers: List[Dict],
        seen_urls: set,
        company_name: str,
        post_url: str,
        post_content: str
    ):
        """Add an engager from a comment dict."""
        actor = comment.get('actor', {})
        if not actor:
            return

        linkedin_url = actor.get('linkedinUrl', '')
        if not linkedin_url or linkedin_url in seen_urls:
            return

        # Skip if no profile URL (just comment URL)
        if '/in/' not in linkedin_url:
            return

        seen_urls.add(linkedin_url)
        comment_text = comment.get('commentary', '')[:200]

        engagers.append({
            "name": actor.get('name', 'Unknown'),
            "title": actor.get('position', 'LinkedIn User'),
            "company": "Not specified",
            "linkedin_url": linkedin_url,
            "email": None,
            "intent_signal": f"Commented on {company_name}: \"{comment_text[:80]}\"" if comment_text else f"Engaged with {company_name} post",
            "intent_score": 65,
            "source_platform": "linkedin",
            "source_url": post_url,
            "priority": "warm",
            "scoring_reasoning": f"Commented on {company_name} (competitor) post - shows interest in this space",
            "engagement_type": "comment"
        })


class LinkedInCompanyPostsBatchTool(BaseTool):
    """
    Fetch posts from multiple competitor company pages in batch.

    More efficient for competitor displacement across multiple competitors.
    """

    name: str = "linkedin_company_posts_batch"
    description: str = """
    Fetch posts from multiple competitor LinkedIn company pages.

    Use this to gather leads from MULTIPLE competitors at once.

    Parameters:
    - company_urls: List of LinkedIn company URLs
    - max_posts_per_company: Max posts per company (default: 5)

    Returns JSON with engagers grouped by company.
    """
    args_schema: Type[BaseModel] = LinkedInCompanyPostsBatchInput

    def _run(
        self,
        company_urls: List[str],
        max_posts_per_company: int = 5
    ) -> str:
        """
        Fetch posts from multiple companies.
        """
        if not company_urls:
            return json.dumps({
                "error": "No company URLs provided",
                "results": {},
                "total_engagers": 0
            })

        print(f"\n[LINKEDIN_POSTS_BATCH] Fetching posts from {len(company_urls)} companies...")

        single_tool = LinkedInCompanyPostsTool()
        results = {}
        all_engagers = []

        for url in company_urls:
            result_str = single_tool._run(
                company_url=url,
                max_posts=max_posts_per_company
            )
            result = json.loads(result_str)

            company_name = url.split('/company/')[-1].rstrip('/').replace('-', ' ').title()
            results[company_name] = {
                "engagers": result.get('engagers', []),
                "count": result.get('count', 0),
                "posts_fetched": result.get('posts_fetched', 0)
            }
            all_engagers.extend(result.get('engagers', []))

            # Small delay between companies
            time.sleep(2)

        print(f"[LINKEDIN_POSTS_BATCH] Found {len(all_engagers)} total engagers across {len(company_urls)} companies")

        return json.dumps({
            "results": results,
            "all_engagers": all_engagers,
            "total_engagers": len(all_engagers),
            "companies_searched": len(company_urls),
            "recommendation": f"Found {len(all_engagers)} competitor engagers. Run filter_sellers before final output."
        }, indent=2)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LINKEDIN COMPANY POSTS TEST")
    print("=" * 70)

    tool = LinkedInCompanyPostsTool()
    result = tool._run(
        company_url="https://www.linkedin.com/company/figma/",
        max_posts=5
    )
    print("\nResult:")
    print(result)
