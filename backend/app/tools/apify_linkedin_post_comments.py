"""LinkedIn Post Comments Scraper - Get engagers from LinkedIn posts."""
import os
import json
from typing import Type, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from apify_client import ApifyClient


class LinkedInPostCommentsInput(BaseModel):
    """Input schema for LinkedIn post comments scraper."""
    post_ids: List[str] = Field(..., description="List of LinkedIn post IDs or full post URLs")
    limit: int = Field(default=100, description="Maximum comments per post (max 100)")
    sort_order: str = Field(default="most recent", description="Sort order: 'most recent' or 'most relevant'")


class LinkedInPostCommentsTool(BaseTool):
    """
    Get comments and engagers from LinkedIn posts.

    This tool scrapes:
    - Comments on posts
    - Commenters' profiles (name, title, company)
    - Reactions and engagement data

    Use this to find people who are:
    - Actively engaging with relevant content
    - Discussing specific topics in comments
    - Showing interest through reactions

    This is great for finding warm leads who are already engaged with relevant topics.
    """

    name: str = "LinkedIn Post Comments Scraper"
    description: str = """
    Scrape comments and engagers from LinkedIn posts.

    Use this after finding relevant posts with LinkedInPostsSearchTool to:
    - Get all commenters on high-intent posts
    - Find people actively discussing the topic
    - Identify engaged community members

    Input parameters:
    - post_ids: List of post IDs or full post URLs
    - limit: Max comments per post (default: 100)
    - sort_order: "most recent" or "most relevant"

    Returns for each post:
    - Comment text and author
    - Author profile info (name, title, LinkedIn URL)
    - Reaction counts
    """
    args_schema: Type[BaseModel] = LinkedInPostCommentsInput

    def _run(
        self,
        post_ids: List[str],
        limit: int = 100,
        sort_order: str = "most recent"
    ) -> str:
        """Execute LinkedIn post comments scrape."""

        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            return "Error: APIFY_API_TOKEN not found in environment"

        if not post_ids:
            return "Error: No post IDs provided"

        print(f"\n[INFO] Scraping comments from {len(post_ids)} LinkedIn posts")
        print(f"[INFO] Limit: {limit} comments per post, Sort: {sort_order}")

        # Initialize Apify client
        client = ApifyClient(apify_token)

        # Prepare actor input
        # Actor: apimaestro/linkedin-post-comments-replies-engagements-scraper-no-cookies
        # Schema: postIds, page_number, sortOrder, limit
        run_input = {
            "postIds": post_ids,
            "page_number": 1,
            "sortOrder": sort_order,
            "limit": min(limit, 100)
        }

        # Debug logging
        print(f"[DEBUG] Apify run_input: {json.dumps(run_input, indent=2)}")

        try:
            # Run the actor
            print("[INFO] Running LinkedIn Post Comments actor...")
            run = client.actor("apimaestro/linkedin-post-comments-replies-engagements-scraper-no-cookies").call(run_input=run_input)

            # Fetch results
            print("[INFO] Fetching results...")
            results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            if not results:
                return f"No comments found for the provided posts"

            print(f"[OK] Found {len(results)} results")

            # Format results
            return self._format_results(results, post_ids)

        except Exception as e:
            error_msg = f"Error scraping LinkedIn post comments: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def _format_results(self, results: List[Dict[str, Any]], post_ids: List[str]) -> str:
        """Format LinkedIn post comments into structured text."""

        output = []
        output.append("=" * 70)
        output.append("LINKEDIN POST COMMENTS & ENGAGERS")
        output.append("=" * 70)
        output.append(f"\nAnalyzed {len(post_ids)} posts\n")

        all_engagers = []

        for idx, result in enumerate(results, 1):
            # Extract comment data (field names may vary)
            comment_text = result.get('text', result.get('comment', 'N/A'))
            if comment_text and len(comment_text) > 200:
                comment_text = comment_text[:200] + "..."

            # Author info
            author = result.get('author', {})
            if isinstance(author, dict):
                author_name = author.get('name', author.get('firstName', '') + ' ' + author.get('lastName', '')).strip() or 'Unknown'
                author_title = author.get('headline', author.get('title', 'N/A'))
                author_url = author.get('profileUrl', author.get('linkedinUrl', author.get('url', 'N/A')))
                author_company = author.get('company', 'N/A')
            else:
                author_name = result.get('authorName', 'Unknown')
                author_title = result.get('authorTitle', result.get('authorHeadline', 'N/A'))
                author_url = result.get('authorUrl', result.get('authorProfileUrl', 'N/A'))
                author_company = result.get('authorCompany', 'N/A')

            likes = result.get('likesCount', result.get('likes', 0))
            replies = result.get('repliesCount', result.get('replies', 0))
            timestamp = result.get('timestamp', result.get('date', 'N/A'))

            output.append(f"Comment #{idx}")
            output.append("-" * 70)
            output.append(f"Author: {author_name}")
            output.append(f"Title: {author_title}")
            output.append(f"Company: {author_company}")
            output.append(f"LinkedIn: {author_url}")
            output.append(f"\nComment: \"{comment_text}\"")
            output.append(f"Engagement: {likes} likes, {replies} replies")
            output.append(f"Posted: {timestamp}")
            output.append("")

            # Track unique engagers
            all_engagers.append({
                'name': author_name,
                'title': author_title,
                'company': author_company,
                'url': author_url,
                'comment': comment_text
            })

        output.append("=" * 70)
        output.append("\nENGAGER SUMMARY:")
        output.append(f"- Total comments analyzed: {len(results)}")
        output.append(f"- Unique engagers: {len(set(e['name'] for e in all_engagers))}")

        # List unique engagers for quick reference
        unique_engagers = {}
        for e in all_engagers:
            if e['name'] not in unique_engagers:
                unique_engagers[e['name']] = e

        output.append(f"\nTOP ENGAGERS (for lead extraction):")
        for i, (name, data) in enumerate(list(unique_engagers.items())[:10], 1):
            output.append(f"{i}. {name} - {data['title']} @ {data['company']}")

        output.append("=" * 70)

        return "\n".join(output)


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LINKEDIN POST COMMENTS TOOL TEST")
    print("=" * 70)

    tool = LinkedInPostCommentsTool()

    # Test with a sample post
    result = tool._run(
        post_ids=["7289521182721093633"],
        limit=10
    )

    print("\n" + result)
