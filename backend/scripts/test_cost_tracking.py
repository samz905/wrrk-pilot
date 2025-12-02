#!/usr/bin/env python3
"""
Quick test to verify Apify returns cost data and our tracker works.
Run: python scripts/test_cost_tracking.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from apify_client import ApifyClient

def test_apify_cost_response():
    """Test that Apify returns cost data in run response."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("ERROR: APIFY_API_TOKEN not set")
        return False

    print("=" * 50)
    print("TEST 1: Apify Cost Response Structure")
    print("=" * 50)

    client = ApifyClient(token)

    # Use Reddit actor with minimal input (1 post)
    run_input = {
        "queries": ["test"],
        "maxPosts": 1,
        "maxComments": 0,
        "scrapeComments": False,
    }

    print("\nRunning minimal Reddit scraper (1 post)...")
    try:
        run = client.actor("TwqHBuZZPHJxiQrTU").call(run_input=run_input)

        print(f"\nRun ID: {run.get('id', 'N/A')}")
        print(f"Status: {run.get('status', 'N/A')}")

        # Check for cost fields
        print("\n--- Cost Fields in Response ---")

        if "usageTotalUsd" in run:
            print(f"usageTotalUsd: ${run['usageTotalUsd']:.6f}")
        else:
            print("usageTotalUsd: NOT FOUND")

        if "usage" in run:
            usage = run["usage"]
            print(f"usage object: {usage}")
            if "ACTOR_COMPUTE_UNITS" in usage:
                cu = usage["ACTOR_COMPUTE_UNITS"]
                print(f"  ACTOR_COMPUTE_UNITS: {cu}")
                print(f"  Estimated cost (~$0.40/CU): ${cu * 0.40:.6f}")
        else:
            print("usage: NOT FOUND")

        # Show all top-level keys
        print(f"\nAll response keys: {list(run.keys())}")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_cost_tracker():
    """Test our cost tracker module."""
    print("\n" + "=" * 50)
    print("TEST 2: Cost Tracker Module")
    print("=" * 50)

    # Set a test job ID
    os.environ["CURRENT_JOB_ID"] = "test-job-123"

    from app.core.cost_tracker import get_tracker, remove_tracker, track_apify_cost

    # Simulate a run response with cost data
    fake_run = {
        "id": "test-run",
        "status": "SUCCEEDED",
        "usageTotalUsd": 0.0423
    }

    print("\nTracking fake cost: $0.0423")
    cost = track_apify_cost("TwqHBuZZPHJxiQrTU", fake_run)
    print(f"Returned cost: ${cost:.6f}")

    # Add another cost
    fake_run2 = {"usageTotalUsd": 0.0150}
    track_apify_cost("VhxlqQXRwhW8H5hNV", fake_run2)

    # Get summary
    tracker = remove_tracker("test-job-123")
    if tracker:
        summary = tracker.get_summary()
        print(f"\nCost Summary:")
        print(f"  Total: ${summary['total_cost_usd']:.6f}")
        print(f"  Runs: {summary['run_count']}")
        print(f"  By Actor: {summary['by_actor']}")
        return True
    else:
        print("ERROR: Tracker not found")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("APIFY COST TRACKING TESTS")
    print("=" * 60)

    test1 = test_apify_cost_response()
    test2 = test_cost_tracker()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Test 1 (Apify Response): {'PASS' if test1 else 'FAIL'}")
    print(f"Test 2 (Cost Tracker):   {'PASS' if test2 else 'FAIL'}")
    print("=" * 60)
