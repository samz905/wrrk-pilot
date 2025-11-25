"""
Reddit Crew End-to-End Test

Tests the full Reddit prospecting workflow:
1. Task 1: Find top 10 discussions for a query
2. Task 2: Extract leads with buying intent from those discussions

Run with: python test_reddit.py
"""

import json
from app.crews.reddit.crew import RedditProspectingCrew


def test_reddit_crew(query: str = "CRM software", num_results: int = 10):
    """
    Test Reddit crew end-to-end.

    Args:
        query: Search query (default: "CRM software")
        num_results: Number of discussions to find (default: 10)
    """
    print("=" * 80)
    print("REDDIT CREW END-TO-END TEST")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Desired Results: {num_results}")
    print("\nWorkflow:")
    print("  1. Task 1: Find top discussions (uses Reddit Discussion Search tool)")
    print("  2. Task 2: Extract leads from those URLs (uses Reddit Lead Extraction tool)")
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
    print("RAW RESULT")
    print("=" * 80)
    print(result.raw)

    # Try to get structured output
    print("\n" + "=" * 80)
    print("STRUCTURED OUTPUT (Pydantic)")
    print("=" * 80)

    try:
        if hasattr(result, 'pydantic') and result.pydantic:
            output_dict = result.pydantic.model_dump()
            print(json.dumps(output_dict, indent=2))
        else:
            print("No structured pydantic output available")
            print(f"Result type: {type(result)}")
            print(f"Result attributes: {dir(result)}")
    except Exception as e:
        print(f"Error getting pydantic output: {e}")

    print("\n" + "=" * 80)
    print("✓ Test complete!")
    print("=" * 80)

    return result


if __name__ == "__main__":
    # Test with CRM software query, top 10 discussions
    test_reddit_crew(query="CRM software", num_results=10)
