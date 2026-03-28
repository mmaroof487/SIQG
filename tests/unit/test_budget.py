"""Unit tests for budget tracking."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_request(role="readonly", user_id="test-user"):
    request = MagicMock()
    request.app.state.redis = AsyncMock()
    request.state.user_id = user_id
    request.state.role = role
    return request


@pytest.mark.asyncio
async def test_check_budget_passes_when_under_limit():
    """Budget check should pass if usage + cost < limit."""
    request = _make_request()
    request.app.state.redis.get.return_value = "100.0"  # Current usage

    from middleware.performance.budget import check_budget

    await check_budget(request, "test-user", 50.0)  # 100 + 50 = 150 < 50000


@pytest.mark.asyncio
async def test_check_budget_raises_when_exceeded():
    """Budget check should raise 429 when limit exceeded."""
    from fastapi import HTTPException
    from middleware.performance.budget import check_budget

    request = _make_request()
    request.app.state.redis.get.return_value = "49999.0"

    with pytest.raises(HTTPException) as exc_info:
        await check_budget(request, "test-user", 100.0)  # 49999 + 100 > 50000
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_check_budget_admin_bypass():
    """Admin users should always pass budget check."""
    request = _make_request(role="admin")
    request.app.state.redis.get.return_value = "999999.0"  # Over limit

    from middleware.performance.budget import check_budget

    # Should NOT raise even though usage > limit
    await check_budget(request, "admin-user", 100.0)


@pytest.mark.asyncio
async def test_deduct_budget_uses_incrbyfloat():
    """Deduction should use atomic INCRBYFLOAT, not GET+SET."""
    request = _make_request()
    redis = request.app.state.redis
    redis.incrbyfloat.return_value = 150.0
    redis.ttl.return_value = -1  # No expiry

    from middleware.performance.budget import deduct_budget

    await deduct_budget(request, "test-user", 50.0)
    redis.incrbyfloat.assert_called_once()


@pytest.mark.asyncio
async def test_deduct_budget_admin_skipped():
    """Admin deduction should be a no-op."""
    request = _make_request(role="admin")
    redis = request.app.state.redis

    from middleware.performance.budget import deduct_budget

    await deduct_budget(request, "admin-user", 50.0)
    redis.incrbyfloat.assert_not_called()


@pytest.mark.asyncio
async def test_deduct_budget_sets_ttl():
    """After deduction, TTL should be set to midnight UTC."""
    request = _make_request()
    redis = request.app.state.redis
    redis.incrbyfloat.return_value = 100.0
    redis.ttl.return_value = -1  # No TTL yet

    from middleware.performance.budget import deduct_budget

    await deduct_budget(request, "test-user", 50.0)
    redis.expire.assert_called_once()
