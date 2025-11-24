"""
Test Reddit crew with efficient batch scoring.

This test verifies that the Reddit tool:
1. Searches globally across all subreddits (no industry bias)
2. Uses LLM-powered relevance and intent scoring
3. Scores ALL posts in a SINGLE batch API call (not 10 individual calls)
4. Returns high-quality, relevant discussions

Run with: cd backend && source .venv/Scripts/activate && python test_reddit_batch_scoring.py
"""

from app.crews.reddit.crew import RedditProspectingCrew


def main():
    print("=" * 70)
    print("REDDIT CREW - BATCH SCORING TEST")
    print("=" * 70)
    print("\nTest Query: 'project management software'")
    print("Expected: 10 high-quality, relevant Reddit discussions")
    print("Efficiency: All posts scored in 1 LLM API call (not 10 separate calls)")
    print("\n" + "=" * 70)
    print("Starting test...\n")

    # Initialize Reddit crew
    crew = RedditProspectingCrew()

    # Run the crew with test query
    result = crew.crew().kickoff(inputs={
        'search_query': 'project management software',
        'max_results': 10
    })

    # Display results
    print("\n" + "=" * 70)
    print("TEST COMPLETE - Results Below")
    print("=" * 70)
    print(result)

    print("\n" + "=" * 70)
    print("VERIFICATION CHECKLIST:")
    print("=" * 70)
    print("[ ] Check: Are discussions actually about project management software?")
    print("[ ] Check: Do intent scores (0-100) make sense based on post content?")
    print("[ ] Check: Are reasoning explanations accurate and helpful?")
    print("[ ] Check: Did we see '[INFO] Making single batch API call for X posts'?")
    print("[ ] Check: Were all posts scored in 1 API call (not 10 separate calls)?")
    print("=" * 70)


if __name__ == "__main__":
    main()
