import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# Set job ID for tracking
os.environ["CURRENT_JOB_ID"] = "test-job-123"

from apify_client import ApifyClient
from app.core.cost_tracker import track_apify_cost, remove_tracker

token = os.getenv('APIFY_API_TOKEN')
client = ApifyClient(token)

print('Running Reddit actor (minimal)...')
run = client.actor('TwqHBuZZPHJxiQrTU').call(run_input={
    'queries': ['test'],
    'maxPosts': 10,
    'maxComments': 1
})

print(f'\nStatus: {run.get("status")}')
print(f'stats.computeUnits: {run.get("stats", {}).get("computeUnits", "N/A")}')

# Track the cost
cost = track_apify_cost('TwqHBuZZPHJxiQrTU', run)
print(f'\nTracked cost: ${cost:.6f}')

# Get final summary
tracker = remove_tracker("test-job-123")
if tracker:
    print(f'Total tracked: ${tracker.total_cost_usd:.6f}')
    print('\nSUCCESS - Cost tracking works!')
