"""Twitter scraping tool using Apify ScrapeBadger - Find intent signals from tweets."""
import os
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class ApifyTwitterSearchInput(BaseModel):
    """Input schema for Twitter search."""
    query: str = Field(..., description="Search query or keywords (e.g., 'looking for CRM', 'need better sales tool')")
    query_type: str = Field(default="Top", description="Query type: 'Top' for most relevant, 'Latest' for most recent")
    max_results: int = Field(default=20, description="Maximum tweets to return (1-100)")


class ApifyTwitterSearchTool(BaseTool):
    """
    Search Twitter/X for tweets showing buying intent and pain points.

    This tool finds people actively discussing problems, asking for recommendations,
    and complaining about existing solutions - all strong intent signals.

    Best for finding:
    - Help requests: "Anyone know a good [solution]?"
    - Complaint tweets: "So frustrated with [tool]"
    - Alternative searches: "What's better than [competitor]?"
    - Problem discussions: "Struggling to find [solution]"

    Searches across all of Twitter/X to find real-time buying signals.
    """

    name: str = "Twitter Intent Search"
    description: str = """
    Search Twitter/X for tweets showing buying intent and pain points.

    Use this to find prospects who are:
    - Asking for tool recommendations
    - Complaining about current solutions
    - Discussing specific problems
    - Evaluating alternatives

    Input parameters:
    - query: Search keywords (e.g., "frustrated with Salesforce", "need CRM recommendation")
    - query_type: "Top" for most relevant tweets (default), "Latest" for most recent
    - max_results: Number of tweets to return (default: 20, max: 100)

    Returns tweets with:
    - Tweet text and metadata
    - Author information (name, username, followers)
    - Engagement metrics (likes, retweets, replies, views)
    - Intent signal scoring
    - Timestamp for recency tracking
    """
    args_schema: Type[BaseModel] = ApifyTwitterSearchInput

    def _run(
        self,
        query: str,
        query_type: str = "Top",
        max_results: int = 20
    ) -> str:
        """Execute Twitter search and return formatted results."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment variables"

        print(f"\n[INFO] Searching Twitter for: '{query}'")
        print(f"[INFO] Query type: {query_type}, Max results: {max_results}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Prepare ScrapeBadger actor input
        # Actor ID: pzMmk1t7AZ8OKJhfU (ScrapeBadger)
        run_input = {
            "mode": "Advanced Search",
            "query": query,
            "query_type": query_type,  # "Top" or "Latest"
            "max_results": min(max_results, 100)  # Cap at 100
        }

        try:
            # Run the actor
            print("[INFO] Running ScrapeBadger actor...")
            run = client.actor("pzMmk1t7AZ8OKJhfU").call(run_input=run_input)

            # Fetch results from dataset
            print("[INFO] Fetching results...")
            results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            if not results:
                return f"No tweets found for query: '{query}'"

            print(f"[OK] Found {len(results)} tweets")

            # Format results with intent scoring
            formatted_output = []
            formatted_output.append(f"=== TWITTER SEARCH RESULTS ===")
            formatted_output.append(f"Query: '{query}'")
            formatted_output.append(f"Found: {len(results)} tweets\n")

            for i, tweet in enumerate(results, 1):
                # Extract tweet data
                text = tweet.get('full_text') or tweet.get('text', 'No text')
                created_at = tweet.get('created_at_datetime', tweet.get('created_at', 'Unknown'))
                tweet_id = tweet.get('id', 'Unknown')

                # User data
                user = tweet.get('user', {})
                username = user.get('screen_name', user.get('name', 'Unknown'))
                name = user.get('name', 'Unknown')
                followers = user.get('followers_count', 0)
                verified = user.get('is_blue_verified', user.get('verified', False))

                # Engagement metrics
                likes = tweet.get('favorite_count', 0)
                retweets = tweet.get('retweet_count', 0)
                replies = tweet.get('reply_count', 0)
                views = tweet.get('view_count', 0)

                # Calculate intent score
                intent_score = self._calculate_intent_score(
                    text=text,
                    likes=likes,
                    retweets=retweets,
                    replies=replies
                )

                # Intent level classification
                if intent_score >= 80:
                    intent_level = "VERY HIGH"
                elif intent_score >= 60:
                    intent_level = "HIGH"
                elif intent_score >= 40:
                    intent_level = "MEDIUM"
                else:
                    intent_level = "LOW"

                # Format tweet entry
                formatted_output.append(f"--- Tweet {i} ---")
                formatted_output.append(f"Author: @{username} ({name})")
                if verified:
                    formatted_output.append(f"Verified: Yes")
                formatted_output.append(f"Followers: {followers}")
                formatted_output.append(f"Posted: {created_at}")
                formatted_output.append(f"Text: {text}")
                formatted_output.append(f"Engagement: {likes} likes, {retweets} retweets, {replies} replies")
                if views:
                    formatted_output.append(f"Views: {views}")
                formatted_output.append(f"Intent Score: {intent_score}/100 - {intent_level}")
                formatted_output.append(f"Tweet URL: https://twitter.com/{username}/status/{tweet_id}")
                formatted_output.append("")

            return "\n".join(formatted_output)

        except Exception as e:
            error_msg = f"Error running Twitter search: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg

    def _calculate_intent_score(self, text: str, likes: int, retweets: int, replies: int) -> int:
        """
        Calculate intent signal strength (0-100) based on tweet content and engagement.

        Scoring logic:
        - Keyword analysis (40 points): Intent keywords in tweet
        - Engagement (35 points): Likes + retweets show community agreement
        - Discussion (25 points): Replies indicate active problem discussion
        """
        intent_score = 0
        text_lower = text.lower()

        # Keyword scoring (40 points max)
        # Explicit help requests (strongest intent)
        help_request_keywords = [
            'recommend', 'recommendation', 'suggestions', 'looking for',
            'need help', 'anyone know', 'what do you use', 'best tool',
            'which tool', 'help me find'
        ]
        if any(kw in text_lower for kw in help_request_keywords):
            keyword_score = 40

        # Complaints/frustrations (high intent)
        elif any(kw in text_lower for kw in ['frustrated', 'hate', 'terrible', 'awful', 'sucks', 'worst', 'fed up']):
            keyword_score = 32

        # Evaluation/comparison (medium-high intent)
        elif any(kw in text_lower for kw in ['vs', 'versus', 'compare', 'alternative', 'better than', 'switching from']):
            keyword_score = 28

        # Problem discussion (medium intent)
        elif any(kw in text_lower for kw in ['problem', 'issue', 'struggle', 'challenge', 'difficult', 'hard to']):
            keyword_score = 22

        # General discussion (low intent)
        else:
            keyword_score = 10

        intent_score += keyword_score

        # Engagement scoring (35 points max)
        # High engagement = community validation of pain point
        engagement_total = likes + (retweets * 2)  # Retweets count double (stronger signal)
        if engagement_total >= 100:
            engagement_score = 35
        elif engagement_total >= 50:
            engagement_score = 25
        elif engagement_total >= 20:
            engagement_score = 18
        elif engagement_total >= 5:
            engagement_score = 12
        else:
            engagement_score = 5

        intent_score += engagement_score

        # Discussion depth (25 points max)
        # More replies = validated problem with active discussion
        if replies >= 20:
            discussion_score = 25
        elif replies >= 10:
            discussion_score = 18
        elif replies >= 5:
            discussion_score = 12
        elif replies >= 2:
            discussion_score = 8
        else:
            discussion_score = 3

        intent_score += discussion_score

        return min(intent_score, 100)
