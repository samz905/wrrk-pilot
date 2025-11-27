"""
Orchestrator Test Script

Usage:
  python test_orchestrator.py
  python test_orchestrator.py "find me 30 leads for my CRM tool" --target 30

Output:
  test_output/execution_steps.txt  - Execution log
  test_output/leads.csv            - Final leads
"""

import argparse
import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "app"))
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Test the orchestrator agent")
    parser.add_argument(
        "query",
        nargs="?",
        default="project management software for startups",
        help="Product/query description"
    )
    parser.add_argument(
        "--target", "-t",
        type=int,
        default=20,
        help="Target number of leads (default: 20)"
    )
    return parser.parse_args()


class ExecutionLogger:
    """Real-time execution logger that writes to file as steps happen."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.file = open(output_path, "w", encoding="utf-8")
        self._write_header()

    def _write_header(self):
        self.file.write("ORCHESTRATOR EXECUTION LOG\n")
        self.file.write(f"Generated: {datetime.now().isoformat()}\n")
        self.file.write("=" * 70 + "\n\n")
        self.file.flush()

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        self.file.write(entry)
        self.file.flush()
        print(entry.strip())

    def close(self):
        self.file.close()


def export_leads_csv(leads: list, output_path: Path):
    """Export leads to CSV with fixed filename."""
    fieldnames = [
        "name", "title", "company", "intent_signal",
        "intent_score", "source_platform", "source_url",
        "priority", "scoring_reasoning"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead)


async def run_test(query: str, target_leads: int):
    """Run the orchestrator test."""
    from flows.prospecting_flow_v2 import run_prospecting_v2

    # Setup output directory
    output_dir = Path(__file__).parent / "test_output"
    output_dir.mkdir(exist_ok=True)

    # Initialize real-time logger
    logger = ExecutionLogger(output_dir / "execution_steps.txt")

    logger.log(f"Query: {query}")
    logger.log(f"Target: {target_leads} leads")
    logger.log("-" * 50)

    # Event handler captures execution steps in real-time
    def event_handler(event):
        event_type = event.get("type", "unknown")
        data = event.get("data", "")

        if event_type == "thought":
            logger.log(f"[THOUGHT] {data}")
        elif event_type == "agent_started":
            logger.log(f"[AGENT] Started: {data}")
        elif event_type == "agent_completed":
            logger.log(f"[AGENT] Completed: {data}")
        elif event_type == "error":
            logger.log(f"[ERROR] {data}")
        elif event_type == "completed":
            logger.log(f"[COMPLETED] Leads found: {data}")
        else:
            logger.log(f"[{event_type.upper()}] {data}")

    icp_criteria = {
        "titles": ["Founder", "CEO", "CTO", "Head of Product", "VP Engineering"],
        "company_size": "1-500 employees",
        "industries": ["SaaS", "Technology", "AI/ML", "Developer Tools"],
    }

    logger.log("Starting orchestrator...")
    logger.log("=" * 50)

    try:
        result = await run_prospecting_v2(
            query=query,
            target_leads=target_leads,
            icp_criteria=icp_criteria,
            event_callback=event_handler,
            output_dir=str(output_dir)
        )

        logger.log("=" * 50)
        logger.log("FINAL RESULTS:")
        logger.log(f"  Status: {result.status}")
        logger.log(f"  Total leads: {len(result.leads)}")
        logger.log(f"  Hot leads: {result.hot_leads}")
        logger.log(f"  Warm leads: {result.warm_leads}")
        logger.log(f"  Strategies: {result.strategies_used}")

        # Export to fixed filename CSV
        csv_path = output_dir / "leads.csv"
        export_leads_csv(result.leads, csv_path)
        logger.log(f"  CSV: {csv_path}")

        logger.close()

        print(f"\n{'=' * 70}")
        print("OUTPUT FILES:")
        print(f"  Execution log: {output_dir / 'execution_steps.txt'}")
        print(f"  Leads CSV:     {csv_path}")
        print(f"{'=' * 70}")

        return result

    except Exception as e:
        logger.log(f"[FATAL] {type(e).__name__}: {str(e)}")
        logger.close()
        raise


def main():
    args = parse_args()

    print("\n" + "=" * 70)
    print("ORCHESTRATOR TEST")
    print("=" * 70)

    if not os.getenv("OPENAI_API_KEY") or not os.getenv("APIFY_API_TOKEN"):
        print("[ERROR] Missing OPENAI_API_KEY or APIFY_API_TOKEN in .env")
        sys.exit(1)

    result = asyncio.run(run_test(args.query, args.target))

    if result and result.status in ("completed", "partial"):
        print("\n[SUCCESS] Test completed")
        sys.exit(0)
    else:
        print("\n[FAILED] Test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
