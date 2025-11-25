"""Reddit scraping tool using Apify - Find intent signals from Reddit discussions."""
import os
import json
import math
from typing import Type, Optional, Tuple, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient
from openai import OpenAI


class ApifyRedditSearchInput(BaseModel):
    """Input schema for Reddit search."""
    query: str = Field(..., description="Search query or keywords (e.g., 'project management software')")
    subreddit: Optional[str] = Field(None, description="Specific subreddit or leave empty to search all Reddit")
    time_filter: str = Field(default="month", description="Time range: 'hour', 'day', 'week', 'month', 'year', 'all'")
    sort_by: str = Field(default="relevance", description="Sort order: 'relevance', 'hot', 'top', 'new', 'comments'")
    desired_results: int = Field(default=10, description="Number of high-quality results to return (will fetch 5x this amount)")


class ApifyRedditSearchTool(BaseTool):
    """
    Search Reddit for relevant discussions about any topic.

    This tool searches across all Reddit communities to find discussions related to your query.
    Use your reasoning to determine which posts contain potential leads.
    """

    name: str = "Reddit Discussion Search"
    description: str = """
    Search Reddit for discussions related to a query with parallel processing for speed.

    Input parameters:
    - query: Search keywords (what you're looking for)
    - subreddit: Optional - specific subreddit or leave empty to search all Reddit
    - time_filter: Time range (default: "month" for recent posts)
    - sort_by: Sort order (default: "relevance" for most relevant posts)
    - desired_results: Number of high-quality results to return (default: 10, max: 500)
                      System fetches 5x this amount and filters to best quality

    Returns top N Reddit posts with:
    - Post title and content
    - Author information
    - Subreddit and engagement metrics
    - Relevance score (0-100) with reasoning

    Performance: Parallel processing for large requests (~3-4 min for 500 results)
    """
    args_schema: Type[BaseModel] = ApifyRedditSearchInput

    def _fetch_single_batch(
        self,
        apify_token: str,
        query: str,
        batch_size: int,
        subreddit: Optional[str],
        time_filter: str,
        sort_by: str
    ) -> List[Dict]:
        """
        Fetch a single batch of posts from Apify.

        Args:
            apify_token: Apify API token
            query: Search query
            batch_size: Number of posts to fetch (max 100)
            subreddit: Optional subreddit filter
            time_filter: Time range filter
            sort_by: Sort order

        Returns:
            List of post dictionaries
        """
        client = ApifyClient(apify_token)

        # Build search query
        queries = [f"subreddit:{subreddit} {query}"] if subreddit else [query]

        # Prepare actor input
        run_input = {
            "queries": queries,
            "sort": sort_by,
            "timeframe": time_filter,
            "urls": [],
            "maxPosts": max(10, min(batch_size, 100)),  # Min 10, max 100
            "maxComments": 1,
            "scrapeComments": False,
            "includeNsfw": False,
        }

        try:
            # Run the actor
            run = client.actor("TwqHBuZZPHJxiQrTU").call(run_input=run_input)

            # Fetch results
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            return results

        except Exception as e:
            print(f"[ERROR] Batch fetch failed: {str(e)}")
            return []

    def _fetch_posts_parallel(
        self,
        apify_token: str,
        query: str,
        target_posts: int,
        subreddit: Optional[str],
        time_filter: str,
        sort_by: str,
        max_workers: int = 5
    ) -> List[Dict]:
        """
        Fetch posts in parallel across multiple Apify calls.

        Args:
            target_posts: Total number of posts to fetch
            max_workers: Number of parallel workers (default: 5)

        Returns:
            List of all fetched posts
        """
        BATCH_SIZE = 100  # Max posts per Apify call
        num_batches = math.ceil(target_posts / BATCH_SIZE)

        print(f"[INFO] Fetching {target_posts} posts across {num_batches} batches ({max_workers} parallel workers)...")

        all_posts = []
        seen_ids = set()  # Track post IDs to avoid duplicates

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batch fetching tasks
            future_to_batch = {
                executor.submit(
                    self._fetch_single_batch,
                    apify_token,
                    query,
                    BATCH_SIZE,
                    subreddit,
                    time_filter,
                    sort_by
                ): batch_num
                for batch_num in range(num_batches)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    batch_results = future.result()
                    # Deduplicate by post ID
                    for post in batch_results:
                        post_id = post.get('id')
                        if post_id and post_id not in seen_ids:
                            seen_ids.add(post_id)
                            all_posts.append(post)

                    completed += 1
                    print(f"[INFO] Batch {completed}/{num_batches} complete ({len(all_posts)} unique posts)")

                except Exception as e:
                    print(f"[ERROR] Batch {batch_num} failed: {str(e)}")

        print(f"[INFO] Fetching complete: {len(all_posts)} unique posts")
        return all_posts[:target_posts]  # Limit to target

    def _score_posts_parallel(
        self,
        query: str,
        posts: List[Dict],
        max_workers: int = 5
    ) -> List[Dict]:
        """
        Score posts in parallel batches.

        Args:
            query: Search query for context
            posts: List of posts to score
            max_workers: Number of parallel workers

        Returns:
            List of score dictionaries matching posts order
        """
        BATCH_SIZE = 100  # Score 100 posts per API call
        num_batches = math.ceil(len(posts) / BATCH_SIZE)

        print(f"[INFO] Scoring {len(posts)} posts across {num_batches} batches ({max_workers} parallel workers)...")

        # Split posts into batches
        post_batches = [posts[i:i+BATCH_SIZE] for i in range(0, len(posts), BATCH_SIZE)]

        all_scores = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scoring tasks
            future_to_batch = {
                executor.submit(
                    self._batch_score_posts,
                    query,
                    batch
                ): (batch_num, len(batch))
                for batch_num, batch in enumerate(post_batches)
            }

            # Collect results in order
            batch_scores = [None] * num_batches
            completed = 0

            for future in as_completed(future_to_batch):
                batch_num, batch_len = future_to_batch[future]
                try:
                    scores = future.result()
                    batch_scores[batch_num] = scores
                    completed += 1
                    print(f"[INFO] Scoring batch {completed}/{num_batches} complete")

                except Exception as e:
                    print(f"[ERROR] Scoring batch {batch_num} failed: {str(e)}")
                    # Fallback scores
                    batch_scores[batch_num] = [{"score": 50, "reasoning": "Scoring failed"} for _ in range(batch_len)]

            # Flatten scores maintaining order
            for scores in batch_scores:
                if scores:
                    all_scores.extend(scores)

        print(f"[INFO] Scoring complete: {len(all_scores)} posts scored")
        return all_scores

    def _run(
        self,
        query: str,
        subreddit: Optional[str] = None,
        time_filter: str = "month",
        sort_by: str = "relevance",
        desired_results: int = 10
    ) -> str:
        """
        Execute Reddit search with parallel processing and return formatted results.

        Args:
            query: Search query
            subreddit: Optional subreddit filter
            time_filter: Time range
            sort_by: Sort order
            desired_results: Number of high-quality results to return (default: 10, max: 500)

        Returns:
            Formatted string with top N Reddit discussions
        """

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        # Validate and cap desired_results
        desired_results = min(desired_results, 500)  # Max 500 results

        # Calculate how many posts to fetch (5x multiplier for filtering)
        MULTIPLIER = 5
        fetch_target = desired_results * MULTIPLIER

        print(f"\n[INFO] Reddit Search: '{query}'")
        if subreddit:
            print(f"[INFO] Subreddit: r/{subreddit}")
        print(f"[INFO] Strategy: Fetch {fetch_target} posts -> Filter to top {desired_results}")
        print(f"[INFO] Time: {time_filter}, Sort: {sort_by}\n")

        try:
            # STEP 1: Fetch posts (parallel if needed)
            if fetch_target <= 100:
                # Single batch - no parallel needed
                print(f"[INFO] Fetching {fetch_target} posts (single batch)...")
                all_posts = self._fetch_single_batch(
                    apify_token, query, fetch_target, subreddit, time_filter, sort_by
                )
            else:
                # Multiple batches - use parallel processing
                all_posts = self._fetch_posts_parallel(
                    apify_token, query, fetch_target, subreddit, time_filter, sort_by
                )

            if not all_posts:
                return f"No Reddit posts found for query: '{query}'"

            print(f"\n[INFO] Fetched {len(all_posts)} posts total")

            # STEP 2: Extract post data for scoring
            posts_data = []
            for post in all_posts:
                posts_data.append({
                    'title': post.get('title', 'No title'),
                    'text': post.get('body', post.get('text', ''))[:800],
                    'author': post.get('author', 'Unknown'),
                    'subreddit': post.get('subreddit', 'Unknown'),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'created': post.get('created_utc', post.get('created', 'Unknown')),
                    'url': post.get('url', 'No URL')
                })

            # STEP 3: Score posts (parallel if needed)
            if len(posts_data) <= 100:
                # Single batch scoring
                print(f"\n[INFO] Scoring {len(posts_data)} posts (single batch)...")
                scored_posts = self._batch_score_posts(query, posts_data)
            else:
                # Parallel scoring
                scored_posts = self._score_posts_parallel(query, posts_data)

            # STEP 4: Format and return results
            return self._format_results(posts_data, scored_posts, query, desired_results)

        except Exception as e:
            error_msg = f"Error in Reddit search: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def _format_results(
        self,
        posts_data: List[Dict],
        scored_posts: List[Dict],
        query: str,
        desired_results: int
    ) -> str:
        """
        Format Reddit posts into readable output.

        Args:
            posts_data: List of post dictionaries (already extracted)
            scored_posts: List of score dictionaries (already computed)
            query: Search query
            desired_results: Number of top results to return

        Returns:
            Formatted string output
        """

        output = []
        output.append("=" * 70)
        output.append(f"REDDIT LEAD SIGNALS: '{query}'")
        output.append("=" * 70)

        # Filter out low-quality posts (score < 50)
        QUALITY_THRESHOLD = 50
        filtered_posts = []
        for post_data, score_data in zip(posts_data, scored_posts):
            intent_score = score_data.get('score', 50)
            if intent_score >= QUALITY_THRESHOLD:
                filtered_posts.append((post_data, score_data))

        print(f"\n[INFO] Filtered to {len(filtered_posts)} high-quality posts (score >= {QUALITY_THRESHOLD})")

        if not filtered_posts:
            return f"No high-quality Reddit posts found for query: '{query}' (all posts scored below {QUALITY_THRESHOLD})"

        # Sort by score (highest first)
        filtered_posts.sort(key=lambda x: x[1].get('score', 0), reverse=True)

        # Limit to desired number of results
        top_posts = filtered_posts[:desired_results]

        output.append(f"\nTop {len(top_posts)} most relevant discussions (from {len(filtered_posts)} high-quality, {len(posts_data)} total fetched):\n")

        for idx, (post_data, score_data) in enumerate(top_posts, 1):
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
        output.append(f"- Returned: {len(top_posts)} high-quality discussions")
        output.append(f"- Quality posts found: {len(filtered_posts)} (from {len(posts_data)} fetched)")
        output.append(f"- Quality threshold: {QUALITY_THRESHOLD}/100")
        output.append(f"- Subreddits in results: {len(set(p[0]['subreddit'] for p in top_posts))}")
        avg_intent = sum(p[1].get('score', 0) for p in top_posts) / len(top_posts) if top_posts else 0
        output.append(f"- Average relevance score: {avg_intent:.1f}/100")
        avg_comments = sum(p[0]['num_comments'] for p in top_posts) / len(top_posts) if top_posts else 0
        output.append(f"- Average engagement: {avg_comments:.1f} comments/post")
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
