"""Test script for LinkedIn crew."""
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_crew_creation():
    """Test that crew can be created."""
    print("=" * 60)
    print("TESTING LINKEDIN CREW CREATION")
    print("=" * 60)

    try:
        # Change to the linkedin crew directory for yaml loading
        original_dir = os.getcwd()
        crew_dir = Path(__file__).parent / 'app' / 'crews' / 'linkedin'
        os.chdir(crew_dir)

        from crews.linkedin.crew import LinkedInProspectingCrew

        crew_instance = LinkedInProspectingCrew()
        print("[OK] LinkedInProspectingCrew instantiated successfully")

        # Get the crew
        linkedin_crew = crew_instance.crew()
        print(f"[OK] Crew created with {len(linkedin_crew.agents)} agent(s)")
        print(f"[OK] Crew has {len(linkedin_crew.tasks)} task(s)")

        os.chdir(original_dir)
        return crew_instance

    except Exception as e:
        print(f"[FAIL] Failed to create crew: {e}")
        import traceback
        traceback.print_exc()
        os.chdir(original_dir)
        return None

def test_crew_kickoff(skip_execution=True):
    """Test running the crew with sample input."""
    print("\n" + "=" * 60)
    print("TESTING LINKEDIN CREW EXECUTION")
    print("=" * 60)

    if skip_execution:
        print("\n[SKIP] Skipping crew execution test (requires real API keys)")
        print("To run a real test, add valid API keys to .env and call:")
        print("  test_crew_kickoff(skip_execution=False)")
        return

    print("\nNOTE: This will make a real API call to Apify and Claude.")
    print("Make sure you have valid API keys in your .env file.")
    print("=" * 60)

    try:
        # Change to crew directory
        original_dir = os.getcwd()
        crew_dir = Path(__file__).parent / 'app' / 'crews' / 'linkedin'
        os.chdir(crew_dir)

        from crews.linkedin.crew import LinkedInProspectingCrew

        crew_instance = LinkedInProspectingCrew()
        linkedin_crew = crew_instance.crew()

        # Test inputs
        inputs = {
            "search_query": "VP Sales looking for CRM",
            "location": "United States",
            "max_results": 10  # Small number for testing
        }

        print(f"\n[INFO] Running crew with inputs:")
        print(f"  - Search Query: {inputs['search_query']}")
        print(f"  - Location: {inputs['location']}")
        print(f"  - Max Results: {inputs['max_results']}")
        print("\n[INFO] This may take a few minutes...\n")

        # Kickoff the crew
        result = linkedin_crew.kickoff(inputs=inputs)

        print("\n" + "=" * 60)
        print("CREW EXECUTION COMPLETE")
        print("=" * 60)
        print("\nResult:")
        print(result.raw if hasattr(result, 'raw') else result)

        os.chdir(original_dir)

    except Exception as e:
        print(f"\n[FAIL] Crew execution failed: {e}")
        import traceback
        traceback.print_exc()
        os.chdir(original_dir)

if __name__ == "__main__":
    print("\nPHASE 2: LINKEDIN CREW TEST\n")

    # Test 1: Crew creation
    crew_instance = test_crew_creation()

    # Test 2: Crew execution (optional)
    if crew_instance:
        test_crew_kickoff()

    print("\n" + "=" * 60)
    print("LINKEDIN CREW TEST COMPLETE")
    print("=" * 60)
