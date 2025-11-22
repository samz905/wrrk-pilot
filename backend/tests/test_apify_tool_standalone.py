"""Test Apify LinkedIn tool standalone (without agent)."""
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
from tools.apify_linkedin import ApifyLinkedInSearchTool

# Load environment variables
load_dotenv()

print("\n" + "=" * 60)
print("STANDALONE APIFY TOOL TEST")
print("=" * 60)

# Verify API key
apify_token = os.getenv("APIFY_API_TOKEN")
if not apify_token or apify_token.startswith("placeholder"):
    print("\n[ERROR] APIFY_API_TOKEN not set!")
    sys.exit(1)

print(f"\n[OK] APIFY_API_TOKEN: {apify_token[:20]}...")

print("\n" + "=" * 60)
print("CREATING TOOL INSTANCE")
print("=" * 60)

try:
    tool = ApifyLinkedInSearchTool()
    print(f"[OK] Tool created: {tool.name}")
except Exception as e:
    print(f"[FAIL] Failed to create tool: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("CALLING TOOL DIRECTLY")
print("=" * 60)

# Test parameters - INTENT-BASED QUERY
keywords = "looking for CRM alternative"
location = "United States"
max_results = 5  # Small number for quick test

print(f"\nSearching LinkedIn:")
print(f"  Keywords: {keywords}")
print(f"  Location: {location}")
print(f"  Max Results: {max_results}")
print("\n[INFO] This will make a REAL Apify API call...")
print("[INFO] Expected time: 1-2 minutes\n")

try:
    result = tool._run(
        keywords=keywords,
        location=location,
        max_results=max_results
    )

    print("\n" + "=" * 60)
    print("TOOL EXECUTION COMPLETE!")
    print("=" * 60)
    print("\nRESULT:\n")
    print(result)
    print("\n" + "=" * 60)

    # Check if result contains real data
    if "linkedin.com/in/" in result.lower():
        print("\n[SUCCESS] Tool returned real LinkedIn URLs!")
    else:
        print("\n[WARNING] No LinkedIn URLs found in result")

except Exception as e:
    print(f"\n[FAIL] Tool execution failed: {e}")
    import traceback
    traceback.print_exc()
