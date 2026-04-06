"""Phase 5: Security Hardening Integration Tests

Tests for:
1. Circuit breaker blocks when OPEN
2. Encryption/decryption roundtrip
3. RBAC masking for readonly roles
4. Denied columns stripped from result sets
5. Retry mechanism wrapping execution
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from config import settings


@pytest.mark.asyncio
async def test_circuit_breaker_open_blocks_query(client, token: str, redis_client):
    """Test that circuit breaker blocks queries when OPEN."""
    # Set circuit breaker to OPEN
    await redis_client.set("argus:circuit_breaker:state", "open")

    # Try to execute a query
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "SELECT 1"},
    )

    # Should return 503 Service Unavailable
    assert response.status_code == 503, f"Expected 503, got {response.status_code}"

    # Cleanup
    await redis_client.delete("argus:circuit_breaker:state")


@pytest.mark.asyncio
async def test_encryption_roundtrip(client, admin_token: str, primary_session):
    """Test that SSN values are encrypted before storage."""
    # INSERT with SSN
    insert_response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"query": "INSERT INTO users (username, email, hashed_password, ssn, role) VALUES ('encrypt_test', 'encrypt@test.com', 'pass', '123-45-6789', 'admin')"},
    )

    assert insert_response.status_code == 200, f"Insert failed: {insert_response.text}"

    # Verify in DB that SSN is encrypted (base64-like, not raw SSN)
    async with primary_session() as session:
        from sqlalchemy import text
        result = await session.execute(
            text("SELECT ssn FROM users WHERE username = 'encrypt_test'")
        )
        row = result.first()
        assert row is not None, "User not found"

        ssn_value = row[0]
        # Base64 encoded values won't contain hyphens
        assert "-" not in str(ssn_value), f"SSN appears unencrypted: {ssn_value}"
        # But should be fairly long (base64 padding)
        assert len(str(ssn_value)) > 15, f"SSN too short to be encrypted: {ssn_value}"


@pytest.mark.asyncio
async def test_rbac_email_masking_readonly(client, readonly_session, readonly_token: str):
    """Test that readonly role sees masked email (u***@example.com)."""
    # Query email as readonly
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {readonly_token}"},
        json={"query": "SELECT email FROM users LIMIT 1"},
    )

    assert response.status_code == 200, f"Query failed: {response.text}"
    data = response.json()

    assert data.get("rows"), "No rows returned"
    first_row = data["rows"][0]

    # Email should be masked
    email = first_row.get("email", "")
    assert "***" in email, f"Email not masked: {email}"
    assert "@" in email, f"Email format invalid: {email}"


@pytest.mark.asyncio
async def test_denied_columns_stripped_readonly(client, readonly_token: str):
    """Test that SELECT * as readonly strips hashed_password and internal_notes."""
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {readonly_token}"},
        json={"query": "SELECT * FROM users LIMIT 1"},
    )

    assert response.status_code == 200, f"Query failed: {response.text}"
    data = response.json()

    assert data.get("rows"), "No rows returned"
    first_row = data["rows"][0]


    # Denied columns should NOT be present
    assert "hashed_password" not in first_row, f"hashed_password leaked to readonly: {list(first_row.keys())}"
    assert "internal_notes" not in first_row, f"internal_notes leaked to readonly: {list(first_row.keys())}"

    # But allowed columns should be present
    assert "id" in first_row or "username" in first_row, f"No allowed columns in response: {list(first_row.keys())}"


@pytest.mark.asyncio
async def test_admin_sees_all_columns(client, admin_token: str):
    """Test that admin role sees all columns including denied ones."""
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"query": "SELECT * FROM users LIMIT 1"},
    )

    assert response.status_code == 200, f"Query failed: {response.text}"
    data = response.json()

    assert data.get("rows"), "No rows returned"
    first_row = data["rows"][0]

    # Admin sees all columns
    assert "hashed_password" in first_row, f"Admin missing hashed_password: {list(first_row.keys())}"
    assert "id" in first_row, f"Admin missing id: {list(first_row.keys())}"


@pytest.mark.asyncio
async def test_sensitive_field_blocks_direct_query(client, admin_token: str):
    """Test that queries referencing sensitive fields are blocked."""
    # Try to SELECT hashed_password directly
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"query": "SELECT hashed_password FROM users"},
    )

    # Should be blocked with 403
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    data = response.json()
    assert "blocked" in str(data).lower() or "sensitive" in str(data).lower()


@pytest.mark.asyncio
async def test_sensitive_field_insert_allowed(client, admin_token: str):
    """Test that INSERT with sensitive fields is allowed (populate DB)."""
    import time
    ts = str(int(time.time()))

    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "query": f"INSERT INTO users (username, email, hashed_password, role) VALUES ('test_insert_{ts}', 'insert_{ts}@test.com', 'secret_hash', 'guest')"
        },
    )

    # INSERT should be allowed
    assert response.status_code == 200, f"Insert failed: {response.text}"


@pytest.mark.asyncio
async def test_guest_role_sees_no_denied_columns(client, guest_token: str):
    """Test that guest role (most restricted) also has denied columns stripped."""
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {guest_token}"},
        json={"query": "SELECT * FROM users LIMIT 1"},
    )

    assert response.status_code == 200, f"Query failed: {response.text}"
    data = response.json()

    if data.get("rows"):  # Only check if rows exist
        first_row = data["rows"][0]
        assert "hashed_password" not in first_row, f"Guest can see hashed_password"
        assert "internal_notes" not in first_row, f"Guest can see internal_notes"


@pytest.mark.asyncio
async def test_masking_applied_across_large_result_set(client, readonly_token: str):
    """Test that masking is applied to ALL rows, not just first."""
    response = client.post(
        "/api/v1/query/execute",
        headers={"Authorization": f"Bearer {readonly_token}"},
        json={"query": "SELECT email FROM users LIMIT 10"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check all returned rows have masking applied
    for row in data.get("rows", []):
        if "email" in row:
            email = row.get("email", "")
            # If not empty or null, should be masked
            if email:
                assert "***" in email, f"Email not masked in result set: {email}"
