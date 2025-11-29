#!/usr/bin/env python3
"""
Test script for Supervisor Orchestrator v3.5

Usage:
    python test_supervisor.py "ML observability tool for startups" --target 50
    python test_supervisor.py "CRM software for sales teams" --target 100
"""
import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from supervisor_orchestrator import SupervisorOrchestrator, run_prospecting
from utils.lead_exporter import export_leads_json, export_leads_csv, format_leads_table


def main():
    parser = argparse.ArgumentParser(description="Test Supervisor Orchestrator v3.5")
    parser.add_argument("product", type=str, help="Product description")
    parser.add_argument("--target", type=int, default=50, help="Target number of leads")
    parser.add_argument("--output-dir", type=str, default="test_output", help="Output directory")

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = Path(__file__).parent / args.output_dir
    output_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 70)
    print("SUPERVISOR ORCHESTRATOR TEST v3.5")
    print("=" * 70)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Product: {args.product}")
    print(f"[{timestamp}] Target: {args.target} leads")
    print(f"[{timestamp}] Output: {output_dir}")
    print("=" * 70 + "\n")

    # Run the orchestrator
    result = run_prospecting(
        product_description=args.product,
        target_leads=args.target,
        icp_criteria={
            "titles": ["Founder", "CEO", "CTO", "Head of Product", "VP Engineering"],
            "company_size": "1-500 employees",
            "industries": ["SaaS", "Technology", "AI/ML", "Developer Tools"]
        },
        output_dir=str(output_dir)
    )

    # Export results
    timestamp_file = datetime.now().strftime("%Y%m%d-%H%M%S")

    if result.leads:
        # Export JSON
        json_path = output_dir / f"leads_{timestamp_file}.json"
        export_leads_json(result.leads, str(json_path), metadata={
            "product": args.product,
            "target": args.target,
            "total_found": result.total_leads,
            "hot_leads": result.hot_leads,
            "warm_leads": result.warm_leads,
            "platforms": result.platforms_searched,
            "execution_time": result.execution_time
        })

        # Export CSV
        csv_path = output_dir / f"leads_{timestamp_file}.csv"
        export_leads_csv(result.leads, str(csv_path))

        # Print leads table
        print("\n" + format_leads_table(result.leads))

        print(f"\n[EXPORT] JSON: {json_path}")
        print(f"[EXPORT] CSV: {csv_path}")

    # Save execution trace
    trace_path = output_dir / f"execution_trace_{timestamp_file}.txt"
    with open(trace_path, 'w', encoding='utf-8') as f:
        f.write("SUPERVISOR ORCHESTRATOR EXECUTION TRACE\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Product: {args.product}\n")
        f.write(f"Target: {args.target} leads\n")
        f.write(f"Execution time: {result.execution_time:.1f}s\n\n")
        f.write("-" * 70 + "\n")
        f.write("TRACE:\n")
        f.write("-" * 70 + "\n")
        for line in result.trace:
            f.write(f"{line}\n")
        f.write("\n" + "=" * 70 + "\n")

    print(f"[EXPORT] Trace: {trace_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Total leads: {result.total_leads}")
    print(f"Hot leads (score >= 80): {result.hot_leads}")
    print(f"Warm leads (score 60-79): {result.warm_leads}")
    print(f"Reddit leads: {result.reddit_leads}")
    print(f"TechCrunch leads: {result.techcrunch_leads}")
    print(f"Competitor leads: {result.competitor_leads}")
    print(f"Duplicates removed: {result.duplicates_removed}")
    print(f"Execution time: {result.execution_time:.1f}s")
    print(f"Platforms searched: {result.platforms_searched}")

    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  - {error}")

    print("=" * 70)

    # Return exit code
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
