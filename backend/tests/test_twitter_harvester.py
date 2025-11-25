"""Test web.harvester Twitter scraper (alternative provider)."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("WEB HARVESTER TWITTER SCRAPER TEST")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

print("\n[TEST] Testing web.harvester/twitter-scraper...")

try:
    test_input = {
        "searchQuery": "looking for CRM",
        "maxResults": 20
    }

    print(f"Input: {test_input}")
    print("\n[INFO] Starting actor run...")

    run = client.actor("web.harvester/twitter-scraper").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} items")

    if results:
        first_item = results[0]

        # Check if demo or real
        if "demo" in first_item or len(list(first_item.keys())) <= 2:
            print("\n[WARNING] Appears to be demo/limited data")
            print("Fields:", list(first_item.keys()))
        else:
            print("\n" + "=" * 70)
            print("TWEET SCHEMA")
            print("=" * 70)

            print("\nFields found:")
            for key in sorted(first_item.keys()):
                value = first_item[key]
                if isinstance(value, str) and len(value) > 70:
                    value = value[:70] + "..."
                print(f"  {key}: {value}")

            import json
            with open("twitter_harvester_output.json", "w", encoding="utf-8") as f:
                json.dump(results[:3], f, indent=2, ensure_ascii=False)
            print("\n[OK] Saved sample to twitter_harvester_output.json")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
