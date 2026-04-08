"""Rate limiting middleware with anomaly detection."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger
import time

logger = get_logger(__name__)


async def check_rate_limit(request: Request, user_id: str, role: str = "readonly"):
    """
    Check rate limit using sliding window counter with per-role limits.
    Also detect anomalies (request rate 3x baseline).

    Args:
        request: FastAPI Request object
        user_id: User identifier
        role: User role (admin, readonly, guest) to determine rate limit
    """
    redis = request.app.state.redis
    window_seconds = 60

    # Get per-role rate limit
    role_limits = settings.get_rate_limit_for_role
    limit = role_limits.get(role, settings.rate_limit_per_minute)

    # Rate limit key
    limit_key = f"argus:ratelimit:{user_id}"

    # Get current minute bucket
    current_bucket = int(time.time()) // window_seconds
    bucket_key = f"{limit_key}:{current_bucket}"

    # Increment counter for this bucket
    count = await redis.incr(bucket_key)
    if count == 1:
        # EXPIRE set to 2x window to handle edge cases at window boundaries
        await redis.expire(bucket_key, window_seconds * 2)

    # Check if over limit
    if count > limit:
        logger.warning(f"Rate limit exceeded: {user_id} ({count} > {limit} per minute, role={role})")
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Limit: {limit} per minute for {role} role"
        )

    # Check for anomaly (3x baseline)
    # Baseline = average of last 5 minutes
    baseline_key = f"argus:ratelimit_baseline:{user_id}"
    baseline = await redis.get(baseline_key)
    baseline = float(baseline) if baseline else limit * 0.5

    if count > baseline * 3:
        # Flag anomaly but don't block
        anomaly_key = f"argus:anomaly:{user_id}"
        await redis.setex(anomaly_key, window_seconds, "true")
        request.state.anomaly_flag = True
        logger.warning(f"Anomaly detected: {user_id} ({count} > {baseline * 3:.0f} baseline)")
    else:
        request.state.anomaly_flag = False

    # Update rolling baseline (exponential moving average)
    new_baseline = baseline * 0.8 + count * 0.2
    await redis.setex(baseline_key, window_seconds * 10, str(new_baseline))
