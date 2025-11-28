"""
Reddit Stepped Tools - Agent reasons after each step.

These tools wrap the existing ApifyRedditSearchTool but expose each step
separately so the agent can:
1. Search -> Review quality -> Retry if needed
2. Score -> Review results -> Adjust strategy
3. Extract -> Get raw leads -> Apply seller filter

Each tool returns results + quality assessment + recommendation.
"""
import os
import json
from typing import Type, Optional, List, Dict
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Import the existing Reddit tool for underlying functionality
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.apify_reddit import ApifyRedditSearchTool


class RedditSearchInput(BaseModel):
    """Input schema for Reddit search step."""
    query: str = Field(..., description="Search query (e.g., 'AI design tool')")
    limit: int = Field(default=50, description="Max posts to fetch (default: 50)")
    time_filter: str = Field(default="month", description="Time range: 'hour', 'day', 'week', 'month', 'year', 'all'")


class RedditScoreInput(BaseModel):
    """Input schema for Reddit scoring step."""
    posts: List[Dict] = Field(..., description="Posts from reddit_search (pass the posts array)")
    query: str = Field(default="product", description="Original query for context (optional - defaults to 'product')")


class RedditExtractInput(BaseModel):
    """Input schema for Reddit extraction step."""
    posts: List[Dict] = Field(..., description="High-quality posts from reddit_score")
    query: str = Field(default="", description="Original query for context (optional)")


class RedditSearchSteppedTool(BaseTool):
    """
    Step 1: Search Reddit for discussions.

    Returns posts with quality assessment. Agent should review results and decide:
    - Quality HIGH? -> Proceed to reddit_score
    - Quality LOW? -> Try different query or skip to next strategy
    """

    name: str = "reddit_search"
    description: str = """
    Search Reddit for discussions. Returns posts with quality assessment.

    Agent should review results and decide:
    - Quality HIGH? -> Proceed to reddit_score
    - Quality LOW? -> Try different query (e.g., "frustrated with [competitor]")
    - Still LOW after 2 tries? -> Skip to next strategy (G2, Crunchbase)

    Parameters:
    - query: Search query (don't specify subreddit - let it find discussions)
    - limit: Max posts to fetch (default: 50)
    - time_filter: Time range (default: "month")

    Returns JSON with:
    - posts: Array of post data
    - count: Number of posts found
    - quality: "HIGH" or "LOW"
    - recommendation: What to do next
    """
    args_schema: Type[BaseModel] = RedditSearchInput

    def _run(
        self,
        query: str,
        limit: int = 50,
        time_filter: str = "month"
    ) -> str:
        """
        Search Reddit and return posts with quality assessment.
        """
        print(f"\n[REDDIT_SEARCH] Searching for '{query}'...")

        # Use existing Reddit tool for the actual search
        reddit_tool = ApifyRedditSearchTool()

        try:
            # Fetch posts using the internal method
            apify_token = os.getenv("APIFY_API_TOKEN")
            if not apify_token:
                return json.dumps({
                    "error": "APIFY_API_TOKEN not found",
                    "posts": [],
                    "count": 0,
                    "quality": "LOW",
                    "recommendation": "Check API token configuration"
                })

            # Fetch posts
            all_posts = reddit_tool._fetch_single_batch(
                apify_token=apify_token,
                query=query,
                batch_size=min(limit, 100),
                subreddit=None,
                time_filter=time_filter,
                sort_by="relevance"
            )

            if not all_posts:
                return json.dumps({
                    "posts": [],
                    "count": 0,
                    "quality": "LOW",
                    "recommendation": f"No posts found for '{query}'. Try different keywords or skip to next strategy."
                })

            # Extract relevant post data
            posts_data = []
            for post in all_posts[:limit]:
                posts_data.append({
                    'title': post.get('title', 'No title'),
                    'text': post.get('body', post.get('text', ''))[:800],
                    'author': post.get('author', 'Unknown'),
                    'subreddit': post.get('subreddit', 'Unknown'),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'url': post.get('url', 'No URL'),
                    'created': post.get('created_utc', post.get('created', 'Unknown'))
                })

            # Assess quality based on relevance
            query_words = set(query.lower().split())
            relevant_count = 0
            for post in posts_data:
                combined = (post['title'] + ' ' + post['text']).lower()
                if any(word in combined for word in query_words if len(word) > 3):
                    relevant_count += 1

            relevance_ratio = relevant_count / len(posts_data) if posts_data else 0
            quality = "HIGH" if relevance_ratio > 0.3 else "LOW"

            print(f"[REDDIT_SEARCH] Found {len(posts_data)} posts, {relevant_count} relevant ({relevance_ratio*100:.0f}%)")
            print(f"[REDDIT_SEARCH] Quality: {quality}")

            recommendation = self._get_recommendation(quality, len(posts_data), query)

            return json.dumps({
                "posts": posts_data,
                "count": len(posts_data),
                "relevant_count": relevant_count,
                "relevance_ratio": round(relevance_ratio, 2),
                "quality": quality,
                "recommendation": recommendation
            }, indent=2)

        except Exception as e:
            print(f"[REDDIT_SEARCH] Error: {e}")
            return json.dumps({
                "error": str(e),
                "posts": [],
                "count": 0,
                "quality": "LOW",
                "recommendation": "Search failed. Try different query or skip to next strategy."
            })

    def _get_recommendation(self, quality: str, count: int, query: str) -> str:
        """Generate recommendation based on search results."""
        if quality == "HIGH" and count >= 20:
            return f"Proceed to reddit_score. Found {count} posts with good relevance."
        elif quality == "HIGH":
            return f"Proceed to reddit_score. Found {count} relevant posts (limited but quality)."
        elif count == 0:
            return f"No posts found. Try different query like 'frustrated with [competitor]' or 'best [category]'."
        else:
            return f"Low relevance ({count} posts). Consider different query like 'looking for {query}' or 'alternative to [competitor]'. Or skip to next strategy."


