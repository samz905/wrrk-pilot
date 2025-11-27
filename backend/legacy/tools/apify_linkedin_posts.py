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
            # Schema: keyword, sort_type, page_number, date_filter, limit
            run_input = {
                "keyword": query,
                "sort_type": "relevance",
                "page_number": 1,
                "date_filter": "",
                "limit": min(max_results, 100)
            }

            # Debug logging
            import json
            print(f"[DEBUG] Apify run_input: {json.dumps(run_input, indent=2)}")
            print(f"[DEBUG] Calling Apify actor 5QnEH5N71IK2mFLrP (LinkedIn Posts Search)...")

            try:
                # Run the Actor and wait for it to finish
                run = client.actor("5QnEH5N71IK2mFLrP").call(run_input=run_input)
                print(f"[DEBUG] Apify run completed, dataset: {run.get('defaultDatasetId', 'N/A')}")

                # Fetch results from the run's dataset
                results = []
                for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                    results.append(item)

                print(f"[DEBUG] Apify returned {len(results)} posts")

            except Exception as e:
                print(f"[ERROR] Apify failed: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                return f"Error: Apify actor failed - {str(e)}"

            if results:
                print(f"\n[DEBUG] First post keys: {list(results[0].keys())}\n")

            return self._format_results(results)

        except Exception as e:
            print(f"[ERROR] LinkedIn posts search failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
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

            # Calculate intent score (0-100)
            intent_score = self._calculate_intent_score(post_text, likes, comments)

            # Intent level classification
            if intent_score >= 80:
                intent_level = "VERY HIGH"
            elif intent_score >= 60:
                intent_level = "HIGH"
            elif intent_score >= 40:
                intent_level = "MEDIUM"
            else:
                intent_level = "LOW"

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

🎯 Intent Score: {intent_score}/100 - {intent_level}
   (Based on: Keywords + Engagement + Discussion)
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

    def _calculate_intent_score(self, text: str, likes: int, comments: int) -> int:
        """
        Calculate intent signal strength (0-100) based on post content and engagement.

        Scoring logic:
        - Disqualifying signals: Filter out sellers/promoters/job posts
        - Keyword analysis (40 points): Intent keywords in post
        - Engagement (35 points): Likes show community agreement
        - Discussion (25 points): Comments indicate active problem discussion
        """
        intent_score = 0
        text_lower = text.lower() if text else ""

        # DISQUALIFYING SIGNALS - Filter out non-buyers
        # Sellers/promoters
        seller_keywords = [
            'excited to announce', 'proud to announce', 'thrilled to share',
            'launching our', 'introducing our', 'check out our', 'our new product',
            'our solution', 'our platform', 'we built', 'we created', 'we developed',
            'join our team', 'we are hiring', "we're hiring", 'now hiring',
            'signup', 'sign up', 'get started', 'free trial', 'book a demo'
        ]
        if any(kw in text_lower for kw in seller_keywords):
            return 5  # Seller/promoter, not a buyer

        # Job posts (very common on LinkedIn)
        job_keywords = [
            'job opening', 'position available', 'now hiring', 'join our team',
            'apply now', 'send your resume', 'careers page', 'job opportunity'
        ]
        if any(kw in text_lower for kw in job_keywords):
            return 3  # Job post, not a buyer

        # Already solved their problem
        solved_keywords = [
            'finally found a solution', 'problem solved', 'switched to and love',
            'no longer struggling', 'happy to report', 'issue resolved'
        ]
        if any(kw in text_lower for kw in solved_keywords):
            return 10  # Problem already solved

        # Keyword scoring (40 points max)
        # Explicit help requests (highest intent)
        help_request_keywords = [
            'looking for recommendations', 'any suggestions', 'need help finding',
            'can anyone recommend', 'what do you all use', 'looking for a better',
            'searching for', 'trying to find', 'need a solution'
        ]
        if any(kw in text_lower for kw in help_request_keywords):
            keyword_score = 40

        # Complaints/frustrations (high intent)
        elif any(kw in text_lower for kw in ['frustrated with', 'tired of', 'sick of', 'struggling with', 'nightmare']):
            keyword_score = 32

        # Evaluation/comparison (medium-high intent)
        elif any(kw in text_lower for kw in ['vs', 'versus', 'comparing', 'alternative to', 'better than', 'switching from']):
            keyword_score = 28

        # Problem discussion (medium intent)
        elif any(kw in text_lower for kw in ['challenge', 'problem', 'issue', 'difficult', 'struggle', 'pain point']):
            keyword_score = 22

        # General discussion (low intent)
        else:
            keyword_score = 10

        intent_score += keyword_score

        # Engagement scoring (35 points max)
        # High engagement = community validation of pain point
        if likes >= 50:
            engagement_score = 35
        elif likes >= 20:
            engagement_score = 25
        elif likes >= 10:
            engagement_score = 18
        elif likes >= 5:
            engagement_score = 12
        else:
            engagement_score = 5

        intent_score += engagement_score

        # Discussion depth (25 points max)
        # More comments = validated problem with active discussion
        if comments >= 20:
            discussion_score = 25
        elif comments >= 10:
            discussion_score = 18
        elif comments >= 5:
            discussion_score = 12
        elif comments >= 2:
            discussion_score = 8
        else:
            discussion_score = 3

        intent_score += discussion_score

        return min(intent_score, 100)
