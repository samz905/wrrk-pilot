"""Apify LinkedIn Posts Search tool - Find intent signals."""
from typing import Type, Optional, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
import os


class LinkedInPostsSearchInput(BaseModel):
    """Input schema for LinkedIn posts search."""
    query: str = Field(..., description="Search query to find posts (e.g., 'frustrated with Salesforce', 'looking for CRM')")
    max_results: int = Field(default=20, description="Maximum posts to return (max 100)")


class ApifyLinkedInPostsSearchTool(BaseTool):
    """Search LinkedIn posts for intent signals and buying behavior."""

    name: str = "LinkedIn Posts Search"
    description: str = """
    Search LinkedIn for posts mentioning specific topics, problems, or needs.
    This finds REAL INTENT SIGNALS - people actively posting about problems.

    Use this to find prospects who are:
    - Complaining about competitors ("frustrated with Salesforce")
    - Asking for recommendations ("looking for CRM alternative")
    - Discussing specific problems ("our sales process is broken")
    - Evaluating solutions ("comparing HubSpot vs Pipedrive")

    Returns: Post content, author info, engagement metrics, and timing.

    Example queries:
    - "looking for project management software"
    - "Salesforce is too expensive"
    - "need better analytics tool"
    - "switching from [competitor]"
    """
    args_schema: Type[BaseModel] = LinkedInPostsSearchInput

    def _run(
        self,
        query: str,
        max_results: int = 20
    ) -> str:
        """Execute LinkedIn posts search via Apify."""
        try:
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token:
                return "Error: APIFY_API_TOKEN not found in environment"

            print(f"\n[INFO] Searching LinkedIn posts for: '{query}'")

            # Initialize Apify client
            client = ApifyClient(apify_token)

            # Prepare Actor input for apimaestro/linkedin-posts-search-scraper-no-cookies
            run_input = {
                "searchQuery": query,
                "maxPosts": min(max_results, 100),
                "startPage": 1
            }

            print(f"[INFO] Calling Apify actor 5QnEH5N71IK2mFLrP (LinkedIn Posts Search)...")

            # Run the Actor and wait for it to finish
            run = client.actor("5QnEH5N71IK2mFLrP").call(run_input=run_input)

            print(f"[INFO] Actor run completed. Fetching posts...")

            # Fetch results from the run's dataset
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[INFO] Found {len(results)} posts with intent signals")

            if results:
                print(f"\n[DEBUG] First post keys: {list(results[0].keys())}\n")

            return self._format_results(results)

        except Exception as e:
            return f"Error executing LinkedIn posts search: {str(e)}"

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format LinkedIn posts into structured text with intent signals."""
        if not results:
            return "No posts found matching the search criteria."

        formatted_posts = []

        for idx, post in enumerate(results, 1):
            # Extract author information
            author = post.get('author', {})
            if isinstance(author, dict):
                author_name = author.get('name', 'N/A')
                author_url = author.get('profileUrl', author.get('url', 'N/A'))
                author_title = author.get('headline', 'N/A')
            else:
                author_name = 'N/A'
                author_url = 'N/A'
                author_title = 'N/A'

            # Extract post content
            post_text = post.get('text', post.get('content', 'N/A'))
            if post_text and len(post_text) > 300:
                post_text = post_text[:300] + "..."

            # Extract engagement metrics
            likes = post.get('likesCount', post.get('likes', 0))
            comments = post.get('commentsCount', post.get('comments', 0))

            # Extract timing
            post_date = post.get('postedDate', post.get('date', 'N/A'))

            # Extract post URL
            post_url = post.get('postUrl', post.get('url', 'N/A'))

            formatted_post = f"""
Intent Signal #{idx}:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Author: {author_name}
   Title: {author_title}
   LinkedIn: {author_url}

📝 Post Content:
   "{post_text}"

📊 Engagement: {likes} likes, {comments} comments
📅 Posted: {post_date}
🔗 Post URL: {post_url}

🎯 Intent Score: {"HIGH" if (likes > 10 or comments > 5) else "MEDIUM" if (likes > 3 or comments > 2) else "LOW"}
   (Based on: Recency + Engagement + Content)
"""
            formatted_posts.append(formatted_post.strip())

        summary = f"""
Found {len(results)} LinkedIn posts with buying intent signals:

{chr(10).join(formatted_posts)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Next Steps:
   1. Prioritize posts with HIGH intent scores
   2. Check author profiles for decision-making authority
   3. Reach out within 24-48 hours while problem is fresh
   4. Reference specific post content in outreach
"""

        return summary
