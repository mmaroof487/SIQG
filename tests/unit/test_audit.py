"""Unit tests for audit logging."""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from models import AuditLog


@pytest.mark.asyncio
@patch("middleware.observability.audit.PrimarySession")
@patch("middleware.observability.audit.asyncio.create_task")
async def test_write_audit_log_is_fire_and_forget(mock_create_task, mock_session):
    """Write audit log should schedule a background task and not await it."""
    from middleware.observability.audit import write_audit_log

    await write_audit_log(
        trace_id="trace-123",
        user_id="user-123",
        role="readonly",
        fingerprint="abcd",
        query_type="SELECT",
        latency_ms=45.0,
        status="success",
        cached=False,
        slow=False,
        anomaly_flag=False,
    )
    
    # Ensure it created a background task
    mock_create_task.assert_called_once()
    assert not mock_session.called  # Session isn't opened synchronously


@pytest.mark.asyncio
@patch("middleware.observability.audit.PrimarySession")
async def test_get_audit_logs(mock_session_cls):
    """Get audit logs should query the DB and return formatted list."""
    mock_session = AsyncMock()
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    
    # Mocking a returned row
    class MockRow:
        trace_id = "trace-1"
        user_id = "user-1"
        role = "admin"
        query_fingerprint = "hash"
        query_type = "SELECT"
        latency_ms = 10.0
        status = "success"
        cached = True
        slow = False
        anomaly_flag = False
        error_message = None
        created_at = None

    mock_result.scalars.return_value.all.return_value = [MockRow()]
    mock_session.execute.return_value = mock_result
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cls.return_value.__aexit__ = AsyncMock()

    from middleware.observability.audit import get_audit_logs

    logs = await get_audit_logs(limit=10)
    assert len(logs) == 1
    assert logs[0]["trace_id"] == "trace-1"
    
    # Verify execution was called
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch("middleware.observability.audit.PrimarySession")
async def test_get_audit_logs_with_user_filter(mock_session_cls):
    """Get audit logs should apply user_id filter."""
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cls.return_value.__aexit__ = AsyncMock()

    from middleware.observability.audit import get_audit_logs

    await get_audit_logs(user_id="specific-user-id")
    
    # Verify execution was called with a parameterized query (where clause)
    call_args = mock_session.execute.call_args[0][0]
    # The statement string should contain a WHERE clause
    assert "WHERE" in str(call_args)
