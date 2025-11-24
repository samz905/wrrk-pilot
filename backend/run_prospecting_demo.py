"""
Run full prospecting pipeline for demo.

Query: "find me leads for my project management software"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from flows.prospecting_flow import ProspectingFlow, ProspectingState


def main():
    print("=" * 80)
    print("PROSPECTING DEMO: Project Management Software Leads")
    print("=" * 80)
    print()
    print("Query: find me leads for my project management software")
    print("Pipeline: Reddit > LinkedIn > Twitter > Google > Aggregation > Qualification")
    print()
    print("=" * 80)
    print()

    # Event callback to show progress
    def event_callback(event):
        event_type = event.get("type", "")
        data = event.get("data", "")

        if event_type == "thought":
            print(f"[THOUGHT] {data}")
        elif event_type == "crew_started":
            print(f"\n{'='*60}")
            print(f"[CREW STARTED] {data}")
            print(f"{'='*60}")
        elif event_type == "crew_completed":
            print(f"[CREW COMPLETED] {data}\n")
        elif event_type == "error":
            print(f"[ERROR] {data}")

    # Create and run flow
    flow = ProspectingFlow(event_callback=event_callback)

    try:
        result = flow.kickoff(inputs={
            "query": "find me leads for my project management software",
            "max_leads": 10
        })

        print("\n" + "=" * 80)
        print("PROSPECTING COMPLETE!")
        print("=" * 80)
        print()

        # Extract qualified leads
        if hasattr(result, 'leads') and result.leads:
            qualified_output = result.leads[0].get("qualified_leads", "")

            print("=" * 80)
            print("TOP 10 QUALIFIED LEADS")
            print("=" * 80)
            print()
            print(qualified_output)
            print()

            # Also save to file
            with open("prospecting_demo_results.txt", "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("PROSPECTING DEMO RESULTS\n")
                f.write("=" * 80 + "\n\n")
                f.write("Query: find me leads for my project management software\n")
                f.write("Pipeline: Reddit > LinkedIn > Twitter > Google > Aggregation > Qualification\n\n")
                f.write("=" * 80 + "\n")
                f.write("TOP 10 QUALIFIED LEADS\n")
                f.write("=" * 80 + "\n\n")
                f.write(qualified_output)

            print("Results saved to: prospecting_demo_results.txt")

        else:
            print("No results generated")

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
