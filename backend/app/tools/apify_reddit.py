"""Reddit scraping tool using Apify - Find intent signals from Reddit discussions."""
import os
import json
from typing import Type, Optional, Tuple
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
from openai import OpenAI


class ApifyRedditSearchInput(BaseModel):
    """Input schema for Reddit search."""
    query: str = Field(..., description="Search query or keywords (e.g., 'looking for CRM alternative')")
    subreddit: Optional[str] = Field(None, description="Specific subreddit (e.g., 'sales', 'entrepreneur') or leave empty for all")
    time_filter: str = Field(default="month", description="Time range: 'hour', 'day', 'week', 'month', 'year', 'all'")
    sort_by: str = Field(default="relevance", description="Sort order: 'relevance', 'hot', 'top', 'new', 'comments'")
    max_results: int = Field(default=20, description="Maximum posts to return (1-100)")


class ApifyRedditSearchTool(BaseTool):
    """
    Search Reddit for posts and discussions showing genuine interest and pain points.

    This tool finds people actively discussing problems, asking for recommendations,
    and complaining about existing solutions across ANY topic or industry.

    Best for finding:
    - Help requests: "Can anyone recommend a [solution]?"
    - Complaint threads: "Why is [problem] so hard?"
    - Alternative searches: "Cheaper alternative to [competitor]?"
    - Problem discussions: "How do you solve [specific problem]?"

    Works across all subreddits - from technical communities to consumer forums,
    from business subreddits to hobbyist groups. The search query determines
    which communities are most relevant.
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

        # STEP 1: Extract all post data for batch scoring
        posts_data = []
        for post in results:
            posts_data.append({
                'title': post.get('title', 'No title'),
                'text': post.get('body', post.get('text', ''))[:800],  # Truncate for token limits
                'author': post.get('author', 'Unknown'),
                'subreddit': post.get('subreddit', 'Unknown'),
                'score': post.get('score', 0),
                'num_comments': post.get('num_comments', 0),
                'created': post.get('created_utc', post.get('created', 'Unknown')),
                'url': post.get('url', 'No URL')
            })

        # STEP 2: Batch score ALL posts in ONE API call
        print(f"\n[INFO] Batch scoring {len(posts_data)} posts with LLM...")
        scored_posts = self._batch_score_posts(query, posts_data)

        # STEP 3: Format output with scores
        for idx, (post_data, score_data) in enumerate(zip(posts_data, scored_posts), 1):
            intent_score = score_data.get('score', 50)
            reasoning = score_data.get('reasoning', 'No reasoning provided')

            output.append(f"Intent Signal #{idx}")
            output.append("─" * 70)
            output.append(f"Title: {post_data['title']}")
            if post_data['text'] and len(post_data['text']) > 0:
                # Truncate long posts
                display_text = post_data['text'][:300] + "..." if len(post_data['text']) > 300 else post_data['text']
                output.append(f"Content: {display_text}")
            output.append(f"\nSubreddit: r/{post_data['subreddit']}")
            output.append(f"Author: u/{post_data['author']}")
            output.append(f"Engagement: {post_data['score']} upvotes, {post_data['num_comments']} comments")
            output.append(f"Posted: {post_data['created']}")
            output.append(f"URL: {post_data['url']}")
            output.append(f"\n💡 Intent Score: {intent_score}/100")
            output.append(f"Intent Level: {self._get_intent_level(intent_score)}")
            output.append(f"Reasoning: {reasoning}")
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

    def _batch_score_posts(self, query: str, posts: list) -> list:
        """
        Score ALL posts in a SINGLE LLM API call for maximum efficiency.

        Takes up to 100 posts and returns scores for all in one request.
        Returns list of dicts: [{"score": 85, "reasoning": "..."}, ...]
        """

        if not posts:
            return []

        # Build batch prompt with all posts
        posts_text = ""
        for i, post in enumerate(posts, 1):
            posts_text += f"\n---POST {i}---\n"
            posts_text += f"Title: {post['title']}\n"
            posts_text += f"Subreddit: r/{post['subreddit']}\n"
            posts_text += f"Engagement: {post['score']} upvotes, {post['num_comments']} comments\n"
            if post['text'] and len(post['text'].strip()) > 0:
                # Show first 300 chars of content
                content_preview = post['text'][:300] + "..." if len(post['text']) > 300 else post['text']
                posts_text += f"Content: {content_preview}\n"

        prompt = f"""Score these {len(posts)} Reddit posts for relevance and buying intent related to: "{query}"

{posts_text}

For EACH post (1 through {len(posts)}), analyze:
1. RELEVANCE: Is it actually about the search query topic?
2. INTENT TYPE:
   - Actively seeking recommendations/solutions → 80-100 (HIGHEST)
   - Complaining about current tools → 60-79 (HIGH)
   - Comparing/evaluating alternatives → 60-79 (HIGH)
   - Discussing a problem that needs solving → 40-59 (MEDIUM)
   - Just sharing general thoughts → 20-39 (LOW)
   - Promoting their own product → 5-19 (DISQUALIFY)
   - Already solved their problem → 10-19 (LOW)
3. ENGAGEMENT: High upvotes/comments = validated pain point

