"""
LinkedIn Crew End-to-End Test

Tests the full LinkedIn prospecting workflow:
1. Task 1: Find top 10 posts with intent signals for a query
2. Task 2: Extract leads with buying intent from those posts

Run with: python test_linkedin.py
"""

import json
from app.crews.linkedin.crew import LinkedInProspectingCrew


def test_linkedin_crew(query: str = "CRM software", num_results: int = 10):
    """Test LinkedIn crew end-to-end."""
    print("=" * 80)
    print("LINKEDIN CREW END-TO-END TEST")
    print("=" * 80)
    print(f"\nQuery: '{query}'")
    print(f"Desired Results: {num_results}")
    print("\nWorkflow:")
    print("  1. Task 1: Find top posts with intent signals (uses LinkedIn Posts Search tool)")
    print("  2. Task 2: Extract leads from those posts (uses LinkedIn Lead Extraction tool)")
    print("\n" + "=" * 80)
    print("Running...\n")

    crew = LinkedInProspectingCrew()
    result = crew.crew().kickoff(inputs={
        'search_query': query,
        'desired_results': num_results
    })

    print("\n" + "=" * 80)
    print("RAW RESULT")
    print("=" * 80)
    print(result.raw)

    print("\n" + "=" * 80)
    print("STRUCTURED OUTPUT (Pydantic)")
    print("=" * 80)

    try:
        if hasattr(result, 'pydantic') and result.pydantic:
            output_dict = result.pydantic.model_dump()
            print(json.dumps(output_dict, indent=2))
        else:
            print("No structured pydantic output available")
    except Exception as e:
        print(f"Error getting pydantic output: {e}")

    print("\n" + "=" * 80)
    print("✓ Test complete!")
    print("=" * 80)
    return result


def test_decision_makers(company_url: str, query: str = "engineering managers"):
    """Test the decision makers tool standalone."""
    print("=" * 80)
    print("LINKEDIN DECISION MAKERS TOOL TEST")
    print("=" * 80)
    print(f"\nCompany URL: '{company_url}'")
    print(f"Query: '{query}'")
    print("\n" + "=" * 80)
    print("Running...\n")

    from app.tools.apify_linkedin_employees import LinkedInEmployeesSearchTool

    tool = LinkedInEmployeesSearchTool()
    result = tool._run(
        company_url=company_url,
        query=query,
        max_employees=30
    )

    print(result)

    print("\n" + "=" * 80)
    print("✓ Test complete!")
    print("=" * 80)
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--decision-makers":
        # Test decision makers tool
        company = sys.argv[2] if len(sys.argv) > 2 else "https://www.linkedin.com/company/google/"
        query = sys.argv[3] if len(sys.argv) > 3 else "engineering managers"
        test_decision_makers(company, query)
    else:
        # Test main crew workflow
        query = sys.argv[1] if len(sys.argv) > 1 else "CRM software"
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        test_linkedin_crew(query=query, num_results=num)
