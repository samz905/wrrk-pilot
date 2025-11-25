"""Test ScrapeBadger Twitter actor (pzMmk1t7AZ8OKJhfU)."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("SCRAPEBADGER TWITTER ACTOR TEST")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

print("\n[TEST] Testing pzMmk1t7AZ8OKJhfU (ScrapeBadger)...")
print("Description: Get Twitter data without API key")

try:
    # Test Advanced Search mode for intent signals
    test_input = {
        "mode": "Advanced Search",  # Advanced Search is the correct mode
        "query": "looking for CRM",
        "query_type": "Top",  # Top tweets (most relevant)
        "max_results": 20
    }

    print(f"Input: {test_input}")
    print("\n[INFO] Starting actor run...")

    run = client.actor("pzMmk1t7AZ8OKJhfU").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} tweets")

    if results:
        first_tweet = results[0]

        # Check if demo or real data
        if "demo" in first_tweet and len(list(first_tweet.keys())) == 1:
            print("\n[WARNING] Demo data only :(")
        else:
            print("\n" + "=" * 70)
            print("SUCCESS - REAL TWEET DATA!")
            print("=" * 70)

            print("\nTweet schema (sorted fields):")
            for key in sorted(first_tweet.keys()):
                value = first_tweet[key]
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                elif isinstance(value, dict):
                    value = f"<dict with {len(value)} keys>"
                elif isinstance(value, list):
                    value = f"<list with {len(value)} items>"
                print(f"  {key}: {value}")

            # Show a sample tweet
            print("\n" + "=" * 70)
            print("SAMPLE TWEET")
            print("=" * 70)
            print(f"Text: {first_tweet.get('text', 'N/A')}")
            print(f"Author: {first_tweet.get('author', {}).get('username', 'N/A')}")
            print(f"Likes: {first_tweet.get('like_count', 0)}")
            print(f"Retweets: {first_tweet.get('retweet_count', 0)}")
            print(f"Replies: {first_tweet.get('reply_count', 0)}")

            # Save samples
            import json
            with open("scrapebadger_output.json", "w", encoding="utf-8") as f:
                json.dump(results[:3], f, indent=2, ensure_ascii=False)
            print("\n[OK] Saved 3 samples to scrapebadger_output.json")

    else:
        print("[ERROR] No results returned")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
