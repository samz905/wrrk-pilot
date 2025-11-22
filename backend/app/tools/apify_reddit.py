"""Reddit scraping tool using Apify - Find intent signals from Reddit discussions."""
import os
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class ApifyRedditSearchInput(BaseModel):
    """Input schema for Reddit search."""
    query: str = Field(..., description="Search query or keywords (e.g., 'looking for CRM alternative')")
    subreddit: Optional[str] = Field(None, description="Specific subreddit (e.g., 'sales', 'entrepreneur') or leave empty for all")
    time_filter: str = Field(default="month", description="Time range: 'hour', 'day', 'week', 'month', 'year', 'all'")
    sort_by: str = Field(default="relevance", description="Sort order: 'relevance', 'hot', 'top', 'new', 'comments'")
    max_results: int = Field(default=20, description="Maximum posts to return (1-100)")


class ApifyRedditSearchTool(BaseTool):
    """
    Search Reddit for posts and discussions showing buying intent and pain points.

    This tool finds people actively discussing problems, asking for recommendations,
    and complaining about existing solutions - all strong intent signals.

    Best for finding:
    - Help requests: "Can anyone recommend a [solution]?"
    - Complaint threads: "Why is [problem] so hard?"
    - Alternative searches: "Cheaper alternative to [competitor]?"
    - Problem discussions: "How do you solve [specific problem]?"

    Key subreddits for B2B prospecting:
    - r/sales - Sales professionals
    - r/entrepreneur - Founders with budget authority
    - r/startups - Early-stage companies
    - r/SaaS - SaaS operators
    - r/smallbusiness - Small business owners
    """

    name: str = "Reddit Discussion Search"
    description: str = """
    Search Reddit for discussions showing buying intent and pain points.

    Use this to find prospects who are:
    - Asking for tool recommendations
    - Complaining about current solutions
    - Discussing specific problems
    - Evaluating alternatives

    Input parameters:
    - query: Search keywords (e.g., "frustrated with Salesforce")
    - subreddit: Target subreddit (e.g., "sales") or leave empty for all
    - time_filter: Recency filter (default: "month")
    - sort_by: How to sort results (default: "relevance")
    - max_results: Number of posts to return (default: 20)

    Returns Reddit posts with:
    - Post title and content
    - Author information
    - Subreddit and engagement metrics
    - Intent signal scoring
    """
    args_schema: Type[BaseModel] = ApifyRedditSearchInput

    def _run(
        self,
        query: str,
        subreddit: Optional[str] = None,
        time_filter: str = "month",
        sort_by: str = "relevance",
        max_results: int = 20
    ) -> str:
        """Execute Reddit search and return formatted results."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        print(f"\n[INFO] Searching Reddit for: '{query}'")
        if subreddit:
            print(f"[INFO] Subreddit: r/{subreddit}")
        print(f"[INFO] Time filter: {time_filter}, Sort: {sort_by}, Max results: {max_results}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Build search query with subreddit if specified
        if subreddit:
            # Search within specific subreddit
            queries = [f"subreddit:{subreddit} {query}"]
        else:
            # Search across all subreddits
            queries = [query]

        # Prepare actor input
        # Note: Actor requires min 10 posts, min 1 maxComments
        run_input = {
            "queries": queries,
            "sort": sort_by,
            "timeframe": time_filter,
            "urls": [],  # Must be empty array, not None
            "maxPosts": max(10, min(max_results, 100)),  # Min 10, max 100
            "maxComments": 1,  # Min 1 required by actor (we won't use comments for now)
            "scrapeComments": False,  # Don't actually scrape comment content
            "includeNsfw": False,
        }

        print(f"[INFO] Calling Apify actor TwqHBuZZPHJxiQrTU (Reddit Scraper Pro)...")

        try:
            # Run the actor
            run = client.actor("TwqHBuZZPHJxiQrTU").call(run_input=run_input)

            print(f"[INFO] Actor run completed. Fetching posts...")

            # Fetch results
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[INFO] Found {len(results)} posts\n")

            if not results:
                return f"No Reddit posts found for query: '{query}'"

            print(f"[DEBUG] First post keys: {list(results[0].keys())}\n")

            # Format results for agent consumption
            return self._format_results(results, query)

        except Exception as e:
            error_msg = f"Error calling Apify Reddit actor: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def _format_results(self, results: list, query: str) -> str:
        """Format Reddit posts into readable output with intent scoring."""

        output = []
        output.append("=" * 70)
        output.append(f"REDDIT INTENT SIGNALS: '{query}'")
        output.append("=" * 70)
        output.append(f"\nFound {len(results)} Reddit discussions:\n")

        for idx, post in enumerate(results, 1):
            # Extract post data (actual field names from actor output)
            title = post.get('title', 'No title')
            text = post.get('body', post.get('text', ''))  # 'body' is the actual field name
            author = post.get('author', 'Unknown')
            subreddit = post.get('subreddit', 'Unknown')
            score = post.get('score', 0)
            num_comments = post.get('num_comments', 0)  # Actual field name
            created = post.get('created_utc', post.get('created', 'Unknown'))  # Unix timestamp
            url = post.get('url', 'No URL')

            # Calculate intent score based on engagement and keywords
            intent_score = self._calculate_intent_score(title, text, score, num_comments)

            output.append(f"Intent Signal #{idx}")
            output.append("─" * 70)
            output.append(f"Title: {title}")
            if text and len(text) > 0:
                # Truncate long posts
                display_text = text[:300] + "..." if len(text) > 300 else text
                output.append(f"Content: {display_text}")
            output.append(f"\nSubreddit: r/{subreddit}")
            output.append(f"Author: u/{author}")
            output.append(f"Engagement: {score} upvotes, {num_comments} comments")
            output.append(f"Posted: {created}")
            output.append(f"URL: {url}")
            output.append(f"\n💡 Intent Score: {intent_score}/100")
            output.append(f"Intent Level: {self._get_intent_level(intent_score)}")
            output.append("")

        output.append("=" * 70)
        output.append("\nKEY INSIGHTS:")
        output.append(f"- Total discussions found: {len(results)}")
        output.append(f"- Subreddits represented: {len(set(p.get('subreddit', 'Unknown') for p in results))}")
        avg_score = sum(p.get('score', 0) for p in results) / len(results) if results else 0
        output.append(f"- Average upvotes: {avg_score:.1f}")
        avg_comments = sum(p.get('num_comments', 0) for p in results) / len(results) if results else 0
        output.append(f"- Average comments: {avg_comments:.1f}")
        output.append("=" * 70)

        return "\n".join(output)

    def _calculate_intent_score(self, title: str, text: str, score: int, num_comments: int) -> int:
        """
        Calculate intent signal strength (0-100).

        Based on:
        - Keyword analysis (35 points)
        - Engagement metrics (35 points)
        - Discussion depth (30 points)
        """

        intent_score = 0
        combined_text = (title + " " + text).lower()

        # Keyword scoring (35 points)
        keyword_score = 0

        # Explicit requests (highest intent)
        request_keywords = ['recommend', 'suggestion', 'looking for', 'need help', 'what do you use', 'alternatives']
        if any(kw in combined_text for kw in request_keywords):
            keyword_score = 35

        # Complaints about competitors
        elif any(word in combined_text for word in ['frustrated', 'hate', 'terrible', 'awful', 'sucks', 'expensive']):
            keyword_score = 30

        # Evaluation/comparison
        elif any(word in combined_text for word in ['vs', 'versus', 'compare', 'better than', 'switch from']):
            keyword_score = 25

        # Problem discussion
        elif any(word in combined_text for word in ['problem', 'issue', 'struggle', 'difficult', 'challenge']):
            keyword_score = 20

        # General interest
        else:
            keyword_score = 10

        intent_score += keyword_score

        # Engagement scoring (35 points max)
        # High upvotes = community validation of the problem
        upvote_score = min(score / 10, 20)  # Max 20 points (200+ upvotes)
        intent_score += upvote_score

        # Comment count scoring (15 points max)
        comment_score = min(num_comments / 2, 15)  # Max 15 points (30+ comments)
        intent_score += comment_score

        # Discussion depth (30 points)
        # More comments = more people discussing = validated pain point
        if num_comments >= 20:
            discussion_score = 30  # Very active discussion
        elif num_comments >= 10:
            discussion_score = 20
        elif num_comments >= 5:
            discussion_score = 10
        else:
            discussion_score = 5

        intent_score += discussion_score

        return min(int(intent_score), 100)

    def _get_intent_level(self, score: int) -> str:
        """Convert numerical score to intent level."""
        if score >= 80:
            return "🔥 VERY HIGH - Explicit request or very active discussion"
        elif score >= 60:
            return "🟢 HIGH - Strong intent signal"
        elif score >= 40:
            return "🟡 MEDIUM - Moderate intent"
        else:
            return "🔵 LOW - Weak signal"


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("REDDIT SEARCH TOOL TEST")
    print("=" * 70)

    tool = ApifyRedditSearchTool()

    # Test search
    result = tool._run(
        query="looking for CRM alternative",
        subreddit="sales",
        time_filter="month",
        max_results=5
    )

    print("\n" + result)
