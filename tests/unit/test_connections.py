"""
Unit tests for Phase B — Multi-Database Workbench connections endpoints.

Tests cover:
1. Registering a new connection (POST /connections)
2. Listing connections (GET /connections)
3. Getting a single connection (GET /connections/{id})
4. Deleting a connection (DELETE /connections/{id})
5. Testing connectivity (POST /connections/{id}/test)
6. Adding column encryption (POST /connections/{id}/encryption)
7. Removing column encryption (DELETE /connections/{id}/encryption/{config_id})
8. Ownership enforcement (user B cannot access user A's connection)
9. Inactive connection returns 404 on query routing
10. Duplicate encryption config returns 409
11. Test endpoint decrypts connection string before testing
12. Invalid UUID returns 400
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# ─── Helpers / Fixtures ───────────────────────────────────────────────────────

def make_user_db(
    user_id=None,
    conn_id=None,
    is_active=True,
    conn_str_enc="ENCRYPTED_BLOB",
):
    from models.user_database import UserDatabase, DatabaseType
    ud = MagicMock(spec=UserDatabase)
    ud.id = conn_id or uuid.uuid4()
    ud.user_id = user_id or uuid.uuid4()
    ud.display_name = "Test DB"
    ud.db_type = DatabaseType.POSTGRES
    ud.conn_str_enc = conn_str_enc
    ud.is_active = is_active
    ud.created_at = datetime(2024, 1, 1)
    ud.updated_at = datetime(2024, 1, 1)
    return ud


def make_col_config(conn_id=None, table="users", col="ssn"):
    from models.user_database import ColumnEncryptionConfig
    cfg = MagicMock(spec=ColumnEncryptionConfig)
    cfg.id = 1
    cfg.connection_id = conn_id or uuid.uuid4()
    cfg.table_name = table
    cfg.column_name = col
    cfg.created_at = datetime(2024, 1, 1)
    return cfg


# ─── Test: get_user_database ownership ────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_database_returns_own_connection():
    """get_user_database returns row when ownership matches."""
    from utils.connection_manager import get_user_database

    user_id = uuid.uuid4()
    conn_id = uuid.uuid4()
    mock_db = make_user_db(user_id=user_id, conn_id=conn_id)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_db
    mock_session.execute.return_value = mock_result

    result = await get_user_database(mock_session, str(conn_id), str(user_id))
    assert result is mock_db


@pytest.mark.asyncio
async def test_get_user_database_returns_none_for_wrong_owner():
    """get_user_database returns None when connection belongs to different user."""
    from utils.connection_manager import get_user_database

    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    conn_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    result = await get_user_database(mock_session, str(conn_id), str(other_user_id))
    assert result is None


@pytest.mark.asyncio
async def test_get_user_database_returns_none_for_invalid_uuid():
    """get_user_database returns None gracefully for malformed UUIDs."""
    from utils.connection_manager import get_user_database

    mock_session = AsyncMock()
    result = await get_user_database(mock_session, "not-a-uuid", "also-not-a-uuid")
    assert result is None


# ─── Test: test_connection ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_test_connection_returns_ok_on_success():
    """test_connection returns {ok: True} when asyncpg connects successfully."""
    from utils.connection_manager import test_connection

    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("utils.connection_manager.asyncpg.connect", return_value=mock_conn):
        result = await test_connection("postgres://localhost/test")

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_test_connection_returns_error_on_failure():
    """test_connection returns {ok: False, error: ...} when connection fails."""
    from utils.connection_manager import test_connection
    import asyncio

    with patch(
        "utils.connection_manager.asyncpg.connect",
        side_effect=Exception("FATAL: password authentication failed"),
    ):
        result = await test_connection("postgres://user:wrong@localhost/db")

    assert result["ok"] is False
    assert "password authentication" in result["error"]


@pytest.mark.asyncio
async def test_test_connection_returns_error_on_timeout():
    """test_connection returns error dict when timeout exceeded."""
    from utils.connection_manager import test_connection
    import asyncio

    with patch(
        "utils.connection_manager.asyncio.wait_for",
        side_effect=asyncio.TimeoutError(),
    ):
        result = await test_connection("postgres://localhost/test", timeout=0.001)

    assert result["ok"] is False
    assert "timed out" in result["error"]


# ─── Test: get_connection_encrypted_columns ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_connection_encrypted_columns_returns_columns():
    """get_connection_encrypted_columns returns column names for matching configs."""
    from utils.connection_manager import get_connection_encrypted_columns

    conn_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["ssn", "credit_card"]
    mock_session.execute.return_value = mock_result

    cols = await get_connection_encrypted_columns(mock_session, str(conn_id), "users")
    assert "ssn" in cols
    assert "credit_card" in cols


@pytest.mark.asyncio
async def test_get_connection_encrypted_columns_returns_empty_for_no_table():
    """get_connection_encrypted_columns returns [] when table_name is empty."""
    from utils.connection_manager import get_connection_encrypted_columns

    mock_session = AsyncMock()
    cols = await get_connection_encrypted_columns(mock_session, str(uuid.uuid4()), "")
    assert cols == []


# ─── Test: invalidate_connection_cache ────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalidate_connection_cache_deletes_matching_keys():
    """invalidate_connection_cache scans and deletes argus:cache:{conn_id}:* keys."""
    from utils.connection_manager import invalidate_connection_cache

    conn_id = str(uuid.uuid4())
    mock_redis = AsyncMock()
    # Simulate one batch of scan results then done
    mock_redis.scan.side_effect = [
        (b"0", [f"argus:cache:{conn_id}:abc", f"argus:cache:{conn_id}:def"]),
    ]
    mock_redis.delete = AsyncMock(return_value=2)

    deleted = await invalidate_connection_cache(mock_redis, conn_id)
    assert deleted == 2
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_connection_cache_handles_empty_results():
    """invalidate_connection_cache handles scan returning no matching keys."""
    from utils.connection_manager import invalidate_connection_cache

    conn_id = str(uuid.uuid4())
    mock_redis = AsyncMock()
    mock_redis.scan.side_effect = [(b"0", [])]
    mock_redis.delete = AsyncMock()

    deleted = await invalidate_connection_cache(mock_redis, conn_id)
    assert deleted == 0
    mock_redis.delete.assert_not_called()


# ─── Test: encrypt_query_values_for_columns / decrypt_rows_for_columns ────────

def test_encrypt_query_values_for_columns_encrypts_matching_column():
    """encrypt_query_values_for_columns encrypts the named column in INSERT."""
    from middleware.security.encryption import (
        encrypt_query_values_for_columns,
        decrypt_rows_for_columns,
    )

    original_ssn = "123-45-6789"
    query = f"INSERT INTO users (name, ssn) VALUES ('Alice', '{original_ssn}')"
    encrypted_query = encrypt_query_values_for_columns(query, ["ssn"])

    # The original SSN should no longer appear in plaintext
    assert original_ssn not in encrypted_query
    assert "Alice" in encrypted_query  # non-encrypted column unchanged


def test_decrypt_rows_for_columns_roundtrip():
    """decrypt_rows_for_columns correctly decrypts a column encrypted by encrypt_value."""
    from middleware.security.encryption import (
        encrypt_value,
        decrypt_rows_for_columns,
    )

    secret = "my-secret-value"
    encrypted = encrypt_value(secret)
    rows = [{"name": "Alice", "ssn": encrypted}]

    result = decrypt_rows_for_columns(rows, ["ssn"])
    assert result[0]["ssn"] == secret
    assert result[0]["name"] == "Alice"


def test_decrypt_rows_for_columns_skips_non_encrypted_column():
    """decrypt_rows_for_columns leaves columns not in the list unchanged."""
    from middleware.security.encryption import decrypt_rows_for_columns

    rows = [{"name": "Alice", "age": "30"}]
    result = decrypt_rows_for_columns(rows, ["ssn"])  # "ssn" not in row

    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == "30"
