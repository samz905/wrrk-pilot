"""Test Website Crawler actor (aYG0l9s7dbB7j3gbS)."""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

print("\n" + "=" * 70)
print("WEBSITE CRAWLER ACTOR TEST")
print("=" * 70)

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

print("\n[TEST] Testing actor aYG0l9s7dbB7j3gbS (Website Content Crawler)")
print("URL: https://www.forbes.com/sites/quickerbettertech/2021/02/19/on-crm-48-percent-say-that-their-crm-system-doesnt-meet-their-needs-the-good-news-is-that-this-is-fixable/")

try:
    # Simplified input - just crawl one URL
    test_input = {
        "startUrls": [{
            "url": "https://www.forbes.com/sites/quickerbettertech/2021/02/19/on-crm-48-percent-say-that-their-crm-system-doesnt-meet-their-needs-the-good-news-is-that-this-is-fixable/"
        }],
        "maxCrawlDepth": 0,  # Don't follow links, just this page
        "maxCrawlPages": 1,  # Only 1 page
        "saveMarkdown": True,  # Get markdown content
        "htmlTransformer": "readableText",
        "readableTextCharThreshold": 100,
        "removeCookieWarnings": True,
        "blockMedia": True,
        "proxyConfiguration": { "useApifyProxy": True }
    }

    print(f"\n[INFO] Starting actor run...")
    print("[INFO] Crawling 1 page for content extraction...")

    run = client.actor("aYG0l9s7dbB7j3gbS").call(run_input=test_input)

    print(f"[OK] Actor run completed! ID: {run['id']}")
    print(f"Status: {run.get('status')}")

    # Fetch results
    print("\n[INFO] Fetching results...")
    results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    print(f"[OK] Found {len(results)} crawled pages")

    if results:
        first_result = results[0]

        print("\n" + "=" * 70)
        print("CRAWLER RESULT SCHEMA")
        print("=" * 70)

        print("\nAvailable fields:")
        for key in sorted(first_result.keys()):
            value = first_result[key]
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            elif isinstance(value, dict):
                value = f"<dict with {len(value)} keys>"
            elif isinstance(value, list):
                value = f"<list with {len(value)} items>"
            print(f"  {key}: {value}")

        # Check markdown content
        if 'markdown' in first_result:
            markdown_len = len(first_result['markdown'])
            print(f"\n[INFO] Markdown content length: {markdown_len} chars")
            print("\n[PREVIEW] First 500 chars of markdown:")
            print(first_result['markdown'][:500])

        # Save sample
        import json
        with open("website_crawler_output.json", "w", encoding="utf-8") as f:
            json.dump(results[:1], f, indent=2, ensure_ascii=False)
        print("\n[OK] Saved sample to website_crawler_output.json")

    else:
        print("[ERROR] No results returned")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
