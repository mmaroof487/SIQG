"""Unit tests for budget tracking."""
import pytest
from unittest.mock import AsyncMock, MagicMock

def _make_request(role="readonly", user_id="test-user"):
    request = MagicMock()
    request.app.state.redis = AsyncMock()
    request.app.state.redis.ttl.return_value = -1
    request.state.user_id = user_id
    request.state.role = role
    return request


@pytest.mark.asyncio
async def test_check_budget_passes_when_under_limit():
    """Budget check should pass if usage + cost < limit."""
    request = _make_request()
    request.app.state.redis.eval.return_value = 150.0  # Returns new usage

    from middleware.performance.budget import check_budget

    await check_budget(request, "test-user", 50.0)
    request.app.state.redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_check_budget_raises_when_exceeded():
    """Budget check should raise 429 when limit exceeded."""
    from fastapi import HTTPException
    from middleware.performance.budget import check_budget

    request = _make_request()
    request.app.state.redis.eval.return_value = -1  # Indicates limit exceeded
    request.app.state.redis.get.return_value = "49999.0"

    with pytest.raises(HTTPException) as exc_info:
        await check_budget(request, "test-user", 100.0)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_check_budget_admin_bypass():
    """Admin users should always pass budget check."""
    request = _make_request(role="admin")
    
    from middleware.performance.budget import check_budget

    await check_budget(request, "admin-user", 100.0)
    request.app.state.redis.eval.assert_not_called()


@pytest.mark.asyncio
async def test_refund_budget_uses_incrbyfloat():
    """Refund should use atomic INCRBYFLOAT."""
    request = _make_request()
    redis = request.app.state.redis

    from middleware.performance.budget import refund_budget

    await refund_budget(request, "test-user", 50.0)
    redis.incrbyfloat.assert_called_once()
