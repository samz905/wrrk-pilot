"""Test Google SERP actor (563JCPLOqM1kMmbbP)."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("GOOGLE SERP ACTOR TEST")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

print("\n[TEST] Testing actor 563JCPLOqM1kMmbbP (Google SERP)")
print("Query: 'companies complaining about CRM'")

try:
    # Input based on provided schema
    test_input = {
        "keyword": "companies complaining about CRM",
        "include_merged": True,
        "limit": "10",
        "country": "US",
        "hl": "en"
    }

    print(f"Input: {test_input}")
    print("\n[INFO] Starting actor run...")

    run = client.actor("563JCPLOqM1kMmbbP").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} results")

    if results:
        first_result = results[0]

        print("\n" + "=" * 70)
        print("SERP RESULT SCHEMA")
        print("=" * 70)

        print("\nAvailable fields:")
        for key in sorted(first_result.keys()):
            value = first_result[key]
            if isinstance(value, str) and len(value) > 60:
                value = value[:60] + "..."
            elif isinstance(value, dict):
                value = f"<dict with {len(value)} keys>"
            elif isinstance(value, list):
                value = f"<list with {len(value)} items>"
            print(f"  {key}: {value}")

        # Save sample
        import json
        with open("google_serp_output.json", "w", encoding="utf-8") as f:
            json.dump(results[:3], f, indent=2, ensure_ascii=False)
        print("\n[OK] Saved 3 samples to google_serp_output.json")

    else:
        print("[ERROR] No results returned")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
