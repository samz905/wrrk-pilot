#!/usr/bin/env python3
"""
Check Apify usage costs for recent prospecting runs.
Run from backend directory: python scripts/check_apify_costs.py
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from apify_client import ApifyClient


def get_recent_runs(client: ApifyClient, limit: int = 50) -> list:
    """Get recent actor runs from the account."""
    runs = []

    # Get runs from the last 7 days
    try:
        runs_list = client.runs().list(limit=limit, desc=True)
        for run in runs_list.items:
            runs.append(run)
    except Exception as e:
        print(f"Error fetching runs: {e}")

    return runs


def analyze_costs(runs: list) -> dict:
    """Analyze costs from runs."""

    # Actor ID to friendly name mapping
    actor_names = {
        "TwqHBuZZPHJxiQrTU": "Reddit Scraper",
        "VhxlqQXRwhW8H5hNV": "LinkedIn Profile Detail",
        "cIdqlEvw6afc1do1p": "LinkedIn Employees",
        "apimaestro/linkedin-companies-search-scraper": "LinkedIn Company Search",
        "apimaestro/linkedin-post-comments-replies-engagements-scraper-no-cookies": "LinkedIn Post Comments",
        "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest": "Twitter Scraper",
        "harvestapi/linkedin-company-posts": "LinkedIn Company Posts",
        "curious_coder/crunchbase-scraper": "Crunchbase Scraper",
        "563JCPLOqM1kMmbbP": "Google SERP",
        "5QnEH5N71IK2mFLrP": "LinkedIn Posts",
    }

    # Group runs by approximate session (within 10 minutes)
    sessions = []
    current_session = {"runs": [], "start": None, "end": None}

    for run in sorted(runs, key=lambda x: x.get("startedAt", ""), reverse=True):
        started_at = run.get("startedAt")
        if not started_at:
            continue

        if isinstance(started_at, str):
            try:
                run_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except:
                continue
        else:
            run_time = started_at

        # Check if this run belongs to current session (within 10 min of last run)
        if current_session["runs"] and current_session["end"]:
            time_diff = abs((run_time - current_session["end"]).total_seconds())
            if time_diff > 600:  # More than 10 minutes apart
                if current_session["runs"]:
                    sessions.append(current_session)
                current_session = {"runs": [], "start": None, "end": None}

        current_session["runs"].append(run)
        if current_session["start"] is None or run_time < current_session["start"]:
            current_session["start"] = run_time
        if current_session["end"] is None or run_time > current_session["end"]:
            current_session["end"] = run_time

    if current_session["runs"]:
        sessions.append(current_session)

    # Analyze each session
    analysis = {
        "total_runs": len(runs),
        "sessions": [],
        "by_actor": {},
        "total_cost_usd": 0,
    }

    for session in sessions[:5]:  # Last 5 sessions
        session_data = {
            "start": session["start"].isoformat() if session["start"] else "N/A",
            "run_count": len(session["runs"]),
            "actors_used": [],
            "total_cost_usd": 0,
            "compute_units": 0,
        }

        for run in session["runs"]:
            actor_id = run.get("actId", "unknown")
            actor_name = actor_names.get(actor_id, actor_id)

            # Get usage stats
            usage = run.get("usage", {})
            cost_usd = usage.get("ACTOR_COMPUTE_UNITS", 0) * 0.40  # ~$0.40 per compute unit

            # Also check usageTotalUsd if available
            if "usageTotalUsd" in run:
                cost_usd = run["usageTotalUsd"]

            session_data["actors_used"].append({
                "actor": actor_name,
                "status": run.get("status", "unknown"),
                "cost_usd": cost_usd,
            })
            session_data["total_cost_usd"] += cost_usd

            # Track by actor
            if actor_name not in analysis["by_actor"]:
                analysis["by_actor"][actor_name] = {"runs": 0, "total_cost": 0}
            analysis["by_actor"][actor_name]["runs"] += 1
            analysis["by_actor"][actor_name]["total_cost"] += cost_usd

        analysis["sessions"].append(session_data)
        analysis["total_cost_usd"] += session_data["total_cost_usd"]

    return analysis


def main():
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("Error: APIFY_API_TOKEN not found in environment")
        print("Make sure you have a .env file with APIFY_API_TOKEN set")
        return

    print("=" * 60)
    print("APIFY USAGE COST ANALYSIS")
    print("=" * 60)

    client = ApifyClient(token)

    # Get account info
    try:
        user = client.user().get()
        print(f"\nAccount: {user.get('username', 'N/A')}")
        print(f"Plan: {user.get('plan', {}).get('id', 'N/A')}")

        # Get usage limits
        limits = user.get("limits", {})
        usage = user.get("usage", {})

        monthly_usage = usage.get("monthlyUsage", {})
        if monthly_usage:
            print(f"\nMonthly Usage:")
            print(f"  Compute Units: {monthly_usage.get('ACTOR_COMPUTE_UNITS', 0):.2f}")
            print(f"  Dataset Reads: {monthly_usage.get('DATASET_READS', 0)}")
            print(f"  Dataset Writes: {monthly_usage.get('DATASET_WRITES', 0)}")
    except Exception as e:
        print(f"Could not fetch account info: {e}")

    print("\n" + "-" * 60)
    print("RECENT RUNS")
    print("-" * 60)

    runs = get_recent_runs(client, limit=50)

    if not runs:
        print("No recent runs found")
        return

    analysis = analyze_costs(runs)

    print(f"\nTotal runs analyzed: {analysis['total_runs']}")
    print(f"Prospecting sessions found: {len(analysis['sessions'])}")

    # Show last 2 sessions in detail
    print("\n" + "=" * 60)
    print("LAST 2 PROSPECTING SESSIONS")
    print("=" * 60)

    for i, session in enumerate(analysis["sessions"][:2], 1):
        print(f"\n--- Session {i} ({session['start']}) ---")
        print(f"Runs in session: {session['run_count']}")

        # Group by actor for cleaner output
        actor_summary = {}
        for actor_run in session["actors_used"]:
            name = actor_run["actor"]
            if name not in actor_summary:
                actor_summary[name] = {"count": 0, "cost": 0}
            actor_summary[name]["count"] += 1
            actor_summary[name]["cost"] += actor_run["cost_usd"]

        print("\nActors used:")
        for actor, data in sorted(actor_summary.items(), key=lambda x: -x[1]["cost"]):
            print(f"  - {actor}: {data['count']}x runs, ${data['cost']:.4f}")

        print(f"\nSession Total: ${session['total_cost_usd']:.4f}")

    # Overall summary
    print("\n" + "=" * 60)
    print("COST SUMMARY BY ACTOR (all runs)")
    print("=" * 60)

    for actor, data in sorted(analysis["by_actor"].items(), key=lambda x: -x[1]["total_cost"]):
        avg_cost = data["total_cost"] / data["runs"] if data["runs"] > 0 else 0
        print(f"  {actor}:")
        print(f"    Runs: {data['runs']}, Total: ${data['total_cost']:.4f}, Avg: ${avg_cost:.4f}/run")

    print("\n" + "=" * 60)
    if analysis["sessions"]:
        avg_per_session = sum(s["total_cost_usd"] for s in analysis["sessions"]) / len(analysis["sessions"])
        print(f"AVERAGE COST PER PROSPECTING RUN: ${avg_per_session:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
