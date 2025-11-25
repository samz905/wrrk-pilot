"""Test coder_luffy/free-tweet-scraper (actually free!)."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("FREE TWEET SCRAPER TEST")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

print("\n[TEST] Testing coder_luffy/free-tweet-scraper...")
print("This actor should work on free Apify plan!")

try:
    # Try different input parameters (need to discover schema)
    test_input = {
        "query": "looking for CRM",
        "max_tweets": 20
    }

    print(f"Input (attempt 1): {test_input}")
    print("\n[INFO] Starting actor run...")

    run = client.actor("coder_luffy/free-tweet-scraper").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} tweets")

    if results:
        first_tweet = results[0]

        # Check if real data
        if "demo" in first_tweet and len(list(first_tweet.keys())) == 1:
            print("\n[ERROR] Still demo data :(")
        else:
            print("\n" + "=" * 70)
            print("SUCCESS - REAL TWEET DATA!")
            print("=" * 70)

            print("\nTweet schema:")
            for key in sorted(first_tweet.keys()):
                value = first_tweet[key]
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                print(f"  {key}: {value}")

            import json
            with open("free_twitter_output.json", "w", encoding="utf-8") as f:
                json.dump(results[:3], f, indent=2, ensure_ascii=False)
            print("\n[OK] Saved samples to free_twitter_output.json")

    else:
        print("[ERROR] No results returned")

except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nLet's see what went wrong:")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
