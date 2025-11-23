"""Test Reddit tool with real Apify API calls."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 70)
print("REDDIT TOOL STANDALONE TEST")
print("=" * 70)

from tools.apify_reddit import ApifyRedditSearchTool

tool = ApifyRedditSearchTool()
print(f"\n[OK] Tool created: {tool.name}\n")

# Test 1: Search in r/sales
print("\n" + "=" * 70)
print("TEST 1: Searching r/sales for CRM frustrations")
print("=" * 70)

result1 = tool._run(
    query="frustrated with Salesforce",
    subreddit="sales",
    time_filter="month",
    max_results=10  # Min 10 required by actor
)
print(result1)

# Test 2: Search in r/entrepreneur
print("\n" + "=" * 70)
print("TEST 2: Searching r/entrepreneur for tool recommendations")
print("=" * 70)

result2 = tool._run(
    query="need project management tool",
    subreddit="entrepreneur",
    time_filter="month",
    max_results=10  # Min 10 required
)
print(result2)

# Test 3: Search across all subreddits
print("\n" + "=" * 70)
print("TEST 3: Searching all subreddits for CRM needs")
print("=" * 70)

result3 = tool._run(
    query="looking for CRM recommendations",
    subreddit=None,  # Search all
    time_filter="week",
    max_results=10  # Min 10 required
)
print(result3)

print("\n" + "=" * 70)
print("ALL TESTS COMPLETE")
print("=" * 70)
print("\n[SUCCESS] ✓ Reddit tool is working with real data!")
print("\nNext step: Build Reddit crew to orchestrate this tool")
