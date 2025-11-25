"""
Test LinkedIn Posts Search Tool Directly

Tests just the Apify actor to see what raw data we get back.
"""

import os
import json
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from apify_client import ApifyClient


def test_posts_search_raw(query: str = "CRM software", max_posts: int = 30):
    """Test the raw Apify actor for LinkedIn posts search."""
    print("=" * 80)
    print("LINKEDIN POSTS SEARCH - RAW API TEST")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Max Posts: {max_posts}")
    print("\n" + "=" * 80)

    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        print("ERROR: APIFY_API_TOKEN not set")
        return

    client = ApifyClient(apify_token)

    run_input = {
        "searchQuery": query,
        "maxPosts": max_posts,
        "sortType": "relevance"  # Options: "relevance" (default), "date_posted"
    }

    print(f"\n[DEBUG] Apify run_input: {json.dumps(run_input, indent=2)}")
    print(f"[DEBUG] Calling Apify actor apimaestro/linkedin-posts-search-scraper-no-cookies...")

    try:
        run = client.actor("apimaestro/linkedin-posts-search-scraper-no-cookies").call(run_input=run_input)
        print(f"[DEBUG] Run completed, dataset: {run.get('defaultDatasetId', 'N/A')}")

        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        print(f"\n[INFO] Apify returned {len(results)} posts")

        if not results:
            print("\nNo posts found!")
            return

        # Show first result structure
        print("\n" + "=" * 80)
        print("FIRST POST - RAW DATA STRUCTURE")
        print("=" * 80)
        print(f"\nKeys: {list(results[0].keys())}")
        print(f"\nFull first post:\n{json.dumps(results[0], indent=2, default=str)[:2000]}")

        # Analyze all posts
        print("\n" + "=" * 80)
        print(f"ALL {len(results)} POSTS SUMMARY")
        print("=" * 80)

        for idx, post in enumerate(results, 1):
            # Extract author info
            author = post.get('author', {})
            if isinstance(author, dict):
                author_name = author.get('name', 'N/A')
                author_title = author.get('headline', 'N/A')
                author_url = author.get('profileUrl', author.get('url', 'N/A'))
            else:
                author_name = 'N/A'
                author_title = 'N/A'
                author_url = 'N/A'

            # Extract post content
            post_text = post.get('text', post.get('content', ''))
            if post_text and len(post_text) > 150:
                post_text = post_text[:150] + "..."

            # Extract metrics
            likes = post.get('likesCount', post.get('likes', 0))
            comments = post.get('commentsCount', post.get('comments', 0))
            post_url = post.get('postUrl', post.get('url', 'N/A'))
            post_date = post.get('postedDate', post.get('date', 'N/A'))

            print(f"\n--- Post #{idx} ---")
            print(f"Author: {author_name}")
            print(f"Title: {author_title}")
            print(f"Profile: {author_url}")
            print(f"Post URL: {post_url}")
            print(f"Date: {post_date}")
            print(f"Engagement: {likes} likes, {comments} comments")
            print(f"Content: {post_text}")

        print("\n" + "=" * 80)
        print("✓ Test complete!")
        print("=" * 80)

        return results

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "CRM software"
    max_posts = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    test_posts_search_raw(query, max_posts)
