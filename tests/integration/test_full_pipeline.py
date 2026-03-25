"""Integration tests for the full query pipeline."""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_select_query_flow(client):
    """Test full SELECT query flow."""
    # This will be tested with a real DB once Docker setup works
    pass


@pytest.mark.asyncio
async def test_drop_table_blocked(client):
    """Test DROP TABLE query is blocked."""
    pass
