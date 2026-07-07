import pytest
from httpx import AsyncClient
import time
import asyncio

@pytest.mark.asyncio
async def test_global_rate_limit(async_client: AsyncClient, redis_client):
    """Test the global 100 req/min rate limit in main.py."""
    
    # First, let's clear the rate limit keys
    current_bucket = int(time.time()) // 60
    await redis_client.delete(f"argus:global_rl:127.0.0.1:{current_bucket}")
    
    # Send 100 requests (should succeed)
    # Using small batches to not overwhelm the test client, but we need to hit 100
    for _ in range(10):
        tasks = []
        for _ in range(10):
            tasks.append(async_client.get("/health/live"))
        responses = await asyncio.gather(*tasks)
        for resp in responses:
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            
    # The 101st request should be rate limited
    resp = await async_client.get("/health/live")
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many requests. Please slow down."
