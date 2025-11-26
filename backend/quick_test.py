"""Quick test of the prospecting flow v2."""
import asyncio
import os
import sys
import warnings
import logging

# Suppress warnings and verbose logging
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.ERROR)

sys.path.insert(0, 'C:/Users/samZ9/Downloads/Code/wrrk-pilot/backend/app')
os.chdir('C:/Users/samZ9/Downloads/Code/wrrk-pilot/backend')

# Create output dir
os.makedirs('./test_output', exist_ok=True)

# Redirect dotenv warnings
import io
old_stderr = sys.stderr
sys.stderr = io.StringIO()

from dotenv import load_dotenv
load_dotenv()

# Restore stderr
sys.stderr = old_stderr

from flows.prospecting_flow_v2 import run_prospecting_v2

async def test():
    output_lines = []

    def log(msg):
        print(msg)
        output_lines.append(msg)

    try:
        log("Starting prospecting flow v2 test...")

        result = await run_prospecting_v2(
            query='AI design tool for startups',
            target_leads=10,
            icp_criteria={'titles': ['Founder', 'CEO', 'CTO']},
            output_dir='./test_output'
        )

        log("\n=== FINAL RESULTS ===")
        log(f"Status: {result.status}")
        log(f"Total leads: {len(result.leads)}")
        log(f"Hot leads: {result.hot_leads}")
        log(f"Warm leads: {result.warm_leads}")
        log(f"Platforms: {result.platforms_searched}")
        log(f"Strategies: {result.strategies_used}")
        log(f"Retries: {result.retries}")

        if result.error:
            log(f"Error: {result.error}")

        # List lead usernames
        if result.leads:
            log("\nLeads found:")
            for i, lead in enumerate(result.leads[:15], 1):
                name = lead.get('username', lead.get('name', 'Unknown'))
                score = lead.get('intent_score', 0)
                platform = lead.get('platform', 'unknown')
                log(f"  {i}. {name} (Score: {score}, Platform: {platform})")
        else:
            log("\nNo leads found!")

        # Save results to file
        with open('./test_output/quick_test_results.txt', 'w') as f:
            f.write('\n'.join(output_lines))

        return result

    except Exception as e:
        import traceback
        error_msg = f"ERROR: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        log(error_msg)

        with open('./test_output/quick_test_results.txt', 'w') as f:
            f.write('\n'.join(output_lines))

        return None

if __name__ == "__main__":
    result = asyncio.run(test())
    if result:
        print(f"\nTest completed with status: {result.status}")
    else:
        print("\nTest failed!")
