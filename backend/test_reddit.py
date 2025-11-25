"""
Reddit Lead Discovery - Flexible & Scalable Test

Tests the Reddit crew with parallel processing for any number of results (N).

Strategy:
- Fetches 5x the desired results (to account for filtering)
- Uses parallel processing for large N (>20 results)
- Batch scores all posts efficiently
- Filters out low-quality posts (score < 50)
- Returns top N most relevant discussions

Performance:
- N=10: ~30 sec (single batch)
- N=50: ~1 min (parallel: 3 batches)
- N=100: ~2 min (parallel: 5 batches)
- N=500: ~3-4 min (parallel: 25 batches)

Run with: python test_reddit.py
"""

from app.crews.reddit.crew import RedditProspectingCrew


def test_reddit_crew(query: str = "project management software", num_results: int = 50):
    """
    Test Reddit crew with flexible result count.

    Args:
        query: Search query (default: "project management software")
        num_results: Number of high-quality results to return (default: 50, max: 500)
    """
    print("=" * 80)
    print("REDDIT LEAD DISCOVERY - PARALLEL PROCESSING TEST")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Desired Results: {num_results}")
    print(f"\nStrategy:")
    print(f"  1. Fetch {num_results * 5} posts (5x multiplier)")
    if num_results * 5 > 100:
        batches = (num_results * 5 + 99) // 100
        print(f"  2. Parallel fetching: {batches} batches (5 workers)")
        print(f"  3. Parallel scoring: {batches} batches (5 workers)")
    else:
        print(f"  2. Single batch fetch")
        print(f"  3. Single batch scoring")
    print(f"  4. Filter quality (score >= 50)")
    print(f"  5. Return top {num_results}")
    print("\n" + "=" * 80)
    print("Running...\n")

    # Initialize and run crew
    crew = RedditProspectingCrew()
    result = crew.crew().kickoff(inputs={
        'search_query': query,
        'desired_results': num_results
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
    # Default test: N=50 (tests parallel processing with ~1 min runtime)
    test_reddit_crew(query="project management software", num_results=50)

    # Other test cases (uncomment to try):
    # test_reddit_crew(query="project management software", num_results=10)   # Quick test
    # test_reddit_crew(query="affordable CRM software", num_results=100)      # Medium test
    # test_reddit_crew(query="email marketing tools", num_results=500)        # Large test (3-4 min)
