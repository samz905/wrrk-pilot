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


class RedditLeadExtractionInput(BaseModel):
    """Input schema for Reddit lead extraction."""
    query: str = Field(..., description="Search query for context (e.g., 'project management software')")
    post_urls: List[str] = Field(..., description="List of Reddit post URLs to extract leads from (e.g., ['https://reddit.com/r/...', ...])")
    max_comments: int = Field(default=30, description="Number of comments to fetch per post (default: 30)")


# Structured output models for LLM responses
class PostScore(BaseModel):
    """Structured output for post scoring."""
    post_number: int = Field(..., description="1-indexed post number")
    score: int = Field(..., ge=0, le=100, description="Intent/relevance score 0-100")
    reasoning: str = Field(..., description="Brief explanation for the score")


class Lead(BaseModel):
    """Structured output for extracted lead."""
    username: str = Field(..., description="Reddit username without u/ prefix")
    buying_signal: str = Field(..., description="Exact quote showing buying intent (max 100 chars)")
    intent_score: int = Field(..., ge=0, le=100, description="Intent score 0-100")
    fit_reasoning: str = Field(..., description="2-3 sentence explanation of why this is a good lead")


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
        sort_by: str,
        max_comments: int = 1
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
            "maxComments": max_comments,
            "scrapeComments": max_comments > 0,
            "includeNsfw": False,
        }

        # Debug logging
        print(f"[DEBUG] Apify run_input: {json.dumps(run_input, indent=2)}")

        try:
            # Run the actor
            print(f"[DEBUG] Calling Apify actor TwqHBuZZPHJxiQrTU...")
            run = client.actor("TwqHBuZZPHJxiQrTU").call(run_input=run_input)
            print(f"[DEBUG] Apify run completed, dataset: {run.get('defaultDatasetId', 'N/A')}")

            # Fetch results
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[DEBUG] Apify returned {len(results)} posts")
            return results

        except Exception as e:
            print(f"[ERROR] Apify failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _fetch_posts_by_urls(
        self,
        apify_token: str,
        post_urls: List[str],
        max_comments: int = 30,
        max_workers: int = 5
    ) -> List[Dict]:
        """
        Fetch specific Reddit posts by their URLs with comments.

        Args:
            apify_token: Apify API token
            post_urls: List of Reddit post URLs to fetch
            max_comments: Number of comments to fetch per post (default: 30)
            max_workers: Number of parallel workers (default: 5)

        Returns:
            List of post dictionaries with comments
        """
        if not post_urls:
            return []

        # Process in batches of 10 URLs for parallel processing
        BATCH_SIZE = 10
        num_batches = math.ceil(len(post_urls) / BATCH_SIZE)

        print(f"[INFO] Fetching {len(post_urls)} posts by URL across {num_batches} batches ({max_workers} parallel workers)...")

        all_posts = []
        seen_ids = set()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Split URLs into batches
            url_batches = [post_urls[i:i+BATCH_SIZE] for i in range(0, len(post_urls), BATCH_SIZE)]

            # Submit all batch fetching tasks
            future_to_batch = {
                executor.submit(
                    self._fetch_url_batch,
                    apify_token,
                    url_batch,
                    max_comments
                ): batch_num
                for batch_num, url_batch in enumerate(url_batches)
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
                    print(f"[INFO] URL batch {completed}/{num_batches} complete ({len(all_posts)} unique posts)")

                except Exception as e:
                    print(f"[ERROR] URL batch {batch_num} failed: {str(e)}")

        print(f"[INFO] URL fetching complete: {len(all_posts)} posts retrieved")
        return all_posts

    def _fetch_url_batch(
        self,
        apify_token: str,
        urls: List[str],
        max_comments: int
    ) -> List[Dict]:
        """
        Fetch a batch of posts by their URLs using Apify.

        Args:
            apify_token: Apify API token
            urls: List of Reddit post URLs
            max_comments: Number of comments to fetch per post

        Returns:
            List of post dictionaries
        """
        client = ApifyClient(apify_token)

        # Prepare actor input with URLs
        run_input = {
            "queries": [],  # No search queries, using URLs instead
            "urls": urls,  # Specific URLs to fetch
            "maxPosts": len(urls),
            "maxComments": max_comments,
            "scrapeComments": max_comments > 0,
            "includeNsfw": False,
        }

        # Debug logging
        print(f"[DEBUG] URL batch run_input: {json.dumps(run_input, indent=2)}")

        try:
            # Run the actor
            print(f"[DEBUG] Calling Apify actor for {len(urls)} URLs...")
            run = client.actor("TwqHBuZZPHJxiQrTU").call(run_input=run_input)
            print(f"[DEBUG] URL batch run completed, dataset: {run.get('defaultDatasetId', 'N/A')}")

            # Fetch results
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)

            print(f"[DEBUG] URL batch returned {len(results)} posts with comments")
            return results

        except Exception as e:
            print(f"[ERROR] URL batch fetch failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
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
        BATCH_SIZE = 50  # Score 50 posts per API call (reduced from 100 to avoid JSON truncation)
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
            if len(posts_data) <= 50:
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

    def extract_leads(
        self,
        query: str,
        post_urls: List[str],
        max_comments: int = 30
    ) -> str:
        """
        Extract individual Reddit users with buying intent from specific post URLs.

        Takes a list of Reddit post URLs (from Task 1), fetches those posts with comments,
        then extracts specific users (both post authors and commenters) who show buying signals.

        Args:
            query: Search query for context (e.g., "project management software")
            post_urls: List of Reddit post URLs to analyze
            max_comments: Number of comments to fetch per post (default: 30)

        Returns:
            Formatted list of Reddit users with buying intent, including:
            - Username and URL
            - Buying signal (their specific comment/post)
            - Intent score and fit reasoning
            - Source discussion context
        """

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        if not post_urls:
            return "Error: No post URLs provided for lead extraction"

        print(f"\n[INFO] Reddit Lead Extraction from URLs")
        print(f"[INFO] Search Context: '{query}'")
        print(f"[INFO] Posts to analyze: {len(post_urls)}")
        print(f"[INFO] Fetching {max_comments} comments per post\n")

        try:
            # STEP 1: Fetch posts by URLs WITH comments
            all_posts = self._fetch_posts_by_urls(
                apify_token,
                post_urls,
                max_comments=max_comments
            )

            if not all_posts:
                return f"No Reddit posts retrieved from {len(post_urls)} URLs"

            print(f"\n[INFO] Successfully fetched {len(all_posts)} posts with comments")

            # STEP 2: Extract post data with comments
            posts_data = []
            for post in all_posts:
                # Extract comments
                comments_raw = post.get('comments', [])
                comments_list = []
                for comment in comments_raw[:max_comments]:
                    comment_text = comment.get('text', comment.get('body', ''))
                    comment_author = comment.get('author', 'Unknown')
                    if comment_text and comment_author and comment_author != '[deleted]':
                        comments_list.append({
                            'author': comment_author,
                            'text': comment_text[:500]  # Limit comment length
                        })

                posts_data.append({
                    'title': post.get('title', 'No title'),
                    'text': post.get('body', post.get('text', ''))[:800],
                    'author': post.get('author', 'Unknown'),
                    'subreddit': post.get('subreddit', 'Unknown'),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'created': post.get('created_utc', post.get('created', 'Unknown')),
                    'url': post.get('url', 'No URL'),
                    'comments': comments_list
                })

            print(f"[INFO] Analyzing {len(posts_data)} discussions for leads...")

            # STEP 3: Extract leads from all discussions (no filtering needed - Task 1 already filtered)
            all_leads = []
            for idx, post_data in enumerate(posts_data, 1):
                print(f"[INFO] Extracting leads from discussion {idx}/{len(posts_data)}...")
                # Pass query for context-aware lead extraction
                leads = self._extract_leads_from_discussion_v2(query, post_data)
                all_leads.extend(leads)

            # STEP 4: Format and return results
            return self._format_lead_results(all_leads, query, len(post_urls))

        except Exception as e:
            error_msg = f"Error in Reddit lead extraction: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def _extract_leads_from_discussion(
        self,
        query: str,
        post_data: Dict,
        score_data: Dict
    ) -> List[Dict]:
        """
        Extract individual users with buying intent from a single discussion.

        Uses LLM to analyze the post and comments to identify users showing
        buying signals (asking for recommendations, complaining about tools, etc.)

        Args:
            query: Search query for context
            post_data: Post data including comments
            score_data: Discussion score data

        Returns:
            List of lead dictionaries with user info and buying signals
        """

        # Build prompt for LLM to extract leads
        prompt = f"""Analyze this Reddit discussion to extract individual users who show BUYING INTENT for: "{query}"

DISCUSSION:
Title: {post_data['title']}
Subreddit: r/{post_data['subreddit']}
URL: {post_data['url']}

ORIGINAL POST by u/{post_data['author']}:
{post_data['text'][:600]}

COMMENTS:
"""

        # Add comments to prompt
        for i, comment in enumerate(post_data.get('comments', [])[:20], 1):
            prompt += f"\n{i}. u/{comment['author']}: {comment['text'][:300]}\n"

        prompt += f"""

TASK: Extract users (post author OR commenters) who show BUYING INTENT:
- Actively seeking recommendations or solutions
- Complaining about current tools/solutions
- Asking "what should I use?" or "any alternatives?"
- Sharing specific pain points or problems
- Comparing/evaluating options

For EACH user with buying intent, return:
1. username (without 'u/' prefix)
2. buying_signal (exact quote showing their intent - keep it concise, max 100 chars)
3. intent_score (0-100, how strong is their buying intent)
4. fit_reasoning (2-3 sentences: why this user is a good lead, what problem they have, why they're likely to buy)

IMPORTANT:
- Only include users who show GENUINE buying intent (not casual discussion)
- Original poster counts as a lead if they show intent
- Commenters who just agree but don't show intent should be excluded
- Look for action-oriented language ("need", "looking for", "frustrated with")

Return ONLY a JSON array (no markdown, no code blocks):
[
  {{
    "username": "john_doe",
    "buying_signal": "Does anyone know a better PM tool? Asana is too expensive",
    "intent_score": 85,
    "fit_reasoning": "User is actively seeking alternatives to Asana, specifically due to pricing concerns. Shows high purchase intent and clear pain point. Ready to evaluate new options immediately."
  }},
  ...
]

If NO users show buying intent, return an empty array: []
"""

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying buying signals in online discussions. Extract only users with genuine purchase intent. Return valid JSON arrays only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )

            result_text = response.choices[0].message.content.strip()
            result_text = result_text.replace("```json", "").replace("```", "").strip()

            leads_array = json.loads(result_text)

            # Enrich leads with context
            enriched_leads = []
            for lead in leads_array:
                enriched_leads.append({
                    'username': lead.get('username', 'Unknown'),
                    'url': f"https://reddit.com/u/{lead.get('username', 'Unknown')}",
                    'buying_signal': lead.get('buying_signal', 'No signal captured'),
                    'intent_score': lead.get('intent_score', 50),
                    'fit_reasoning': lead.get('fit_reasoning', 'No reasoning provided'),
                    'source_post': {
                        'title': post_data['title'],
                        'url': post_data['url'],
                        'subreddit': post_data['subreddit'],
                        'discussion_score': score_data.get('score', 0)
                    }
                })

            print(f"[INFO] Extracted {len(enriched_leads)} leads from this discussion")
            return enriched_leads

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse lead extraction JSON: {e}")
            print(f"[DEBUG] Raw response: {result_text[:500]}")
            return []

        except Exception as e:
            print(f"[ERROR] Lead extraction failed for discussion: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_leads_from_discussion_v2(
        self,
        query: str,
        post_data: Dict
    ) -> List[Dict]:
        """
        Extract individual users with buying intent from a single discussion (v2 - with query context).

        Uses LLM to analyze the post and comments to identify users showing
        buying signals. Uses the search query for context.

        Args:
            query: Search query for context (e.g., "project management software")
            post_data: Post data including comments

        Returns:
            List of lead dictionaries with user info and buying signals
        """

        # Build prompt for LLM to extract leads
        prompt = f"""Analyze this Reddit discussion to extract individual users who show BUYING INTENT for: "{query}"

DISCUSSION:
Title: {post_data['title']}
Subreddit: r/{post_data['subreddit']}
URL: {post_data['url']}

ORIGINAL POST by u/{post_data['author']}:
{post_data['text'][:600]}

COMMENTS:
"""

        # Add comments to prompt
        for i, comment in enumerate(post_data.get('comments', [])[:20], 1):
            prompt += f"\n{i}. u/{comment['author']}: {comment['text'][:300]}\n"

        prompt += f"""

TASK: Extract users (post author OR commenters) who show BUYING INTENT related to the topic discussed:
- Actively seeking recommendations or solutions
- Complaining about current tools/solutions
- Asking "what should I use?" or "any alternatives?"
- Sharing specific pain points or problems
- Comparing/evaluating options

For EACH user with buying intent, return:
1. username (without 'u/' prefix)
2. buying_signal (exact quote showing their intent - keep it concise, max 100 chars)
3. intent_score (0-100, how strong is their buying intent)
4. fit_reasoning (2-3 sentences: why this user is a good lead, what problem they have, why they're likely to buy)

IMPORTANT:
- Only include users who show GENUINE buying intent (not casual discussion)
- Original poster counts as a lead if they show intent
- Commenters who just agree but don't show intent should be excluded
- Look for action-oriented language ("need", "looking for", "frustrated with")

Return ONLY a JSON array (no markdown, no code blocks):
[
  {{
    "username": "john_doe",
    "buying_signal": "Does anyone know a better PM tool? Asana is too expensive",
    "intent_score": 85,
    "fit_reasoning": "User is actively seeking alternatives to Asana, specifically due to pricing concerns. Shows high purchase intent and clear pain point. Ready to evaluate new options immediately."
  }},
  ...
]

If NO users show buying intent, return an empty leads array.
"""

        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # JSON schema for structured output
            json_schema = {
                "name": "lead_extraction",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "leads": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "buying_signal": {"type": "string"},
                                    "intent_score": {"type": "integer"},
                                    "fit_reasoning": {"type": "string"}
                                },
                                "required": ["username", "buying_signal", "intent_score", "fit_reasoning"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["leads"],
                    "additionalProperties": False
                }
            }

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying buying signals in online discussions. Extract only users with genuine purchase intent."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
                temperature=0.3,
                max_tokens=1500
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            leads_array = result.get("leads", [])

            # Enrich leads with context
            enriched_leads = []
            for lead in leads_array:
                enriched_leads.append({
                    'username': lead.get('username', 'Unknown'),
                    'url': f"https://reddit.com/u/{lead.get('username', 'Unknown')}",
                    'buying_signal': lead.get('buying_signal', 'No signal captured'),
                    'intent_score': lead.get('intent_score', 50),
                    'fit_reasoning': lead.get('fit_reasoning', 'No reasoning provided'),
                    'source_post': {
                        'title': post_data['title'],
                        'url': post_data['url'],
                        'subreddit': post_data['subreddit'],
                        'discussion_score': 0  # No score available in v2
                    }
                })

            print(f"[INFO] Extracted {len(enriched_leads)} leads from this discussion (structured)")
            return enriched_leads

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse lead extraction JSON: {e}")
            print(f"[DEBUG] Raw response: {result_text[:500]}")
            return []

        except Exception as e:
            print(f"[ERROR] Lead extraction failed for discussion: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _format_lead_results(
        self,
        leads: List[Dict],
        query: str,
        num_posts: int
    ) -> str:
        """
        Format extracted leads into readable output.

        Args:
            leads: List of lead dictionaries
            query: Search query
            num_posts: Number of posts analyzed

        Returns:
            Formatted string output
        """

        output = []
        output.append("=" * 70)
        output.append(f"REDDIT LEADS WITH BUYING INTENT: '{query}'")
        output.append("=" * 70)

        if not leads:
            return f"\n".join(output) + f"\n\nNo leads with buying intent found from {num_posts} discussions analyzed."

        # Sort leads by intent score (highest first)
        leads.sort(key=lambda x: x.get('intent_score', 0), reverse=True)

        output.append(f"\nExtracted {len(leads)} Reddit users with buying intent from {num_posts} high-quality discussions:\n")

        for idx, lead in enumerate(leads, 1):
            output.append(f"LEAD #{idx}")
            output.append("-" * 70)
            output.append(f"Username: u/{lead['username']}")
            output.append(f"Profile URL: {lead['url']}")
            output.append(f"\nBuying Signal:")
            output.append(f'  "{lead["buying_signal"]}"')
            output.append(f"\nIntent Score: {lead['intent_score']}/100 {self._get_intent_emoji(lead['intent_score'])}")
            output.append(f"\nFit Reasoning:")
            output.append(f"  {lead['fit_reasoning']}")
            output.append(f"\nSource Discussion:")
            output.append(f"  Title: {lead['source_post']['title']}")
            output.append(f"  Subreddit: r/{lead['source_post']['subreddit']}")
            output.append(f"  Discussion Quality: {lead['source_post']['discussion_score']}/100")
            output.append(f"  URL: {lead['source_post']['url']}")
            output.append("")

        output.append("=" * 70)
        output.append("\nLEAD INSIGHTS:")
        output.append(f"- Total leads extracted: {len(leads)}")
        output.append(f"- Discussions analyzed: {num_posts}")
        avg_intent = sum(lead['intent_score'] for lead in leads) / len(leads) if leads else 0
        output.append(f"- Average intent score: {avg_intent:.1f}/100")

        # Count unique subreddits
        unique_subreddits = set(lead['source_post']['subreddit'] for lead in leads)
        output.append(f"- Subreddits represented: {len(unique_subreddits)}")

        # Count high-intent leads (>= 80)
        high_intent_count = sum(1 for lead in leads if lead['intent_score'] >= 80)
        output.append(f"- High-intent leads (>=80): {high_intent_count}")

        output.append("=" * 70)

        return "\n".join(output)

    def _get_intent_emoji(self, score: int) -> str:
        """Get emoji for intent score level."""
        if score >= 80:
            return "🔥"
        elif score >= 60:
            return "🟢"
        elif score >= 40:
            return "🟡"
        else:
            return "🔵"

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

        Takes up to 50 posts and returns scores for all in one request.
        Returns list of dicts: [{"score": 85, "reasoning": "..."}, ...]

        NOTE: Limited to 50 posts to avoid JSON truncation errors.
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
            # Single API call for ALL posts with structured output
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            print(f"[INFO] Making single batch API call for {len(posts)} posts (structured output)...")

            # JSON schema for structured output
            json_schema = {
                "name": "post_scores",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "scores": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "post_number": {"type": "integer"},
                                    "score": {"type": "integer"},
                                    "reasoning": {"type": "string"}
                                },
                                "required": ["post_number", "score", "reasoning"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["scores"],
                    "additionalProperties": False
                }
            }

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing online discussions for buyer intent and relevance."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
                temperature=0.3,
                max_tokens=2000
            )

            # Parse structured response
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            scores_array = result.get("scores", [])

            print(f"[INFO] Successfully scored {len(scores_array)} posts in 1 API call (structured)")

            # Validate we got scores for all posts
            if len(scores_array) != len(posts):
                print(f"[WARNING] Expected {len(posts)} scores but got {len(scores_array)}")

            return scores_array

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM JSON response: {e}")
            print(f"[DEBUG] Raw response: {result_text[:500] if 'result_text' in dir() else 'N/A'}")
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


