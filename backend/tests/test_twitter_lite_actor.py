"""Test Twitter Scraper Lite actor (free tier friendly)."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("TWITTER SCRAPER LITE EXPLORATION")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

# Test the lite version which claims 1000 demo results on free tier
print("\n[TEST] Testing apidojo/twitter-scraper-lite...")

try:
    test_input = {
        "searchTerms": ["looking for CRM"],
        "maxTweets": 20,
        "includeSearchTerms": True
    }

    print(f"Input: {test_input}")
    print("\n[INFO] Starting actor run...")

    run = client.actor("apidojo/twitter-scraper-lite").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} tweets")

    if results:
        first_tweet = results[0]

        # Check if it's demo data
        if first_tweet.get("demo"):
            print("\n[WARNING] This is DEMO data, not real tweets")
            print("Demo data fields:", list(first_tweet.keys()))
        else:
            print("\n" + "=" * 70)
            print("REAL TWEET DATA - FIELD SCHEMA")
            print("=" * 70)

            print("\nAvailable fields:")
            for key in sorted(first_tweet.keys()):
                value = first_tweet[key]
                if isinstance(value, str) and len(value) > 80:
                    value = value[:80] + "..."
                print(f"  {key}: {value}")

            # Save samples
            import json
            with open("twitter_lite_output.json", "w", encoding="utf-8") as f:
                json.dump(results[:5], f, indent=2, ensure_ascii=False)
            print("\n[OK] Saved 5 sample tweets to twitter_lite_output.json")

    else:
        print("[ERROR] No results returned")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
