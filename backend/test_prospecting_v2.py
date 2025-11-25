"""
Test script for ProspectingFlow v2 with full logging and lead export.

This script tests the updated prospecting flow with:
- Commenter classification (problem relaters vs solution givers)
- New Twitter Apify actor
- AgentLogger for full execution trace
- LeadExporter for JSON/CSV output
- Target: 50-100 qualified leads
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Load environment variables
load_dotenv()


def check_api_keys():
    """Verify all required API keys are present."""
    keys = {
        "APIFY_API_TOKEN": os.getenv("APIFY_API_TOKEN"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }

    missing = [k for k, v in keys.items() if not v]
    if missing:
        print(f"[ERROR] Missing API keys: {missing}")
        return False

    print("[OK] All API keys present")
    return True


async def run_test():
    """Run the prospecting test with full logging."""

    # Import here to avoid import errors before path setup
    from flows.prospecting_flow_v2 import run_prospecting_v2, ProspectingStatus

    print("\n" + "="*70)
    print("PROSPECTING FLOW V2 - FULL TEST")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print("="*70)

    # Test configuration
    product_description = """
    AI design agent that helps startups and SaaS companies ship UI faster.

    Our tool automates design workflows, generates UI components, and helps
    non-designers create professional-looking interfaces. We're looking for
    founders, product managers, and developers who are frustrated with design
    bottlenecks or struggling to find good designers.
    """

    icp_criteria = {
        "titles": [
            "Founder",
            "CEO",
            "CTO",
            "Head of Product",
            "Product Manager",
            "Lead Developer"
        ],
        "company_size": "1-100 employees",
        "industries": [
            "SaaS",
            "Technology",
            "Startups",
            "Software Development"
        ],
        "signals": [
            "Complaining about design",
            "Looking for designers",
            "Discussing Figma/design tools",
            "Asking for design recommendations",
            "Frustrated with UI/UX",
            "Need faster product iteration"
        ]
    }

    target_leads = 75  # Target 50-100 leads

    print(f"\nProduct: {product_description[:100]}...")
    print(f"\nICP: {icp_criteria}")
    print(f"\nTarget: {target_leads} qualified leads")

    # Create output directory
    output_dir = Path(__file__).parent / "test_output"
    output_dir.mkdir(exist_ok=True)

    print(f"\nOutput directory: {output_dir}")

    # Event handler for real-time updates
    def event_handler(event):
        event_type = event.get('type', 'unknown')
        data = event.get('data', '')

        # Format based on event type
        if event_type == 'thought':
            print(f"\n[THOUGHT] {data}")
        elif event_type == 'agent_started':
            print(f"\n[AGENT] Started: {data}")
        elif event_type == 'agent_completed':
            print(f"\n[AGENT] Completed: {data}")
        elif event_type == 'error':
            print(f"\n[ERROR] {data}")
        elif event_type == 'completed':
            print(f"\n[COMPLETED] {data}")
        else:
            print(f"\n[{event_type.upper()}] {data}")

    print("\n" + "-"*70)
    print("Starting Orchestrator Agent...")
    print("-"*70)

    try:
        # Run the flow
        result = await run_prospecting_v2(
            query=product_description,
            target_leads=target_leads,
            icp_criteria=icp_criteria,
            event_callback=event_handler,
            output_dir=str(output_dir)
        )

        # Print final results
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)
        print(f"Status: {result.status}")
        print(f"Total leads found: {len(result.leads)}")
        print(f"Hot leads (80+): {result.hot_leads}")
        print(f"Warm leads (60-79): {result.warm_leads}")
        print(f"Platforms searched: {result.platforms_searched}")
        print(f"Strategies used: {result.strategies_used}")
        print(f"Retries: {result.retries}")

        if result.error:
            print(f"Error: {result.error}")

        print("\n" + "="*70)
        print("OUTPUT FILES")
        print("="*70)

        # List output files
        for f in output_dir.glob("*"):
            print(f"  - {f.name}")

        print("="*70)

        return result

    except Exception as e:
        print(f"\n[FATAL ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    print("\nChecking prerequisites...")

    if not check_api_keys():
        print("\nPlease set the required environment variables and try again.")
        sys.exit(1)

    # Run the async test
    result = asyncio.run(run_test())

    if result and result.status == "completed":
        print("\n[SUCCESS] Test completed successfully!")
        sys.exit(0)
    elif result and result.status == "partial":
        print("\n[PARTIAL] Test completed with partial results")
        sys.exit(0)
    else:
        print("\n[FAILED] Test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
