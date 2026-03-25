"""Metrics collection and exposure."""
from fastapi import Request
from utils.logger import get_logger

logger = get_logger(__name__)


async def record_query_metric(
    request: Request,
    query_type: str,
    latency_ms: float,
    cached: bool = False,
    slow: bool = False,
    status: str = "success",
):
    """
    Record query metrics in Redis counters.
    Exposed via `/api/v1/metrics/live` for React dashboard.
    """
    redis = request.app.state.redis

    # Counters for this minute
    now_bucket = int(request.state.start_time // 60)
    metrics_key = f"metrics:{now_bucket}"

    try:
        # Increment counters
        await redis.hincrby(metrics_key, "total_requests", 1)
        await redis.hincrby(metrics_key, f"request_type:{query_type}", 1)

        if cached:
            await redis.hincrby(metrics_key, "cached_requests", 1)

        if slow:
            await redis.hincrby(metrics_key, "slow_requests", 1)

        if status == "success":
            await redis.hincrby(metrics_key, "successful_requests", 1)
        else:
            await redis.hincrby(metrics_key, "failed_requests", 1)

        # Store latency for percentile calculation (sorted set)
        latency_key = f"latencies:{now_bucket}"
        await redis.zadd(latency_key, {f"{latency_ms}": request.state.trace_id})

        # Set TTL (keep metrics for 1 hour)
        await redis.expire(metrics_key, 3600)
        await redis.expire(latency_key, 3600)

        logger.info(f"Metrics recorded: {query_type} {latency_ms:.1f}ms cached={cached}")
    except Exception as e:
        logger.warning(f"Metrics recording error: {e}")
