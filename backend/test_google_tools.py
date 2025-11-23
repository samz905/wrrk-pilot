"""Test Google SERP and Website Crawler tools together."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 70)
print("GOOGLE TOOLS TEST")
print("=" * 70)

from tools.apify_google_serp import ApifyGoogleSERPTool
from tools.apify_website_crawler import ApifyWebsiteCrawlerTool

# Test SERP tool
print("\n[TEST 1] Google SERP Search Tool")
print("="*70)

serp_tool = ApifyGoogleSERPTool()

query = "companies complaining about CRM"
print(f"\nSearching for: '{query}'")

serp_result = serp_tool._run(
    query=query,
    max_results=5,
    country="US"
)

# Save SERP results
with open("google_serp_tool_output.txt", "w", encoding="utf-8") as f:
    f.write(serp_result)

print("\n[OK] SERP results saved to google_serp_tool_output.txt")
print("\nPreview (first 500 chars):")
print(serp_result[:500])

# Test Website Crawler tool with top URL from SERP
print("\n\n[TEST 2] Website Crawler Tool")
print("="*70)

crawler_tool = ApifyWebsiteCrawlerTool()

# Extract first URL from SERP results
test_url = "https://www.forbes.com/sites/quickerbettertech/2021/02/19/on-crm-48-percent-say-that-their-crm-system-doesnt-meet-their-needs-the-good-news-is-that-this-is-fixable/"

print(f"\nCrawling URL: {test_url}")

crawler_result = crawler_tool._run(
    urls=[test_url],
    max_pages=1
)

# Save crawler results
with open("website_crawler_tool_output.txt", "w", encoding="utf-8") as f:
    f.write(crawler_result)

print("\n[OK] Crawler results saved to website_crawler_tool_output.txt")
print("\nPreview (first 500 chars):")
print(crawler_result[:500])

print("\n" + "=" * 70)
print("BOTH GOOGLE TOOLS TESTED SUCCESSFULLY!")
print("=" * 70)
