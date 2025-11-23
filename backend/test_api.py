"""Test FastAPI endpoints with SSE streaming."""
import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("\n" + "=" * 70)
    print("Testing /health endpoint")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_start_prospecting():
    """Test starting a prospecting job."""
    print("\n" + "=" * 70)
    print("Testing POST /api/v1/prospect/start")
    print("=" * 70)

    payload = {
        "query": "companies complaining about CRM",
        "max_leads": 10
    }

    response = requests.post(f"{API_BASE}/api/v1/prospect/start", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Job ID: {data['job_id']}")
        print(f"Stream URL: {data['stream_url']}")
        return data['job_id']
    else:
        print(f"Error: {response.text}")
        return None

def test_sse_stream(job_id):
    """Test SSE stream for a job."""
    print("\n" + "=" * 70)
    print(f"Testing GET /api/v1/prospect/{job_id}/stream (SSE)")
    print("=" * 70)

    try:
        response = requests.get(
            f"{API_BASE}/api/v1/prospect/{job_id}/stream",
            stream=True,
            headers={"Accept": "text/event-stream"}
        )

        print(f"Status: {response.status_code}")
        print("\nStreaming events (Ctrl+C to stop):")
        print("-" * 70)

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(decoded_line)

                # Stop after completion or error event
                if 'event: completed' in decoded_line or 'event: error' in decoded_line:
                    print("\n[INFO] Received terminal event, stopping stream")
                    break

    except KeyboardInterrupt:
        print("\n\n[INFO] Stream interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Stream failed: {e}")

def test_job_status(job_id):
    """Test job status endpoint."""
    print("\n" + "=" * 70)
    print(f"Testing GET /api/v1/prospect/{job_id}/status")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/api/v1/prospect/{job_id}/status")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Job Status: {data['status']}")
        print(f"Query: {data['query']}")
        print(f"Max Leads: {data['max_leads']}")
        print(f"Created At: {data['created_at']}")
        if data.get('error'):
            print(f"Error: {data['error']}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("FASTAPI PROSPECTING API - TEST SUITE")
    print("=" * 70)
    print("\nMake sure FastAPI server is running:")
    print("  cd backend && python -m app.main")
    print("\nPress Enter to start tests...")
    input()

    # Test 1: Health check
    if not test_health():
        print("\n[ERROR] Health check failed. Is the server running?")
        sys.exit(1)

    # Test 2: Start prospecting
    job_id = test_start_prospecting()
    if not job_id:
        print("\n[ERROR] Failed to start prospecting job")
        sys.exit(1)

    # Test 3: Check initial status
    test_job_status(job_id)

    # Test 4: Stream SSE events
    test_sse_stream(job_id)

    # Test 5: Check final status
    test_job_status(job_id)

    print("\n" + "=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)
