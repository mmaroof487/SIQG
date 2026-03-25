"""Rate limiting middleware with anomaly detection."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger
import time

logger = get_logger(__name__)


async def check_rate_limit(request: Request, user_id: str):
    """
    Check rate limit using sliding window counter.
    Also detect anomalies (request rate 3x baseline).
    """
    redis = request.app.state.redis
    window_seconds = 60

    # Rate limit key
    limit_key = f"ratelimit:{user_id}"

    # Get current minute bucket
    current_bucket = int(time.time()) // window_seconds
    bucket_key = f"{limit_key}:{current_bucket}"

    # Increment counter for this bucket
    count = await redis.incr(bucket_key)
    if count == 1:
        await redis.expire(bucket_key, window_seconds + 1)

    # Check if over limit
    limit = settings.rate_limit_per_minute
    if count > limit:
        logger.warning(f"Rate limit exceeded: {user_id} ({count} > {limit} per minute)")
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Limit: {limit} per minute"
        )

    # Check for anomaly (3x baseline)
    # Baseline = average of last 5 minutes
    baseline_key = f"ratelimit_baseline:{user_id}"
    baseline = await redis.get(baseline_key)
    baseline = float(baseline) if baseline else limit * 0.5

    if count > baseline * 3:
        # Flag anomaly but don't block
        anomaly_key = f"anomaly:{user_id}"
        await redis.setex(anomaly_key, window_seconds, "true")
        request.state.anomaly_flag = True
        logger.warning(f"Anomaly detected: {user_id} ({count} > {baseline * 3:.0f} baseline)")
    else:
        request.state.anomaly_flag = False

    # Update rolling baseline (exponential moving average)
    new_baseline = baseline * 0.8 + count * 0.2
    await redis.setex(baseline_key, window_seconds * 10, str(new_baseline))
