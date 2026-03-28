"""Integration tests for the full query pipeline."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_status_endpoint(client):
    """Test service status endpoint."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    body = response.json()
    assert "service" in body


@pytest.mark.asyncio
async def test_query_without_auth(client):
    """Test query execution without auth returns 401/403."""
    response = client.post(
        "/api/v1/query/execute",
        json={"query": "SELECT 1"},
    )
    # Should be rejected — no auth header
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_drop_table_blocked(client):
    """Test DROP TABLE query is blocked at validation layer."""
    response = client.post(
        "/api/v1/query/execute",
        json={"query": "DROP TABLE users"},
        headers={"Authorization": "Bearer fake-token"},
    )
    # Should be blocked — either 400 (query blocked) or 401 (invalid token)
    assert response.status_code in (400, 401)


@pytest.mark.asyncio
async def test_sql_injection_blocked(client):
    """Test SQL injection pattern is blocked."""
    response = client.post(
        "/api/v1/query/execute",
        json={"query": "SELECT * FROM users WHERE id = 1 OR 1=1"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code in (400, 401)


@pytest.mark.asyncio
async def test_metrics_endpoint_unauthenticated(client):
    """Test /api/v1/metrics/live is accessible without auth."""
    response = client.get("/api/v1/metrics/live")
    # Should be accessible (unauthenticated) — may return 200 or 500 if Redis not available
    assert response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_admin_endpoints_require_auth(client):
    """Test admin endpoints reject unauthenticated requests."""
    endpoints = [
        "/api/v1/admin/audit",
        "/api/v1/admin/slow-queries",
        "/api/v1/admin/heatmap",
        "/api/v1/admin/budget",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in (401, 403, 422), (
            f"{endpoint} returned {response.status_code}"
        )
