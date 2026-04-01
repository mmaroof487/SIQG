"""Brute force protection middleware."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def check_brute_force(request: Request, username: str):
    """
    Check if user/IP is locked due to too many failed auth attempts.
    Raises 423 if locked.
    """
    redis = request.app.state.redis
    key = f"argus:brute:{request.client.host}:{username}"

    count = await redis.get(key)
    count = int(count) if count else 0

    if count >= settings.brute_force_max_attempts:
        ttl = await redis.ttl(key)
        logger.warning(
            f"Brute force lockout: {username} from {request.client.host}, TTL={ttl}s"
        )
        raise HTTPException(
            status_code=423,
            detail=f"Account locked due to too many failed attempts. Try again in {ttl} seconds."
        )


async def record_failed_attempt(request: Request, username: str):
    """Record a failed auth attempt."""
    redis = request.app.state.redis
    key = f"argus:brute:{request.client.host}:{username}"
    ttl = settings.brute_force_lockout_minutes * 60

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, ttl)

    logger.warning(
        f"Failed auth attempt: {username} from {request.client.host} (attempt {count})"
    )


async def record_successful_attempt(request: Request, username: str):
    """Clear failed attempts on successful auth."""
    redis = request.app.state.redis
    key = f"argus:brute:{request.client.host}:{username}"
    await redis.delete(key)