class RedditScoreTool(BaseTool):
    """
    Step 2: Score Reddit posts for buying intent.

    Takes posts from reddit_search and scores them for buying intent.
    Agent should review:
    - Many high scores (>=50)? -> Proceed to reddit_extract
    - Few high scores? -> Results may be weak, consider other strategies
    """

    name: str = "reddit_score"
    description: str = """
    Score Reddit posts for buying intent. Call after reddit_search.

    Returns scored posts. Agent should review:
    - Many high scores (>=50)? -> Proceed to reddit_extract
    - Few high scores? -> Results may be weak, consider other strategies

    Parameters:
    - posts: Posts from reddit_search (pass the posts array)
    - query: Original query for context

    Returns JSON with:
    - scored_posts: All posts with scores
    - high_quality_count: Number of posts with score >= 50
    - high_quality_posts: Only the high-scoring posts
    - recommendation: What to do next
    """
    args_schema: Type[BaseModel] = RedditScoreInput

    def _run(self, posts: List[Dict], query: str) -> str:
        """
        Score posts for buying intent.
        """
        if not posts:
            return json.dumps({
                "scored_posts": [],
                "high_quality_count": 0,
                "high_quality_posts": [],
                "recommendation": "No posts to score. Try reddit_search first."
            })

        print(f"\n[REDDIT_SCORE] Scoring {len(posts)} posts for buying intent...")

        # Use existing Reddit tool for scoring
        reddit_tool = ApifyRedditSearchTool()

        try:
            # Score posts using the batch method
            scored = reddit_tool._batch_score_posts(query, posts)

            # Merge scores with post data
            scored_posts = []
            high_quality_posts = []

            for i, (post, score_data) in enumerate(zip(posts, scored)):
                post_with_score = post.copy()
                post_with_score['intent_score'] = score_data.get('score', 50)
                post_with_score['scoring_reasoning'] = score_data.get('reasoning', 'No reasoning')
                scored_posts.append(post_with_score)

                if score_data.get('score', 0) >= 50:
                    high_quality_posts.append(post_with_score)

            print(f"[REDDIT_SCORE] {len(high_quality_posts)}/{len(posts)} posts scored >= 50")

            recommendation = self._get_recommendation(
                len(high_quality_posts),
                len(posts)
            )

            return json.dumps({
                "scored_posts": scored_posts,
                "total_scored": len(scored_posts),
                "high_quality_count": len(high_quality_posts),
                "high_quality_posts": high_quality_posts,
                "recommendation": recommendation
            }, indent=2)

        except Exception as e:
            print(f"[REDDIT_SCORE] Error: {e}")
            return json.dumps({
                "error": str(e),
                "scored_posts": [],
                "high_quality_count": 0,
                "high_quality_posts": [],
                "recommendation": "Scoring failed. Skip to next strategy."
            })

    def _get_recommendation(self, high_quality: int, total: int) -> str:
        """Generate recommendation based on scoring results."""
        if total == 0:
            return "No posts to score."

        ratio = high_quality / total

        if high_quality >= 10:
            return f"Excellent! {high_quality} high-quality posts. Proceed to reddit_extract with high_quality_posts."
        elif high_quality >= 5:
            return f"Good. {high_quality} quality posts. Proceed to reddit_extract."
        elif high_quality > 0:
            return f"Limited. Only {high_quality} quality posts. Proceed but expect fewer leads. Consider adding G2/Crunchbase."
        else:
            return "No high-quality posts found. Skip to next strategy (G2 or Crunchbase)."


