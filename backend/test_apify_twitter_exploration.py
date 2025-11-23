"""Explore Twitter actor input/output schema through API testing."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("TWITTER ACTOR EXPLORATION")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

# Test 1: Minimal input to discover required fields
print("\n[TEST 1] Testing minimal input...")
print("Actor: apidojo/tweet-scraper")

try:
    # Try a very simple search query
    test_input = {
        "searchTerms": ["looking for CRM"],
        "maxItems": 10
    }

    print(f"Input: {test_input}")
    print("\n[INFO] Starting actor run...")

    run = client.actor("apidojo/tweet-scraper").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} tweets")

    if results:
        print("\n" + "=" * 70)
        print("FIRST TWEET FIELDS")
        print("=" * 70)
        first_tweet = results[0]

        # Print all available fields
        print("\nAvailable fields:")
        for key in sorted(first_tweet.keys()):
            value = first_tweet[key]
            # Truncate long values for readability
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            print(f"  {key}: {value}")

        # Save full sample to file
        import json
        with open("twitter_sample_output.json", "w", encoding="utf-8") as f:
            json.dump(results[:3], f, indent=2, ensure_ascii=False)
        print("\n[OK] Saved 3 sample tweets to twitter_sample_output.json")

    else:
        print("[WARNING] No results returned")

except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nThis helps us understand actor requirements!")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
