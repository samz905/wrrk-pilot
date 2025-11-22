"""Test LinkedIn crew with REAL API calls."""
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n" + "=" * 60)
print("REAL LINKEDIN CREW TEST - USING ACTUAL APIs")
print("=" * 60)

# Verify API keys
apify_token = os.getenv("APIFY_API_TOKEN")
openai_key = os.getenv("OPENAI_API_KEY")

if not apify_token or apify_token.startswith("placeholder"):
    print("\n[ERROR] APIFY_API_TOKEN not set or still placeholder!")
    print("Add your real Apify token to backend/.env")
    sys.exit(1)

if not openai_key or openai_key.startswith("placeholder"):
    print("\n[ERROR] OPENAI_API_KEY not set or still placeholder!")
    print("Add your real OpenAI key to backend/.env")
    sys.exit(1)

print(f"\n[OK] APIFY_API_TOKEN: {apify_token[:20]}...")
print(f"[OK] OPENAI_API_KEY: {openai_key[:20]}...")

# Change to crew directory for yaml loading
original_dir = os.getcwd()
crew_dir = Path(__file__).parent / 'app' / 'crews' / 'linkedin'
os.chdir(crew_dir)

try:
    from crews.linkedin.crew import LinkedInProspectingCrew

    print("\n" + "=" * 60)
    print("CREATING CREW")
    print("=" * 60)

    crew_instance = LinkedInProspectingCrew()
    linkedin_crew = crew_instance.crew()

    print(f"[OK] Crew created successfully")
    print(f"[OK] Agent: {linkedin_crew.agents[0].role}")
    print(f"[OK] LLM: gpt-4o-mini")

    # Test inputs - SMALL sample for testing
    inputs = {
        "search_query": "VP Sales new hire",
        "location": "San Francisco",
        "max_results": 5  # Just 5 for quick test
    }

    print("\n" + "=" * 60)
    print("RUNNING CREW WITH REAL APIs")
    print("=" * 60)
    print(f"\nSearch Query: {inputs['search_query']}")
    print(f"Location: {inputs['location']}")
    print(f"Max Results: {inputs['max_results']}")
    print("\n[INFO] This will make real API calls to Apify and OpenAI...")
    print("[INFO] Expected time: 1-2 minutes for Apify scraping")
    print("\n" + "=" * 60 + "\n")

    # Run the crew
    result = linkedin_crew.kickoff(inputs=inputs)

    print("\n" + "=" * 60)
    print("CREW EXECUTION COMPLETE!")
    print("=" * 60)
    print("\nRESULT:\n")
    print(result.raw if hasattr(result, 'raw') else result)
    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    os.chdir(original_dir)
