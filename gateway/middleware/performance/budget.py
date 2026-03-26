"""Daily query budget cost tracking per user."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def check_budget(request: Request, user_id: str, cost: float):
    """
    Check if user has sufficient daily query budget remaining.
    Budget resets at midnight UTC.

    Raises: HTTPException (429) if budget exceeded
    """
    redis = request.app.state.redis

    # Create daily key (resets at midnight UTC)
    today = datetime.utcnow().date()
    budget_key = f"siqg:budget:{user_id}:{today.isoformat()}"

    # Get current budget used
    current_usage = await redis.get(budget_key)
    current_usage = float(current_usage) if current_usage else 0.0

    # Check if would exceed
    new_usage = current_usage + cost
    if new_usage > settings.daily_budget_default:
        remaining = settings.daily_budget_default - current_usage
        logger.warning(
            f"User {user_id} budget exceeded. Usage: {new_usage:.2f} / {settings.daily_budget_default}"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Daily query budget exceeded. Remaining: {remaining:.2f} cost units. Resets at midnight UTC."
        )

    logger.debug(f"Budget check passed for {user_id}: {new_usage:.2f} / {settings.daily_budget_default}")


async def deduct_budget(request: Request, user_id: str, cost: float):
    """
    Deduct cost from user's daily budget using INCRBYFLOAT for atomicity.
    Called after successful query execution.
    """
    redis = request.app.state.redis

    # Create daily key (resets at midnight UTC)
    today = datetime.utcnow().date()
    budget_key = f"siqg:budget:{user_id}:{today.isoformat()}"

    # Deduct cost using INCRBYFLOAT for atomic float operation
    new_usage = await redis.incrbyfloat(budget_key, cost)

    # TTL = seconds until midnight UTC (next day at 00:00)
    from datetime import timedelta
    now = datetime.utcnow()
    tomorrow_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    ttl = int((tomorrow_midnight - now).total_seconds())

    await redis.expire(budget_key, ttl)
    logger.debug(f"Budget deducted: {user_id} cost {cost:.2f}, total {new_usage:.2f} / {settings.daily_budget_default}")
