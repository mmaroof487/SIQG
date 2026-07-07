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
    client_ip = request.client.host if request.client else "unknown"
    key = f"argus:brute:{client_ip}:{username}"

    count = await redis.get(key)
    count = int(count) if count else 0

    global_key = f"argus:brute:user:{username}"
    global_count = await redis.get(global_key)
    global_count = int(global_count) if global_count else 0

    if global_count >= settings.brute_force_max_attempts:
        ttl = await redis.ttl(global_key)
        logger.warning(
            f"Global brute force lockout: {username}, TTL={ttl}s"
        )
        raise HTTPException(
            status_code=423,
            detail=f"Account locked due to too many failed attempts globally. Try again in {ttl} seconds."
        )

    if count >= settings.brute_force_max_attempts:
        ttl = await redis.ttl(key)
        logger.warning(
            f"Brute force lockout: {username} from {request.client.host}, TTL={ttl}s"
        )
        raise HTTPException(
            status_code=423,
            detail=f"Account locked due to too many failed attempts from this IP. Try again in {ttl} seconds."
        )


async def record_failed_attempt(request: Request, username: str):
    """Record a failed auth attempt."""
    redis = request.app.state.redis
    client_ip = request.client.host if request.client else "unknown"
    key = f"argus:brute:{client_ip}:{username}"
    ttl = settings.brute_force_lockout_minutes * 60

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, ttl)

    global_key = f"argus:brute:user:{username}"
    global_count = await redis.incr(global_key)
    if global_count == 1:
        await redis.expire(global_key, ttl)

    logger.warning(
        f"Failed auth attempt: {username} from {client_ip} (attempt {count}, global {global_count})"
    )


async def record_successful_attempt(request: Request, username: str):
    """Clear failed attempts on successful auth."""
    redis = request.app.state.redis
    client_ip = request.client.host if request.client else "unknown"
    key = f"argus:brute:{client_ip}:{username}"
    global_key = f"argus:brute:user:{username}"
    await redis.delete(key)
    await redis.delete(global_key)
