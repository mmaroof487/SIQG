"""Daily query budget cost tracking per user."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)


async def _budget_key(user_id: str) -> str:
    """Build daily budget key using UTC date."""
    today = datetime.utcnow().date()
    return f"argus:budget:{user_id}:{today.isoformat()}"


async def _ensure_ttl(redis, budget_key: str):
    """Set TTL to midnight UTC if not already set."""
    ttl = await redis.ttl(budget_key)
    if ttl < 0:  # No TTL set yet (-1 no expiry, -2 key doesn't exist)
        now = datetime.utcnow()
        tomorrow_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        seconds_until_midnight = int((tomorrow_midnight - now).total_seconds())
        await redis.expire(budget_key, seconds_until_midnight)


async def check_budget(request: Request, user_id: str, cost: float):
    """
    Check if user has sufficient daily query budget remaining.
    Uses atomic INCRBYFLOAT to prevent race conditions under concurrent load.
    Budget resets at midnight UTC.

    Raises: HTTPException (429) if budget exceeded.
    """
    # Admin role gets unlimited budget
    role = getattr(request.state, "role", "guest")
    if role == "admin":
        logger.debug(f"Budget check skipped for admin user {user_id}")
        return

    redis = request.app.state.redis
    budget_key = await _budget_key(user_id)

    # Atomically check current usage before committing
    current_usage = await redis.get(budget_key)
    current_usage = float(current_usage) if current_usage else 0.0

    if current_usage + cost > settings.daily_budget_default:
        remaining = max(0, settings.daily_budget_default - current_usage)
        logger.warning(
            f"User {user_id} budget exceeded. "
            f"Usage: {current_usage + cost:.2f} / {settings.daily_budget_default}"
        )
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily query budget exceeded. "
                f"Remaining: {remaining:.2f} cost units. "
                f"Resets at midnight UTC."
            ),
        )

    logger.debug(
        f"Budget check passed for {user_id}: "
        f"{current_usage + cost:.2f} / {settings.daily_budget_default}"
    )


async def deduct_budget(request: Request, user_id: str, cost: float):
    """
    Deduct cost from user's daily budget using INCRBYFLOAT for atomicity.
    Called AFTER successful query execution only.
    """
    # Admin role gets unlimited budget — no deduction needed
    role = getattr(request.state, "role", "guest")
    if role == "admin":
        return

    redis = request.app.state.redis
    budget_key = await _budget_key(user_id)

    # Atomic float increment — no GET+SET race condition
    new_usage = await redis.incrbyfloat(budget_key, cost)

    # Ensure expiry is set (midnight UTC)
    await _ensure_ttl(redis, budget_key)

    logger.debug(
        f"Budget deducted: {user_id} cost {cost:.2f}, "
        f"total {new_usage:.2f} / {settings.daily_budget_default}"
    )
