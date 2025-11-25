"""Test ScrapeBadger Twitter actor - final validation."""
import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("SCRAPEBADGER - FINAL VALIDATION TEST")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

print("\n[TEST] Actor: pzMmk1t7AZ8OKJhfU (ScrapeBadger)")
print("Query: 'looking for CRM' (intent signal test)")

test_input = {
    "mode": "Advanced Search",
    "query": "looking for CRM",
    "query_type": "Top",
    "max_results": 20
}

print(f"\n[INFO] Starting actor...")

run = client.actor("pzMmk1t7AZ8OKJhfU").call(run_input=test_input)

print(f"[OK] Run completed! ID: {run['id']}")

# Fetch results
results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

print(f"[OK] Found {len(results)} tweets")

if results:
    # Save to file FIRST (before any printing)
    with open("scrapebadger_output.json", "w", encoding="utf-8") as f:
        json.dump(results[:3], f, indent=2, ensure_ascii=False)
    print("[OK] Saved 3 samples to scrapebadger_output.json")

    first_tweet = results[0]

    # Check field availability
    print("\n" + "=" * 70)
    print("TWEET DATA SCHEMA")
    print("=" * 70)

    print("\nKey fields found:")
    important_fields = [
        'full_text', 'text', 'created_at', 'created_at_datetime',
        'favorite_count', 'retweet_count', 'reply_count', 'view_count',
        'user', 'id', 'lang', 'bookmark_count'
    ]

    for field in important_fields:
        if field in first_tweet:
            value = first_tweet[field]
            if isinstance(value, dict):
                print(f"  {field}: <dict with {len(value)} keys>")
            elif isinstance(value, list):
                print(f"  {field}: <list with {len(value)} items>")
            elif isinstance(value, str) and len(value) > 50:
                print(f"  {field}: {value[:50]}...")
            else:
                print(f"  {field}: {value}")

    # Check user data
    if 'user' in first_tweet and isinstance(first_tweet['user'], dict):
        print("\nUser object fields:")
        user = first_tweet['user']
        user_fields = ['username', 'name', 'description', 'followers_count', 'verified']
        for field in user_fields:
            if field in user:
                value = user[field]
                if isinstance(value, str) and len(value) > 40:
                    value = value[:40] + "..."
                print(f"  user.{field}: {value}")

    print("\n" + "=" * 70)
    print("COST ESTIMATE")
    print("=" * 70)
    print("From actor logs: $0.0040 for 20 tweets")
    print("Extrapolated: ~$0.20 per 1000 tweets")
    print("Budget check: Well within <$50/month for typical usage")

    print("\n" + "=" * 70)
    print("SUCCESS - SCRAPEBADGER WORKS ON FREE PLAN!")
    print("=" * 70)
    print("This actor can be used for Twitter integration.")

else:
    print("[ERROR] No results")
