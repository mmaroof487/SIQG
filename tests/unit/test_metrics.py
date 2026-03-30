"""Unit tests for Redis metrics."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_increment_counter():
    """Increment should call INCRBYFLOAT on Redis."""
    request = MagicMock()
    redis = AsyncMock()
    request.app.state.redis = redis

    from middleware.observability.metrics import increment

    await increment(request, "requests_total")
    redis.incrbyfloat.assert_called_once_with("siqg:metrics:requests_total", 1)


@pytest.mark.asyncio
async def test_increment_counter_custom_amount():
    """Increment should support custom amount."""
    request = MagicMock()
    redis = AsyncMock()
    request.app.state.redis = redis

    from middleware.observability.metrics import increment

    await increment(request, "errors", 5)
    redis.incrbyfloat.assert_called_once_with("siqg:metrics:errors", 5)


@pytest.mark.asyncio
async def test_record_latency_uses_pipeline():
    """Latency recording should use LPUSH + LTRIM in a pipeline."""
    request = MagicMock()
    redis = AsyncMock()
    redis.pipeline = MagicMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock()
    redis.pipeline.return_value = pipe

    request.app.state.redis = redis

    from middleware.observability.metrics import record_latency

    await record_latency(request, 42.5)
    pipe.lpush.assert_called_once_with("siqg:metrics:latency_samples", 42.5)
    pipe.ltrim.assert_called_once_with("siqg:metrics:latency_samples", 0, 999)
    pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_live_metrics_empty():
    """Live metrics should handle empty Redis gracefully."""
    redis = AsyncMock()
    redis.mget.return_value = [None, None, None, None, None, None]
    redis.lrange.return_value = []

    from middleware.observability.metrics import get_live_metrics

    metrics = await get_live_metrics(redis)
    assert metrics["requests_total"] == 0
    assert metrics["latency_p50"] == 0
    assert metrics["latency_p95"] == 0
    assert metrics["latency_p99"] == 0
    assert metrics["cache_hit_ratio"] == 0


@pytest.mark.asyncio
async def test_get_live_metrics_with_data():
    """Live metrics should compute percentiles correctly from latency samples."""
    redis = AsyncMock()
    redis.mget.return_value = ["100", "40", "60", "5", "3", "2"]
    # Create 100 samples from 1.0 to 100.0
    redis.lrange.return_value = [str(float(i)) for i in range(1, 101)]

    from middleware.observability.metrics import get_live_metrics

    metrics = await get_live_metrics(redis)
    assert metrics["requests_total"] == 100
    assert metrics["cache_hits"] == 40
    assert metrics["latency_p50"] == 51.0  # 50th percentile of 1..100
    assert metrics["latency_p95"] == 96.0  # 95th percentile
    assert metrics["cache_hit_ratio"] == 40.0  # 40/(40+60) * 100


@pytest.mark.asyncio
async def test_get_live_metrics_division_by_zero():
    """Cache hit ratio should handle 0 total requests."""
    redis = AsyncMock()
    redis.mget.return_value = ["0", "0", "0", "0", "0", "0"]
    redis.lrange.return_value = []

    from middleware.observability.metrics import get_live_metrics

    metrics = await get_live_metrics(redis)
    assert metrics["cache_hit_ratio"] == 0