SCORING RUBRIC:
- 80-100: Explicit request for solution + highly relevant + strong engagement
- 60-79: Clear pain point or complaint + relevant + decent engagement
- 40-59: Problem discussion + somewhat relevant
- 20-39: Tangentially related or weak signal
- 5-19: Off-topic or seller/promoter

Return ONLY a JSON array with {len(posts)} objects (no markdown, no code blocks):
[
  {{"post_number": 1, "score": 85, "reasoning": "Explicitly asking for PM tool recommendations"}},
  {{"post_number": 2, "score": 45, "reasoning": "Discusses project tracking but not seeking solutions"}},
  ...
]"""

        try:
            # Single API call for ALL posts
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            print(f"[INFO] Making single batch API call for {len(posts)} posts...")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing online discussions for buyer intent and relevance. Return only valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000  # Enough for ~100 posts with scores and reasoning
            )

            # Parse LLM response
            result_text = response.choices[0].message.content.strip()

            # Clean up common formatting issues
            result_text = result_text.replace("```json", "").replace("```", "").strip()

            scores_array = json.loads(result_text)

            print(f"[INFO] Successfully scored {len(scores_array)} posts in 1 API call")

            # Validate we got scores for all posts
            if len(scores_array) != len(posts):
                print(f"[WARNING] Expected {len(posts)} scores but got {len(scores_array)}")

            return scores_array

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM JSON response: {e}")
            print(f"[DEBUG] Raw response: {result_text[:500]}")
            # Return fallback scores
            return [{"score": 50, "reasoning": "Batch scoring parse error"} for _ in posts]

        except Exception as e:
            print(f"[ERROR] Batch scoring failed: {e}")
            import traceback
            traceback.print_exc()
            # Return fallback scores
            return [{"score": 50, "reasoning": "Batch scoring API error"} for _ in posts]

    def _calculate_intent_score_llm(self, query: str, title: str, text: str, score: int, num_comments: int) -> Tuple[int, str]:
        """
        Use LLM reasoning to calculate intent signal strength (0-100) and explain why.

        This leverages GPT-4o-mini's ability to understand context, detect subtle patterns,
        and make nuanced judgments that keyword matching cannot achieve.
        """

        # Truncate very long posts to stay within token limits
        post_text = text[:800] if len(text) > 800 else text

        # Build prompt for LLM
        prompt = f"""Analyze this Reddit post to determine if it shows genuine interest or buying intent related to the search query.

SEARCH QUERY: {query}

REDDIT POST:
Title: {title}
Content: {post_text}

Engagement: {score} upvotes, {num_comments} comments

ANALYSIS GUIDELINES:
1. Relevance: Is this post actually about the search query topic? Or is it off-topic?
2. Intent Type: Is the person:
   - Actively seeking recommendations/solutions (HIGHEST INTENT)
   - Complaining about current tools (HIGH INTENT)
   - Comparing/evaluating alternatives (HIGH INTENT)
   - Discussing a problem that needs solving (MEDIUM INTENT)
   - Just sharing general thoughts (LOW INTENT)
   - Promoting their own product (DISQUALIFY - score 5)
   - Already solved their problem (LOW INTENT - score 10)

3. Engagement Context: High upvotes/comments suggest community validation of the pain point

SCORING RUBRIC:
- 80-100: Explicit request for solution + highly relevant + strong engagement
- 60-79: Clear pain point or complaint + relevant + decent engagement
- 40-59: Problem discussion + somewhat relevant
- 20-39: Tangentially related or weak signal
- 5-19: Off-topic or seller/promoter

Return ONLY a JSON object (no markdown, no code blocks):
{{"score": <0-100>, "reasoning": "<1-2 sentence explanation>"}}"""

        try:
            # Call GPT-4o-mini for intent analysis
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing online discussions for buyer intent. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )

            # Parse LLM response
            result_text = response.choices[0].message.content.strip()

            # Clean up common formatting issues
            result_text = result_text.replace("```json", "").replace("```", "").strip()

            result = json.loads(result_text)
            intent_score = int(result.get("score", 50))
            reasoning = result.get("reasoning", "LLM analysis completed")

            return (min(max(intent_score, 0), 100), reasoning)

        except Exception as e:
            print(f"[WARNING] LLM intent scoring failed: {e}")
            # Fallback to simple heuristic if LLM fails
            return self._fallback_intent_score(query, title, post_text, score, num_comments)

    def _fallback_intent_score(self, query: str, title: str, text: str, score: int, num_comments: int) -> Tuple[int, str]:
        """Fallback scoring if LLM call fails."""
        combined = (title + " " + text).lower()

        # Basic relevance check
        query_words = query.lower().split()
        if not any(word in combined for word in query_words if len(word) > 3):
            return (15, "Low relevance to query")

        # Simple pattern matching
        if any(kw in combined for kw in ['recommend', 'looking for', 'need help']):
            return (70, "Request for recommendations")
        elif any(kw in combined for kw in ['frustrated', 'hate', 'expensive']):
            return (60, "Complaint about current solution")
        elif num_comments >= 20:
            return (55, "High engagement discussion")
        else:
            return (40, "General discussion")

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
