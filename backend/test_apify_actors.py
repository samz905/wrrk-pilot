"""Find available Apify actors for LinkedIn."""
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

apify_token = os.getenv("APIFY_API_TOKEN")

print("\n" + "=" * 60)
print("SEARCHING FOR LINKEDIN ACTORS ON APIFY")
print("=" * 60)

# Search for LinkedIn actors
response = httpx.get(
    "https://api.apify.com/v2/store",
    params={
        "token": apify_token,
        "search": "linkedin",
        "limit": 10
    },
    timeout=30.0
)

if response.status_code == 200:
    data = response.json()
    print(f"\nFound {data.get('total', 0)} actors")
    print("\nTop LinkedIn Actors:\n")

    for actor in data.get('data', {}).get('items', []):
        print(f"  - {actor.get('username')}/{actor.get('name')}")
        print(f"    Title: {actor.get('title')}")
        print(f"    Stats: {actor.get('stats', {}).get('totalRuns', 0)} runs")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