class RedditLeadExtractionTool(BaseTool):
    """
    Extract individual Reddit users with buying intent from specific Reddit post URLs.

    This tool takes a list of Reddit post URLs (from Task 1), fetches those posts with comments,
    then extracts specific users (both post authors and commenters) who show buying signals.
    """

    name: str = "Reddit Lead Extraction"
    description: str = """
    Extract individual Reddit users with buying intent from specific Reddit post URLs.

    Input parameters:
    - query: Search query for context (e.g., "project management software") - helps LLM identify relevant buying intent
    - post_urls: List of Reddit post URLs to analyze (from Task 1 discussion finding)
    - max_comments: Number of comments to fetch per post (default: 30)

    Returns list of Reddit users with:
    - Username and profile URL
    - Buying signal (their specific comment/post showing intent)
    - Intent score (0-100) and fit reasoning
    - Source discussion context

    This tool processes URLs in parallel batches of 10 for optimal performance.
    Use this to extract actual people (Reddit users) who are actively looking for solutions,
    complaining about tools, or showing pain points in their posts/comments.
    """
    args_schema: Type[BaseModel] = RedditLeadExtractionInput

    def _run(
        self,
        query: str,
        post_urls: List[str],
        max_comments: int = 30
    ) -> str:
        """
        Execute Reddit lead extraction workflow.

        This wraps the extract_leads() method from ApifyRedditSearchTool.
        """
        # Create instance of the search tool to use its extract_leads method
        search_tool = ApifyRedditSearchTool()

        # Call the extract_leads method
        return search_tool.extract_leads(
            query=query,
            post_urls=post_urls,
            max_comments=max_comments
        )


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
