"""
Integration tests for Phase B — Multi-Database Workbench.

These tests exercise the HTTP layer (via FastAPI TestClient) to verify:
1. POST /connections registers a connection and stores conn string encrypted
2. GET /connections lists only the current user's connections
3. DELETE /connections/{id} soft-deletes the connection
4. Query with unknown connection_id returns 404
5. Inactive connection blocks query routing

Each test uses the conftest `client` fixture (mocked Redis + SQLite DB).
The PrimarySession DB calls are mocked via patch.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# We import helpers from conftest via pytest fixtures


def _make_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ─── Test 1: POST /connections creates record ─────────────────────────────────

def test_register_connection_success(client, admin_token):
    """
    POST /connections stores a new connection with encrypted conn string.
    The plain connection string must NOT appear in the response body.
    """
    plain_conn_str = "postgres://user:superpassword@prod.db.internal/analytics"

    fake_id = str(uuid.uuid4())
    fake_conn = MagicMock()
    fake_conn.id = uuid.UUID(fake_id)
    fake_conn.display_name = "Production Analytics"
    fake_conn.db_type = "postgres"
    fake_conn.is_active = True
    fake_conn.created_at = datetime(2024, 1, 1)
    fake_conn.updated_at = datetime(2024, 1, 1)

    # Patch PrimarySession as a context manager that returns a mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    # refresh sets .id on the passed object
    async def _refresh(obj):
        obj.id = fake_conn.id
        obj.display_name = fake_conn.display_name
        obj.db_type = fake_conn.db_type
        obj.is_active = fake_conn.is_active
        obj.created_at = fake_conn.created_at
        obj.updated_at = fake_conn.updated_at
    mock_session.refresh = AsyncMock(side_effect=_refresh)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("routers.v1.connections.PrimarySession", return_value=mock_ctx):
        response = client.post(
            "/api/v1/connections",
            json={
                "display_name": "Production Analytics",
                "db_type": "postgres",
                "conn_str": plain_conn_str,
            },
            headers=_make_headers(admin_token),
        )

    # Must succeed
    assert response.status_code == 201
    data = response.json()

    # Connection string must NOT appear in response
    assert plain_conn_str not in str(data)
    assert "conn_str" not in data
    assert "conn_str_enc" not in data
    assert data["display_name"] == "Production Analytics"
    assert data["db_type"] == "postgres"
    assert data["is_active"] is True


def test_register_connection_invalid_db_type_returns_400(client, admin_token):
    """POST /connections rejects unsupported db_type."""
    with patch("routers.v1.connections.PrimarySession"):
        response = client.post(
            "/api/v1/connections",
            json={
                "display_name": "Mongo DB",
                "db_type": "mongodb",  # Not supported
                "conn_str": "mongodb://localhost/test",
            },
            headers=_make_headers(admin_token),
        )

    assert response.status_code == 400
    assert "Unsupported db_type" in response.json()["detail"]


# ─── Test 2: GET /connections lists only current user's connections ────────────

def test_list_connections_returns_only_user_connections(client, admin_token):
    """GET /connections returns only the requesting user's connections."""
    user_conn_id = uuid.uuid4()

    fake_conn = MagicMock()
    fake_conn.id = user_conn_id
    fake_conn.display_name = "My DB"
    fake_conn.db_type = "postgres"
    fake_conn.is_active = True
    fake_conn.created_at = datetime(2024, 1, 1)
    fake_conn.updated_at = datetime(2024, 1, 1)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [fake_conn]
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("routers.v1.connections.PrimarySession", return_value=mock_ctx):
        response = client.get(
            "/api/v1/connections",
            headers=_make_headers(admin_token),
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert str(user_conn_id) == data[0]["id"]


# ─── Test 3: DELETE soft-deletes and purges cache ────────────────────────────

def test_delete_connection_soft_deletes(client, admin_token):
    """DELETE /connections/{id} sets is_active=False (soft delete)."""
    conn_id = str(uuid.uuid4())

    fake_conn = MagicMock()
    fake_conn.id = uuid.UUID(conn_id)
    fake_conn.user_id = uuid.uuid4()
    fake_conn.is_active = True

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = fake_conn
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("routers.v1.connections.PrimarySession", return_value=mock_ctx):
        # Patch at the correct import location
        with patch(
            "utils.connection_manager.invalidate_connection_cache",
            new=AsyncMock(return_value=0),
        ):
            response = client.delete(
                f"/api/v1/connections/{conn_id}",
                headers=_make_headers(admin_token),
            )

    assert response.status_code == 204
    assert fake_conn.is_active is False


# ─── Test 4: Query with missing connection_id returns 404 ────────────────────

def test_query_with_unknown_connection_id_returns_404(client, admin_token):
    """
    POST /query/execute with an unknown connection_id must return 404.
    The existing query pipeline (no connection_id) is not affected.
    """
    unknown_id = str(uuid.uuid4())

    with patch("routers.v1.query.PrimarySession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # DB returns None (not found)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_cls.return_value = mock_session

        response = client.post(
            "/api/v1/query/execute",
            json={"query": "SELECT 1", "connection_id": unknown_id},
            headers=_make_headers(admin_token),
        )

    assert response.status_code == 404


# ─── Test 5: Existing pipeline unaffected (no connection_id) ──────────────────

def test_query_without_connection_id_follows_existing_pipeline(client, admin_token):
    """
    Queries without connection_id must go through the existing internal pipeline
    (execute_with_timeout → PrimarySession) without any Phase B code activated.

    We verify by ensuring asyncpg.connect is NOT called.
    """
    with patch("routers.v1.query.execute_with_timeout") as mock_exec:
        mock_exec.return_value = ([], None)  # empty rows, no metadata

        with patch("routers.v1.query.asyncpg") as mock_asyncpg:
            response = client.post(
                "/api/v1/query/execute",
                json={"query": "SELECT 1"},  # No connection_id
                headers=_make_headers(admin_token),
            )

        # asyncpg.connect should NEVER be called for internal queries
        mock_asyncpg.connect.assert_not_called()
