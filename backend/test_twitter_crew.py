"""Test Twitter crew end-to-end."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 70)
print("TWITTER CREW END-TO-END TEST")
print("=" * 70)

from crews.twitter.crew import TwitterProspectingCrew

print("\n[INFO] Initializing Twitter crew...")
crew_instance = TwitterProspectingCrew()

print("[INFO] Creating crew...")
twitter_crew = crew_instance.crew()

print("[OK] Twitter crew created successfully!")
print(f"Agents: {len(twitter_crew.agents)}")
print(f"Tasks: {len(twitter_crew.tasks)}")

# Test with a real prospecting query
search_query = "looking for CRM alternative"

print(f"\n{'=' * 70}")
print(f"RUNNING CREW WITH QUERY: '{search_query}'")
print(f"{'=' * 70}\n")

print("[INFO] This will:")
print("  1. Use Twitter Intent Search tool (ScrapeBadger)")
print("  2. Search for tweets about CRM alternatives")
print("  3. Score intent and prioritize leads")
print("  4. Cost: ~$0.004 per 20 tweets")
print("\n[INFO] Expected time: 1-2 minutes\n")

try:
    # Kickoff the crew
    result = twitter_crew.kickoff(inputs={"search_query": search_query})

    print("\n" + "=" * 70)
    print("TWITTER CREW RESULTS")
    print("=" * 70)

    # Save to file to avoid encoding issues
    with open("twitter_crew_output.txt", "w", encoding="utf-8") as f:
        f.write(str(result))

    print("\n[SUCCESS] Twitter crew completed!")
    print("Results saved to: twitter_crew_output.txt")
    print("\n" + "=" * 70)

except Exception as e:
    print(f"\n[ERROR] Crew execution failed: {e}")
    import traceback
    traceback.print_exc()
