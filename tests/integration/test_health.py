import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_live(async_client: AsyncClient):
    """
    Test the liveness probe endpoint.
    Should always return 200 OK.
    """
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"

@pytest.mark.asyncio
async def test_health_ready(async_client: AsyncClient):
    """
    Test the readiness probe endpoint.
    Should return 200 OK when DB and Redis are connected.
    """
    response = await async_client.get("/health/ready")
    # Assuming the test fixture correctly sets up dependencies
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "db" in data["components"]
    assert "redis" in data["components"]
    assert data["components"]["db"] == "ok"
    assert data["components"]["redis"] == "ok"
