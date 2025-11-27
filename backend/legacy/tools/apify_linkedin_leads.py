"""LinkedIn Lead Extraction tool - Extract leads from LinkedIn posts by URL."""
import os
import json
import re
from typing import Type, List, Dict, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
from openai import OpenAI


class LinkedInLeadExtractionInput(BaseModel):
    """Input schema for LinkedIn lead extraction."""
    query: str = Field(..., description="Search context for finding relevant leads (e.g., 'founder leads', 'CRM decision makers')")
    post_urls: List[str] = Field(..., description="List of LinkedIn post URLs to extract leads from")


class LinkedInLeadExtractionTool(BaseTool):
    """
    Extract leads with buying intent from LinkedIn posts.

    This tool takes LinkedIn post URLs and extracts relevant leads based on the query.
    It analyzes the post content and finds people mentioned or related to the post.
    """

    name: str = "LinkedIn Lead Extraction"
    description: str = """
    Extract leads from LinkedIn posts based on a search query.

    Input parameters:
    - query: Search context (e.g., "founder leads", "CRM decision makers")
    - post_urls: List of LinkedIn post URLs to analyze

    Returns list of LinkedIn leads with:
    - Name and profile URL
    - Title and company
    - Intent signal and relevance score
    - Source post context

    Use this to extract leads from specific LinkedIn posts.
    """
    args_schema: Type[BaseModel] = LinkedInLeadExtractionInput

    def _run(
        self,
        query: str,
        post_urls: List[str]
    ) -> str:
        """
        Execute LinkedIn lead extraction workflow.

        Args:
            query: Search context for finding relevant leads
            post_urls: List of LinkedIn post URLs to analyze

        Returns:
            Formatted string with extracted leads
        """
        if not post_urls:
            return "Error: No post URLs provided for lead extraction"

        print(f"\n[INFO] LinkedIn Lead Extraction from URLs")
        print(f"[INFO] Search Context: '{query}'")
        print(f"[INFO] Posts to analyze: {len(post_urls)}")

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment"

        try:
            all_leads = []

            for idx, post_url in enumerate(post_urls, 1):
                print(f"\n[INFO] Processing post {idx}/{len(post_urls)}: {post_url[:80]}...")

                # Step 1: Fetch post content using Apify
                post_data = self._fetch_post_by_url(apify_token, post_url)

                if not post_data:
                    print(f"[WARNING] Could not fetch post data, extracting info from URL...")
                    # Fallback: Extract what we can from the URL
                    post_data = self._extract_info_from_url(post_url)

                # Step 2: Extract leads from the post
                leads = self._extract_leads_from_post(query, post_data, post_url)
                all_leads.extend(leads)

            # Format and return results
            return self._format_lead_results(all_leads, query, len(post_urls))

        except Exception as e:
            error_msg = f"Error in LinkedIn lead extraction: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def _fetch_post_by_url(
        self,
        apify_token: str,
        post_url: str
    ) -> Optional[Dict]:
        """
        Fetch LinkedIn post content by URL.

        Uses Apify actor to scrape post content.

        Args:
            apify_token: Apify API token
            post_url: LinkedIn post URL

        Returns:
            Post data dictionary or None
        """
        client = ApifyClient(apify_token)

        # Try to use LinkedIn post scraper
        # Actor: apimaestro/linkedin-post-scraper (if available)
        run_input = {
            "urls": [post_url],
            "maxPosts": 1
        }

        print(f"[DEBUG] Attempting to fetch post: {post_url}")

        try:
            # Try the posts search actor with the URL
            run = client.actor("apimaestro/linkedin-posts-search-scraper-no-cookies").call(
                run_input={"searchQuery": "", "urls": [post_url], "maxPosts": 1}
            )

            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            if results:
                print(f"[DEBUG] Successfully fetched post data")
                return results[0]

        except Exception as e:
            print(f"[DEBUG] Could not fetch via posts actor: {e}")

        return None

    def _extract_info_from_url(self, post_url: str) -> Dict:
        """
        Extract information from LinkedIn post URL when API fails.

        Parses URL to extract author/company info.

        Args:
            post_url: LinkedIn post URL

        Returns:
            Basic post info dictionary
        """
        info = {
            "url": post_url,
            "text": "",
            "author": {}
        }

        # Extract author from URL patterns like:
        # https://www.linkedin.com/posts/y-combinator_maritime-fusion-...
        # https://www.linkedin.com/feed/update/urn:li:activity:...

        match = re.search(r'linkedin\.com/posts/([^_/]+)', post_url)
        if match:
            author_slug = match.group(1)
            info["author"] = {
                "name": author_slug.replace("-", " ").title(),
                "profileUrl": f"https://www.linkedin.com/company/{author_slug}/" if "combinator" in author_slug.lower() else f"https://www.linkedin.com/in/{author_slug}/"
            }

        # Extract topic from URL slug
        topic_match = re.search(r'posts/[^_]+_([^-]+)', post_url)
        if topic_match:
            topic = topic_match.group(1).replace("-", " ")
            info["text"] = f"Post about: {topic}"

        return info

    def _extract_leads_from_post(
        self,
        query: str,
        post_data: Dict,
        post_url: str
    ) -> List[Dict]:
        """
        Extract leads from a LinkedIn post using LLM analysis.

        Args:
            query: Search context
            post_data: Post data dictionary
            post_url: Original post URL

        Returns:
            List of lead dictionaries
        """
        # Build context for LLM
        author = post_data.get('author', {})
        if isinstance(author, dict):
            author_name = author.get('name', 'Unknown')
            author_title = author.get('headline', author.get('title', 'N/A'))
            author_url = author.get('profileUrl', author.get('url', 'N/A'))
        else:
            author_name = str(author) if author else 'Unknown'
            author_title = 'N/A'
            author_url = 'N/A'

        post_text = post_data.get('text', post_data.get('content', ''))[:1000]

        prompt = f"""Analyze this LinkedIn post and extract leads relevant to: "{query}"

POST URL: {post_url}

AUTHOR:
- Name: {author_name}
- Title: {author_title}
- Profile: {author_url}

POST CONTENT:
{post_text if post_text else "[No content available - analyze based on URL and author]"}

TASK: Extract people who would be good leads for "{query}".

Consider:
1. The post author - are they a relevant lead?
2. Companies/people mentioned in the post
3. The context (e.g., funding announcements → founders are leads)

For EACH lead found, provide:
- name: Full name
- title: Job title (if known, or infer from context)
- company: Company name
- linkedin_url: Profile URL (construct if needed: https://linkedin.com/in/[name-slug])
- intent_signal: Why they're relevant (based on post context)
- relevance_score: 0-100 based on match to query
- fit_reasoning: Why they're a good lead for this query

Return a JSON object with a "leads" array."""

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            json_schema = {
                "name": "linkedin_leads",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "leads": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "title": {"type": "string"},
                                    "company": {"type": "string"},
                                    "linkedin_url": {"type": "string"},
                                    "intent_signal": {"type": "string"},
                                    "relevance_score": {"type": "integer"},
                                    "fit_reasoning": {"type": "string"}
                                },
                                "required": ["name", "title", "company", "linkedin_url", "intent_signal", "relevance_score", "fit_reasoning"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["leads"],
                    "additionalProperties": False
                }
            }

            response = client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying leads from LinkedIn posts. Extract relevant people based on the search context."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
                temperature=0.3,
                max_tokens=2000
            )

            result = json.loads(response.choices[0].message.content.strip())
            leads = result.get("leads", [])

            # Add source post info to each lead
            for lead in leads:
                lead["source_post_url"] = post_url

            print(f"[INFO] Extracted {len(leads)} leads from post")
            return leads

        except Exception as e:
            print(f"[ERROR] Lead extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _format_lead_results(
        self,
        leads: List[Dict],
        query: str,
        num_posts: int
    ) -> str:
        """Format extracted leads into readable output."""
        output = []
        output.append("=" * 70)
        output.append(f"LINKEDIN LEADS: '{query}'")
        output.append("=" * 70)

        if not leads:
            return "\n".join(output) + f"\n\nNo leads found from {num_posts} posts analyzed."

        # Sort by relevance score
        leads.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        output.append(f"\nExtracted {len(leads)} leads from {num_posts} posts:\n")

        for idx, lead in enumerate(leads, 1):
            score = lead.get('relevance_score', 0)
            emoji = "🔥" if score >= 80 else "🟢" if score >= 60 else "🟡" if score >= 40 else "🔵"

            output.append(f"LEAD #{idx}")
            output.append("-" * 70)
            output.append(f"Name: {lead.get('name', 'Unknown')}")
            output.append(f"Title: {lead.get('title', 'N/A')}")
            output.append(f"Company: {lead.get('company', 'N/A')}")
            output.append(f"LinkedIn: {lead.get('linkedin_url', 'N/A')}")
            output.append(f"\nIntent Signal:")
            output.append(f'  "{lead.get("intent_signal", "N/A")}"')
            output.append(f"\nRelevance Score: {score}/100 {emoji}")
            output.append(f"\nFit Reasoning:")
            output.append(f"  {lead.get('fit_reasoning', 'N/A')}")
            output.append(f"\nSource: {lead.get('source_post_url', 'N/A')}")
            output.append("")

        output.append("=" * 70)
        output.append(f"\nTotal leads: {len(leads)} | Posts analyzed: {num_posts}")
        avg = sum(l.get('relevance_score', 0) for l in leads) / len(leads) if leads else 0
        output.append(f"Average relevance: {avg:.1f}/100")
        output.append("=" * 70)

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("\n" + "=" * 70)
    print("LINKEDIN LEAD EXTRACTION TOOL TEST")
    print("=" * 70)

    tool = LinkedInLeadExtractionTool()

    result = tool._run(
        query="founder leads",
        post_urls=[
            "https://www.linkedin.com/posts/y-combinator_maritime-fusion-has-raised-a-45m-seed-round-activity-7398812668230295553-WSh6"
        ]
    )

    print("\n" + result)
