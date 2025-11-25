"""
Reddit Lead Extraction Test - Two-Task Workflow

Tests the Reddit crew's complete two-task workflow:
- Task 1: Find top N discussion URLs
- Task 2: Extract leads from those URLs

Strategy:
TASK 1 (Discussion Finding):
- Search Reddit for query "project management software"
- Score discussions for relevance (0-100)
- Return top 10 discussion URLs (agent shows "2 URLs + 8 more" in reasoning)

TASK 2 (Lead Extraction):
- Take the 10 URLs from Task 1
- Fetch those posts with ~30 comments each (parallel processing: 10 URLs per batch)
- Extract users (post authors + commenters) showing buying signals
- LLM scores each user and provides fit reasoning

Expected Output:
- List of Reddit usernames with profile URLs
- Buying signals (their specific comments/posts)
- Intent scores (0-100) and LLM-generated fit reasoning
- Source discussion context

Run with: python test_reddit_leads.py
"""

from app.crews.reddit.crew import RedditProspectingCrew


def test_reddit_lead_extraction(query: str = "project management software", desired_results: int = 10):
    """
    Test Reddit lead extraction workflow (both tasks).

    Args:
        query: Search query (default: "project management software")
        desired_results: Number of discussions to find (default: 10)
    """
    print("=" * 80)
    print("REDDIT LEAD EXTRACTION TEST - TWO-TASK WORKFLOW")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Discussions to Find: {desired_results}")
    print(f"\nTwo-Task Workflow:")
    print(f"  TASK 1: Discussion Finding")
    print(f"    - Search Reddit for '{query}'")
    print(f"    - Score discussions for relevance")
    print(f"    - Return top {desired_results} discussion URLs")
    print(f"")
    print(f"  TASK 2: Lead Extraction")
    print(f"    - Take the {desired_results} URLs from Task 1")
    print(f"    - Fetch posts with ~30 comments each")
    print(f"    - Parallel processing: 10 URLs per batch")
    print(f"    - Extract users with buying intent")
    print(f"    - Return lead list with fit reasoning")
    print("\n" + "=" * 80)
    print("Running...\n")

    # Initialize crew
    crew = RedditProspectingCrew()

    # Run BOTH tasks (crew executes sequentially: Task 1 -> Task 2)
    result = crew.crew().kickoff(inputs={
        'search_query': query,
        'desired_results': desired_results
    })

    # Display results (will be output from Task 2: Lead List)
    print("\n" + "=" * 80)
    print("RESULTS (Lead List from Task 2)")
    print("=" * 80)
    print(result)
    print("\n" + "=" * 80)
    print("✓ Two-task workflow complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Test: Extract leads from 10 discussions about project management software
    test_reddit_lead_extraction(query="project management software", desired_results=10)

    # Other test cases (uncomment to try):
    # test_reddit_lead_extraction(query="CRM software", desired_results=5)
    # test_reddit_lead_extraction(query="email marketing tools", desired_results=15)