class RedditExtractTool(BaseTool):
    """
    Step 3: Extract leads from scored Reddit posts.

    Takes high-quality posts and extracts author info as leads.
    IMPORTANT: These leads still need seller filtering!
    """

    name: str = "reddit_extract"
    description: str = """
    Extract leads from scored Reddit posts. Call after reddit_score.

    Extracts author info as potential leads.
    IMPORTANT: These leads still need seller filtering! Use filter_sellers tool next.

    Parameters:
    - posts: High-quality posts from reddit_score (use high_quality_posts)
    - query: Original query for context

    Returns JSON with:
    - leads: Array of extracted leads
    - count: Number of leads
    - warning: Reminder to apply seller filter
    """
    args_schema: Type[BaseModel] = RedditExtractInput

    def _run(self, posts: List[Dict], query: str = "") -> str:
        """
        Extract leads from posts.
        """
        if not posts:
            return json.dumps({
                "leads": [],
                "count": 0,
                "recommendation": "No posts to extract from. Run reddit_search and reddit_score first."
            })

        print(f"\n[REDDIT_EXTRACT] Extracting leads from {len(posts)} posts...")

        leads = []
        for post in posts:
            # Extract author as lead
            author = post.get('author', 'Unknown')
            if author in ['Unknown', '[deleted]', 'AutoModerator']:
                continue

            lead = {
                "name": author,
                "username": author,
                "title": "Founder",  # Default, can be enriched later
                "company": "Not specified",
                "linkedin_url": None,
                "email": None,
                "intent_signal": post.get('title', '')[:200],
                "intent_score": post.get('intent_score', 50),
                "source_platform": "reddit",
                "source_url": post.get('url', ''),
                "priority": self._get_priority(post.get('intent_score', 50)),
                "scoring_reasoning": post.get('scoring_reasoning', 'Extracted from Reddit post')
            }
            leads.append(lead)

        print(f"[REDDIT_EXTRACT] Extracted {len(leads)} leads")

        return json.dumps({
            "leads": leads,
            "count": len(leads),
            "warning": "APPLY filter_sellers BEFORE using these leads! Sellers must be removed.",
            "recommendation": f"Run filter_sellers on these {len(leads)} leads to remove promoters."
        }, indent=2)

    def _get_priority(self, score: int) -> str:
        """Get priority based on intent score."""
        if score >= 80:
            return "hot"
        elif score >= 60:
            return "warm"
        else:
            return "cold"


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("REDDIT STEPPED TOOLS TEST")
    print("=" * 70)

    # Test search
    search_tool = RedditSearchSteppedTool()
    search_result = search_tool._run(
        query="AI design tool",
        limit=20,
        time_filter="month"
    )
    print("\nSearch Result:")
    result_data = json.loads(search_result)
    print(f"Count: {result_data.get('count')}")
    print(f"Quality: {result_data.get('quality')}")
    print(f"Recommendation: {result_data.get('recommendation')}")
