"""Test Twitter tool standalone."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 70)
print("TWITTER TOOL STANDALONE TEST")
print("=" * 70)

from tools.apify_twitter import ApifyTwitterSearchTool

print("\n[INFO] Initializing Twitter tool...")
twitter_tool = ApifyTwitterSearchTool()

print("[OK] Twitter tool created!")

# Test with real query
query = "looking for CRM"

print(f"\n{'=' * 70}")
print(f"TESTING QUERY: '{query}'")
print(f"{'=' * 70}\n")

print("[INFO] Running Twitter search...")
print("[INFO] This uses ScrapeBadger actor (pzMmk1t7AZ8OKJhfU)")
print("[INFO] Cost: ~$0.004 per 20 tweets\n")

try:
    result = twitter_tool._run(
        query=query,
        query_type="Top",
        max_results=20
    )

    print("\n" + "=" * 70)
    print("TWITTER TOOL OUTPUT")
    print("=" * 70)

    # Save to file to avoid encoding issues
    with open("twitter_tool_output.txt", "w", encoding="utf-8") as f:
        f.write(result)

    print("\n[SUCCESS] Twitter tool test completed!")
    print("Results saved to: twitter_tool_output.txt")
    print("\n" + "=" * 70)

    # Print first 500 chars as preview
    print("\nPreview (first 500 chars):")
    print(result[:500] if len(result) > 500 else result)

except Exception as e:
    print(f"\n[ERROR] Tool test failed: {e}")
    import traceback
    traceback.print_exc()
