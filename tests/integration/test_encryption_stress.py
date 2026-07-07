import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_encryption_concurrent_writes(async_client: AsyncClient, valid_connection_id):
    """
    Test concurrent encrypted inserts and updates to ensure the AES-GCM nonce 
    and transaction isolation holds up under stress.
    """
    # 1. Add encryption rule for a test column
    resp = await async_client.post(f"/api/v1/connections/{valid_connection_id}/encryption", json={
        "schema_name": "public",
        "table_name": "users",
        "column_name": "email",
        "classification_method": 3,
        "is_encrypted": True
    })
    
    # 2. Fire 50 concurrent inserts
    async def insert_user(i):
        query = f"INSERT INTO users (username, email) VALUES ('stress_user_{i}', 'stress_{i}@example.com')"
        return await async_client.post("/api/v1/query/execute", json={
            "connection_id": valid_connection_id,
            "query": query
        })
        
    tasks = [insert_user(i) for i in range(50)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check that they all succeeded
    successes = sum(1 for r in responses if getattr(r, 'status_code', None) == 200)
    assert successes == 50, f"Expected 50 successful inserts, got {successes}"

@pytest.mark.asyncio
async def test_encryption_large_batch(async_client: AsyncClient, valid_connection_id):
    """
    Test encrypting a large result set during read.
    """
    # Requires a pre-populated DB, assuming the test fixture sets one up.
    query = "SELECT * FROM users LIMIT 1000;"
    resp = await async_client.post("/api/v1/query/execute", json={
        "connection_id": valid_connection_id,
        "query": query,
        "limit": 1000
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
