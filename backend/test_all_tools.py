"""
Test all Apify atomic tools with 5 results each.

This script validates that all tool schemas are correct and the tools work.
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "app" / "tools"))

# Track results
TEST_RESULTS = {}


def test_tool(name: str, test_func):
    """Run a test and track results."""
    print(f"\n{'='*70}")
    print(f"TESTING: {name}")
    print("="*70)

    try:
        result = test_func()
        TEST_RESULTS[name] = {"status": "PASS", "result": result[:500] if result else "No result"}
        print(f"\n[PASS] {name} completed successfully")
        print(f"Result preview: {result[:300]}..." if result and len(result) > 300 else f"Result: {result}")
        return True
    except Exception as e:
        TEST_RESULTS[name] = {"status": "FAIL", "error": str(e)}
        print(f"\n[FAIL] {name} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_linkedin_posts():
    """Test LinkedIn Posts Search Tool."""
    from apify_linkedin_posts import ApifyLinkedInPostsSearchTool
    tool = ApifyLinkedInPostsSearchTool()
    return tool._run(
        query="CRM software recommendations",
        max_results=5
    )


def test_reddit_search():
    """Test Reddit Search Tool."""
    from apify_reddit import ApifyRedditSearchTool
    tool = ApifyRedditSearchTool()
    return tool._run(
        query="project management tool recommendation",
        subreddit=None,
        time_filter="month",
        sort_by="relevance",
        desired_results=5
    )


def test_twitter_search():
    """Test Twitter Search Tool."""
    from apify_twitter import ApifyTwitterSearchTool
    tool = ApifyTwitterSearchTool()
    return tool._run(
        query="CRM software",
        query_type="Top",
        max_results=5
    )


def test_google_serp():
    """Test Google SERP Tool."""
    from apify_google_serp import ApifyGoogleSERPTool
    tool = ApifyGoogleSERPTool()
    return tool._run(
        query="SaaS company Series A funding 2024",
        max_results=5
    )


def test_crunchbase():
    """Test Crunchbase Tool."""
    from apify_crunchbase import ApifyCrunchbaseTool
    tool = ApifyCrunchbaseTool()
    return tool._run(
        keyword="Series A SaaS",
        limit=5
    )


def test_linkedin_employees():
    """Test LinkedIn Employees Tool."""
    from apify_linkedin_employees import LinkedInEmployeesSearchTool
    tool = LinkedInEmployeesSearchTool()
    return tool._run(
        company_url="https://www.linkedin.com/company/anthropic/",
        query="VP or Director",
        max_employees=5
    )


def test_linkedin_profile_detail():
    """Test LinkedIn Profile Detail Tool."""
    from apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool
    tool = ApifyLinkedInProfileDetailTool()
    return tool._run(
        profile_url="https://www.linkedin.com/in/danielgross/"
    )


def print_summary():
    """Print test summary."""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in TEST_RESULTS.values() if r["status"] == "PASS")
    failed = sum(1 for r in TEST_RESULTS.values() if r["status"] == "FAIL")

    print(f"\nTotal: {len(TEST_RESULTS)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    for name, result in TEST_RESULTS.items():
        status = "[PASS]" if result["status"] == "PASS" else "[FAIL]"
        print(f"{status} {name}")
        if result["status"] == "FAIL":
            print(f"       Error: {result['error']}")

    print("="*70)


if __name__ == "__main__":
    # Check for API token
    if not os.getenv("APIFY_API_TOKEN"):
        print("ERROR: APIFY_API_TOKEN not set in environment")
        print("Please set it in .env file or environment variables")
        sys.exit(1)

    print("\n" + "="*70)
    print("APIFY TOOLS TEST SUITE")
    print("Testing all atomic tools with max 5 results each")
    print("="*70)

    # Run tests - comment out any you don't want to run
    tests = [
        ("LinkedIn Posts Search", test_linkedin_posts),
        ("Reddit Search", test_reddit_search),
        ("Twitter Search", test_twitter_search),
        ("Google SERP", test_google_serp),
        ("Crunchbase", test_crunchbase),
        ("LinkedIn Employees", test_linkedin_employees),
        ("LinkedIn Profile Detail", test_linkedin_profile_detail),
    ]

    for name, test_func in tests:
        test_tool(name, test_func)

    # Print summary
    print_summary()
