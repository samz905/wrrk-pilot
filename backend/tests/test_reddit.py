"""
Reddit Lead Discovery - Final Test

Tests the Reddit crew to find the top 10 most relevant discussions for a given query.

Strategy:
- Fetches 50 posts from Reddit with relevance sorting
- Batch scores all 50 in ONE LLM API call (efficient)
- Filters out low-quality posts (score < 50)
- Returns top 10 most relevant discussions

Run with: python test_reddit.py
"""

from app.crews.reddit.crew import RedditProspectingCrew


def test_reddit_crew(query: str = "project management software"):
    """
    Test Reddit crew with a query.

    Args:
        query: Search query (default: "project management software")
    """
    print("=" * 80)
    print("REDDIT LEAD DISCOVERY TEST")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print("\nHow it works:")
    print("  1. Fetch 50 posts from Reddit (relevance sorted)")
    print("  2. Batch score all 50 posts in 1 LLM API call")
    print("  3. Filter to high-quality only (score >= 50)")
    print("  4. Return top 10 most relevant discussions")
    print("\n" + "=" * 80)
    print("Running...\n")

    # Initialize and run crew
    crew = RedditProspectingCrew()
    result = crew.crew().kickoff(inputs={
        'search_query': query,
        'max_results': 50  # Fetch 50, return top 10 after filtering
    })

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(result)
    print("\n" + "=" * 80)
    print("✓ Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    # You can change the query here
    test_reddit_crew(query="project management software")

    # Try other queries:
    # test_reddit_crew(query="affordable CRM software")
    # test_reddit_crew(query="best note-taking app")
    # test_reddit_crew(query="email marketing tools")
