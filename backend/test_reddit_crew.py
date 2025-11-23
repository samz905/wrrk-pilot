"""Test Reddit crew end-to-end."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 70)
print("REDDIT CREW END-TO-END TEST")
print("=" * 70)

from crews.reddit.crew import RedditProspectingCrew

print("\n[INFO] Initializing Reddit crew...")
crew_instance = RedditProspectingCrew()

print("[INFO] Creating crew...")
reddit_crew = crew_instance.crew()

print("[OK] Reddit crew created successfully!")
print(f"Agents: {len(reddit_crew.agents)}")
print(f"Tasks: {len(reddit_crew.tasks)}")

# Test with a real prospecting query
search_query = "looking for CRM alternative"

print(f"\n{'=' * 70}")
print(f"RUNNING CREW WITH QUERY: '{search_query}'")
print(f"{'=' * 70}\n")

print("[INFO] This will:")
print("  1. Use Reddit Discussion Search tool")
print("  2. Search r/entrepreneur, r/sales, r/startups")
print("  3. Find posts about CRM alternatives")
print("  4. Score intent and prioritize leads")
print("\n[INFO] Expected time: 1-2 minutes\n")

try:
    # Kickoff the crew
    result = reddit_crew.kickoff(inputs={"search_query": search_query})

    print("\n" + "=" * 70)
    print("REDDIT CREW RESULTS")
    print("=" * 70)

    # Save to file to avoid encoding issues
    with open("reddit_crew_output.txt", "w", encoding="utf-8") as f:
        f.write(str(result))

    print("\n[SUCCESS] Reddit crew completed!")
    print("Results saved to: reddit_crew_output.txt")
    print("\n" + "=" * 70)

except Exception as e:
    print(f"\n[ERROR] Crew execution failed: {e}")
    import traceback
    traceback.print_exc()
