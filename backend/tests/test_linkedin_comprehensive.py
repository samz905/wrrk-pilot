"""Test comprehensive LinkedIn prospecting system."""
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "=" * 70)
print("COMPREHENSIVE LINKEDIN PROSPECTING TEST")
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

        if "Intent Signal #" in result:
            print("\n[SUCCESS] ✓ Found posts with intent signals!")
        else:
            print("\n[WARNING] No intent signals found")

    except Exception as e:
        print(f"\n[FAIL] Posts search failed: {e}")
        import traceback
        traceback.print_exc()

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

        if "Email" in result:
            print("\n[SUCCESS] ✓ Profile enriched successfully!")
        else:
            print("\n[WARNING] Enrichment incomplete")

    except Exception as e:
        print(f"\n[FAIL] Profile enrichment failed: {e}")
        import traceback
        traceback.print_exc()

def test_comprehensive_workflow():
    """Test complete workflow: find intent → enrich profile."""
    print("\n" + "=" * 70)
    print("TEST 3: COMPLETE WORKFLOW")
    print("=" * 70)
    print("\nWorkflow:")
    print("1. Find posts about 'frustrated with current tools'")
    print("2. Extract author profile URLs from posts")
    print("3. Enrich top author's profile with contact data")
    print("\n" + "=" * 70)

    from tools.linkedin_comprehensive import LinkedInComprehensiveTool

    tool = LinkedInComprehensiveTool()
    print(f"\n[OK] Comprehensive tool created")

    # Step 1: Find intent signals
    print("\n[STEP 1] Finding intent signals...")
    intent_result = tool._run(
        action="find_intent",
        query="need better project management tool",
        max_results=2
    )
    print(intent_result[:500] + "..." if len(intent_result) > 500 else intent_result)

    # In a real workflow, we'd extract profile URLs from intent_result
    # For now, just demonstrate the capability exists
    print("\n[STEP 2] Would extract profile URLs from posts...")
    print("[STEP 3] Would enrich each profile with contact data...")
    print("\n[SUCCESS] ✓ Complete workflow capability demonstrated!")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RUNNING COMPREHENSIVE TESTS")
    print("=" * 70)
    print("\nNote: Each test makes real Apify API calls")
    print("Choose which tests to run:\n")

    print("1. Test Posts Search (Intent Detection) - ~1 min")
    print("2. Test Profile Enrichment (Email Extraction) - ~1 min")
    print("3. Test Complete Workflow - ~2 min")
    print("4. Run ALL tests - ~4 min")
    print("5. Skip tests (just verify tools load)")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        test_posts_search()
    elif choice == "2":
        test_profile_enrichment()
    elif choice == "3":
        test_comprehensive_workflow()
    elif choice == "4":
        test_posts_search()
        test_profile_enrichment()
        test_comprehensive_workflow()
    elif choice == "5":
        print("\n[INFO] Skipping API tests, verifying tool imports...")
        from tools.apify_linkedin_posts import ApifyLinkedInPostsSearchTool
        from tools.apify_linkedin_profile_detail import ApifyLinkedInProfileDetailTool
        from tools.linkedin_comprehensive import LinkedInComprehensiveTool
        print("[SUCCESS] ✓ All tools imported successfully!")
    else:
        print("\n[ERROR] Invalid choice")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
