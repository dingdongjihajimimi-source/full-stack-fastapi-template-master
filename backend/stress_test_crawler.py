import asyncio
import httpx
import time
import json
import random

# Configuration
API_URL = "http://localhost:8000/api/v1/crawl"
# We need to login first to get a token, but for this stress test script, 
# assuming we can bypass or use a static token if possible.
# Or better, we can invoke the worker function directly? 
# No, "interface" means API. We should test via HTTP.
# We need a valid token. Let's assume we can get one via the login endpoint.

LOGIN_URL = "http://localhost:8000/api/v1/login/access-token"
USERNAME = "admin@example.com"
PASSWORD = "changethis"

CONCURRENCY_TEST = 10  # Number of concurrent tasks
PAGES_PER_TASK = 5
CONCURRENCY_PER_TASK = 5

async def get_access_token():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                LOGIN_URL, 
                data={"username": USERNAME, "password": PASSWORD}
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
        except Exception as e:
            print(f"Login failed: {e}")
            return None

async def poll_task_status(client, task_id, token):
    """Poll task status until completed or failed."""
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()
    while True:
        try:
            resp = await client.get(f"{API_URL}/{task_id}", headers=headers)
            if resp.status_code == 404:
                return "not_found"
            
            data = resp.json()
            status = data["status"]
            
            if status in ["completed", "failed"]:
                duration = time.time() - start_time
                return status, duration
            
            # Print progress for debugging occasionally
            # print(f"Task {task_id}: {status}")
            
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Polling error: {e}")
            return "error", 0

async def run_single_task(client, token, task_idx):
    """Start and monitor a single crawl task."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "url": f"https://example.com/products?task={task_idx}", # Use simulated URL
        "table_name": f"products_stress_{task_idx}",
        "columns": ["title", "price", "description"],
        "max_pages": PAGES_PER_TASK,
        "concurrency": CONCURRENCY_PER_TASK
    }
    
    try:
        start_req_time = time.time()
        resp = await client.post(f"{API_URL}/start", json=payload, headers=headers)
        resp.raise_for_status()
        task_id = resp.json()
        req_latency = time.time() - start_req_time
        
        print(f"Task {task_idx} started (ID: {task_id}) - Latency: {req_latency:.2f}s")
        
        status, duration = await poll_task_status(client, task_id, token)
        return {
            "task_idx": task_idx,
            "task_id": task_id,
            "status": status,
            "duration": duration,
            "req_latency": req_latency
        }
    except Exception as e:
        print(f"Task {task_idx} failed to start: {e}")
        return None

async def main():
    print(f"--- Starting Stress Test (Concurrent Tasks: {CONCURRENCY_TEST}) ---")
    
    token = await get_access_token()
    if not token:
        print("Aborting: Could not get access token.")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        start_time = time.time()
        
        # Launch all tasks concurrently
        tasks = [run_single_task(client, token, i) for i in range(CONCURRENCY_TEST)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        completed = sum(1 for r in results if r and r["status"] == "completed")
        failed = sum(1 for r in results if r and r["status"] == "failed")
        avg_duration = sum(r["duration"] for r in results if r) / len(results) if results else 0
        
        print("\n--- Stress Test Results ---")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Tasks Completed: {completed}/{CONCURRENCY_TEST}")
        print(f"Tasks Failed: {failed}/{CONCURRENCY_TEST}")
        print(f"Avg Task Duration: {avg_duration:.2f}s")
        
        # Check generated files
        # We are running inside/outside container? Assuming we can check via ls or docker exec
        # Here we just print instruction
        print("\nVerification Tip: Check 'backend/generated_data' for created files.")

if __name__ == "__main__":
    asyncio.run(main())
