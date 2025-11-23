"""Test ProspectingFlow with simple query."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

from dotenv import load_dotenv
load_dotenv()

import asyncio
from flows.prospecting_flow import ProspectingFlow, ProspectingState

print("\n" + "=" * 70)
print("PROSPECTING FLOW TEST")
print("=" * 70)

# Event callback for real-time updates
def event_handler(event):
    event_type = event.get("type")
    data = event.get("data")

    if event_type == "thought":
        print(f"[THOUGHT] {data}")
    elif event_type == "tool":
        print(f"[TOOL] {data}")
    elif event_type == "lead_found":
        print(f"[LEAD] {data}")
    elif event_type == "error":
        print(f"[ERROR] {data}")
    else:
        print(f"[{event_type.upper()}] {data}")

# Initialize flow
print("\n[INFO] Creating ProspectingFlow...")
flow = ProspectingFlow(event_callback=event_handler)

# Set initial state
initial_state = ProspectingState(
    query="companies complaining about CRM",
    max_leads=20  # Start small for testing
)

print(f"\n[INFO] Starting prospecting for: '{initial_state.query}'")
print(f"[INFO] Target: {initial_state.max_leads} leads\n")

try:
    # Run the flow
    print("=" * 70)
    print("AGENT ACTIVITY (Real-time)")
    print("=" * 70 + "\n")

    final_state = flow.kickoff(inputs={"query": initial_state.query, "max_leads": initial_state.max_leads})

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    # Access state attributes directly (not as dict)
    print(f"\nStatus: {getattr(final_state, 'status', 'unknown')}")
    print(f"Leads found: {len(getattr(final_state, 'leads', []))}")

    if hasattr(final_state, 'leads') and final_state.leads:
        # Save results
        import json
        # Convert state to dict for JSON serialization
        state_dict = final_state.model_dump() if hasattr(final_state, 'model_dump') else dict(final_state)
        with open("prospecting_flow_results.json", "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False, default=str)
        print("\n[OK] Results saved to prospecting_flow_results.json")

    if hasattr(final_state, 'error') and final_state.error:
        print(f"\n[ERROR] {final_state.error}")

except Exception as e:
    print(f"\n[ERROR] Flow failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
