import asyncio
import httpx
import time

API_BASE = "http://localhost:8000/api/v1"

async def load_test():
    print("Starting load test...")
    
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        # Fire requests rapidly to test FastAPI/Uvicorn throughput
        print("Pounding /health/live endpoint...")
        start_time = time.time()
        tasks = [client.get("/health/live") for _ in range(500)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        success = sum(1 for r in responses if getattr(r, 'status_code', None) == 200)
        print(f"Load test results: {success}/500 requests succeeded in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(load_test())
