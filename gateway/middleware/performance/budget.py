"""Daily query budget cost tracking per user."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from datetime import datetime, timezone, timedelta

logger = get_logger(__name__)


async def _budget_key(user_id: str) -> str:
    """Build daily budget key using UTC date."""
    today = datetime.now(timezone.utc).replace(tzinfo=None).date()
    return f"argus:budget:{user_id}:{today.isoformat()}"


async def _ensure_ttl(redis, budget_key: str):
    """Set TTL to midnight UTC if not already set."""
    ttl = await redis.ttl(budget_key)
    if ttl < 0:  # No TTL set yet (-1 no expiry, -2 key doesn't exist)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        tomorrow_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        seconds_until_midnight = int((tomorrow_midnight - now).total_seconds())
        await redis.expire(budget_key, seconds_until_midnight)


async def check_budget(request: Request, user_id: str, cost: float):
    """
    Atomically check and deduct user's daily query budget.
    Uses Lua script to prevent TOCTOU race conditions under concurrent load.
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
    
    # Lua script for atomic check-and-deduct
    # KEYS[1] = budget_key, ARGV[1] = cost, ARGV[2] = limit
    script = """
    local current = tonumber(redis.call('get', KEYS[1]) or '0')
    local cost = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    if current + cost > limit then
        return -1
    else
        redis.call('incrbyfloat', KEYS[1], cost)
        return current + cost
    end
    """
    
    new_usage = await redis.eval(script, 1, budget_key, cost, settings.daily_budget_default)
    
    if new_usage == -1:
        current_usage = float(await redis.get(budget_key) or 0.0)
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

    await _ensure_ttl(redis, budget_key)
    logger.debug(
        f"Budget check and deduction passed for {user_id}: "
        f"{new_usage:.2f} / {settings.daily_budget_default}"
    )


async def deduct_budget(request: Request, user_id: str, cost: float):
    """
    Deprecated: check_budget now performs atomic deduction.
    This function is left as a no-op for backward compatibility.
    """
    pass

async def refund_budget(request: Request, user_id: str, cost: float):
    """Refund budget if execution fails after check_budget has reserved it."""
    role = getattr(request.state, "role", "guest")
    if role == "admin":
        return
        
    redis = request.app.state.redis
    budget_key = await _budget_key(user_id)
    await redis.incrbyfloat(budget_key, -cost)
    logger.debug(f"Budget refunded for {user_id}: {cost:.2f}")


