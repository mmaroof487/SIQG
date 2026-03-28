"""Unit tests for rate limiting."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_request(user_id="test-user"):
    """Create a mock request with Redis."""
    request = MagicMock()
    request.app.state.redis = AsyncMock()
    request.state.user_id = user_id
    request.state.anomaly_flag = False
    return request


@pytest.mark.asyncio
async def test_rate_limit_within_limit():
    """Test request within limit passes without exception."""
    request = _make_request()
    redis = request.app.state.redis
    redis.incr.return_value = 5  # Under default limit of 60
    redis.ttl.return_value = 50
    redis.get.return_value = None  # No baseline

    from middleware.security.rate_limiter import check_rate_limit

    # Should not raise
    await check_rate_limit(request, "test-user")


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    """Test request exceeding limit raises 429."""
    from fastapi import HTTPException
    from middleware.security.rate_limiter import check_rate_limit

    request = _make_request()
    redis = request.app.state.redis
    redis.incr.return_value = 999  # Way over limit
    redis.ttl.return_value = 50
    redis.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await check_rate_limit(request, "test-user")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_anomaly_flag():
    """Test anomaly flag is set when count exceeds 3x baseline."""
    request = _make_request()
    redis = request.app.state.redis
    redis.incr.return_value = 10  # Under user limit
    redis.ttl.return_value = 50
    redis.get.return_value = "2.0"  # Baseline is 2 → 3x = 6, 10 > 6 → anomaly

    from middleware.security.rate_limiter import check_rate_limit

    await check_rate_limit(request, "test-user")
    assert request.state.anomaly_flag is True


@pytest.mark.asyncio
async def test_rate_limit_sets_expire_on_first_increment():
    """Test EXPIRE is set when count is 1 (first request in window)."""
    request = _make_request()
    redis = request.app.state.redis
    redis.incr.return_value = 1  # First request
    redis.ttl.return_value = -1  # No TTL set yet
    redis.get.return_value = None

    from middleware.security.rate_limiter import check_rate_limit

    await check_rate_limit(request, "test-user")
    redis.expire.assert_called()
