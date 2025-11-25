"""
End-to-end test of the Orchestrator Crew with a real scenario.

Scenario: Design Agent for Founders
"Find leads for our AI design agent that helps startups ship UI faster"
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "app"))
sys.path.insert(0, str(Path(__file__).parent / "app" / "tools"))

from crews.orchestrator.crew import OrchestratorCrew, run_prospecting


def test_design_agent_scenario():
    """
    Test Scenario 1: Design Agent for Founders

    Query: "Find leads for our AI design agent that helps startups ship UI faster"

    Expected behavior:
    1. Agent analyzes query - identifies B2B SaaS for startups
    2. Targets: Founders, Head of Product, Design leads
    3. Searches LinkedIn + Reddit for design bottleneck discussions
    4. Finds people frustrated with design workflows
    5. Returns qualified leads with intent scores >= 60
    """
    print("\n" + "=" * 70)
    print("SCENARIO TEST: Design Agent for Founders")
    print("=" * 70)

    product_description = """
    AI design agent that helps startups ship UI faster.

    Our tool automates design workflows, generates UI components,
    and helps small teams ship product without dedicated designers.

    Target customers: Early-stage startups, small SaaS companies,
    founders who struggle with design bottlenecks.
    """

    icp_criteria = {
        "titles": ["Founder", "CEO", "CTO", "Head of Product", "Product Manager"],
        "company_size": "1-50 employees",
        "industries": ["SaaS", "Technology", "Startups"],
        "signals": [
            "Complaining about design",
            "Looking for designers",
            "Discussing Figma/design tools",
            "Asking for design recommendations"
        ]
    }

    print(f"\nProduct: {product_description[:100]}...")
    print(f"\nICP Criteria: {json.dumps(icp_criteria, indent=2)}")
    print(f"\nTarget: 10 qualified leads")
    print("\n" + "-" * 70)
    print("Starting Orchestrator Agent...")
    print("-" * 70)

    try:
        # Initialize and run the orchestrator crew
        crew = OrchestratorCrew()

        result = crew.crew().kickoff(inputs={
            "product_description": product_description,
            "target_leads": 10,
            "icp_criteria": icp_criteria
        })

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)

        # Check if we got structured output
        if hasattr(result, 'pydantic') and result.pydantic:
            output = result.pydantic
            print(f"\nTotal leads found: {output.total_leads}")
            print(f"Hot leads (score >= 80): {output.hot_leads}")
            print(f"Warm leads (score 60-79): {output.warm_leads}")
            print(f"Platforms searched: {output.platforms_searched}")
            print(f"Strategies used: {output.strategies_used}")
            print(f"\nSummary: {output.summary}")

            print("\n" + "-" * 70)
            print("TOP LEADS:")
            print("-" * 70)

            for i, lead in enumerate(output.leads[:10], 1):
                print(f"\n{i}. {lead.name}")
                print(f"   Title: {lead.title}")
                print(f"   Company: {lead.company}")
                print(f"   Intent Score: {lead.intent_score}/100 [{lead.priority.value.upper()}]")
                print(f"   Signal: \"{lead.intent_signal[:100]}...\"" if len(lead.intent_signal) > 100 else f"   Signal: \"{lead.intent_signal}\"")
                print(f"   Source: {lead.source_platform}")
                if lead.linkedin_url:
                    print(f"   LinkedIn: {lead.linkedin_url}")
        else:
            # Raw output
            print("\nRaw output:")
            print(str(result)[:2000])

        print("\n" + "=" * 70)
        print("TEST COMPLETED")
        print("=" * 70)

        return result

    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Check for required API keys
    if not os.getenv("APIFY_API_TOKEN"):
        print("ERROR: APIFY_API_TOKEN not set")
        sys.exit(1)
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    print("\nAPI Keys: OK")
    print("Crunchbase Cookie:", "Set" if os.getenv("CRUNCHBASE_COOKIE") else "Not set")

    # Run the test
    test_design_agent_scenario()
