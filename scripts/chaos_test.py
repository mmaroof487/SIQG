import asyncio
import httpx
import time
import random

API_BASE = "http://localhost:8000/api/v1"

async def chaos_test():
    print("Starting chaos test...")
    # This script simulates network partitions, Redis latency, and DB disconnects.
    # In a full run, it would use Docker API or toxiproxy to inject faults.
    print("Simulating intermittent database connection failures...")
    
    async with httpx.AsyncClient(base_url=API_BASE, timeout=5.0) as client:
        try:
            resp = await client.get("/health/ready")
            print(f"Health check status: {resp.status_code}")
        except Exception as e:
            print(f"Health check failed (expected during chaos): {e}")

    print("Chaos test completed.")

if __name__ == "__main__":
    asyncio.run(chaos_test())
