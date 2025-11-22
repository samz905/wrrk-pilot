"""Automated LinkedIn prospecting test - runs all tests without prompts."""
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "=" * 70)
print("AUTOMATED COMPREHENSIVE LINKEDIN TEST")
print("=" * 70)

# Verify API keys
apify_token = os.getenv("APIFY_API_TOKEN")
if not apify_token or apify_token.startswith("placeholder"):
    print("\n[ERROR] APIFY_API_TOKEN not set!")
    sys.exit(1)

print(f"\n[OK] APIFY_API_TOKEN: {apify_token[:20]}...")

def test_posts_search():
    """Test LinkedIn posts search for intent signals."""
    print("\n" + "=" * 70)
    print("TEST 1: INTENT SIGNAL DETECTION (Posts Search)")
    print("=" * 70)

    from tools.apify_linkedin_posts import ApifyLinkedInPostsSearchTool

    tool = ApifyLinkedInPostsSearchTool()
    print(f"[OK] Tool created: {tool.name}")

    # Search for real intent signals
    query = "looking for CRM recommendations"
    max_results = 3

    print(f"\nSearching for posts: '{query}'")
    print(f"Max results: {max_results}")
    print("\n[INFO] This will find people actively posting about needing a CRM...")
    print("[INFO] Expected time: 30-60 seconds\n")

    try:
        result = tool._run(query=query, max_results=max_results)
        print("\n" + "=" * 70)
        print("POSTS SEARCH RESULTS:")
        print("=" * 70)
        print(result)
        print("\n" + "=" * 70)

        if "Intent Signal #" in result or "Post #" in result:
            print("\n[SUCCESS] ✓ Found posts with intent signals!")
            return True
        else:
            print("\n[WARNING] No intent signals found")
            return False

    except Exception as e:
        print(f"\n[FAIL] Posts search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_profile_enrichment():
    """Test LinkedIn profile detail scraping."""
    print("\n" + "=" * 70)
    print("TEST 2: PROFILE ENRICHMENT (Email/Phone Extraction)")
    print("=" * 70)

    from tools.apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool

    tool = ApifyLinkedInProfileDetailTool()
    print(f"[OK] Tool created: {tool.name}")

    # Use a real profile URL from earlier tests
    profile_url = "https://www.linkedin.com/in/tomgwynn"

    print(f"\nEnriching profile: {profile_url}")
    print("[INFO] This will attempt to extract email, phone, and detailed data...")
    print("[INFO] Expected time: 30-60 seconds\n")

    try:
        result = tool._run(profile_url=profile_url)
        print("\n" + "=" * 70)
        print("PROFILE ENRICHMENT RESULTS:")
        print("=" * 70)
        print(result)
        print("\n" + "=" * 70)

        if "Name:" in result:
            print("\n[SUCCESS] ✓ Profile enriched successfully!")
            return True
        else:
            print("\n[WARNING] Enrichment incomplete")
            return False

    except Exception as e:
        print(f"\n[FAIL] Profile enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_people_search():
    """Test LinkedIn people search by title."""
    print("\n" + "=" * 70)
    print("TEST 3: PEOPLE SEARCH (Find by Title/Location)")
    print("=" * 70)

    from tools.apify_linkedin import ApifyLinkedInSearchTool

    tool = ApifyLinkedInSearchTool()
    print(f"[OK] Tool created: {tool.name}")

    keywords = "VP Sales"
    location = "San Francisco"
    max_results = 3

    print(f"\nSearching for: '{keywords}' in '{location}'")
    print(f"Max results: {max_results}")
    print("[INFO] Expected time: 30-60 seconds\n")

    try:
        result = tool._run(keywords=keywords, location=location, max_results=max_results)
        print("\n" + "=" * 70)
        print("PEOPLE SEARCH RESULTS:")
        print("=" * 70)
        print(result)
        print("\n" + "=" * 70)

        if "linkedin.com/in/" in result:
            print("\n[SUCCESS] ✓ Found real profiles!")
            return True
        else:
            print("\n[WARNING] No profiles found")
            return False

    except Exception as e:
        print(f"\n[FAIL] People search failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RUNNING ALL TESTS AUTOMATICALLY")
    print("=" * 70)
    print("\nNote: Each test makes real Apify API calls")
    print("Total estimated time: ~3-4 minutes\n")

    results = {
        "posts_search": False,
        "profile_enrichment": False,
        "people_search": False
    }

    # Run all tests
    results["posts_search"] = test_posts_search()
    results["profile_enrichment"] = test_profile_enrichment()
    results["people_search"] = test_people_search()

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    print("\n" + "=" * 70)
    print(f"OVERALL: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n[SUCCESS] All LinkedIn tools working! Ready for Phase 3.")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Review errors above.")
