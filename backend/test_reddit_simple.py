"""Simple Reddit tool test."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

from tools.apify_reddit import ApifyRedditSearchTool

tool = ApifyRedditSearchTool()
print("Testing Reddit tool...")

result = tool._run(
    query="looking for CRM",
    subreddit="entrepreneur",
    time_filter="month",
    max_results=10
)

# Save to file to avoid console encoding issues
with open("reddit_test_output.txt", "w", encoding="utf-8") as f:
    f.write(result)

print("\nResults saved to reddit_test_output.txt")
print("SUCCESS - Reddit tool is working!")
