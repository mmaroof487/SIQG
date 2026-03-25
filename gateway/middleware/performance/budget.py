"""Daily query budget per user."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from datetime import datetime
import time

logger = get_logger(__name__)


async def check_daily_budget(request: Request, user_id: str, cost: float):
    """
    Check if user has exhausted daily query budget.
    Budget resets at midnight UTC.
    """
    redis = request.app.state.redis

    # Create daily key (resets at midnight UTC)
    today = datetime.utcnow().date()
    budget_key = f"budget:{user_id}:{today.isoformat()}"

    # Get current budget used
    current_usage = await redis.get(budget_key)
    current_usage = float(current_usage) if current_usage else 0

    # Check if would exceed
    new_usage = current_usage + cost
    if new_usage > settings.daily_budget_default:
        remaining = settings.daily_budget_default - current_usage
        logger.warning(
            f"User {user_id} exceeded daily budget. Usage: {new_usage} / {settings.daily_budget_default}"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Daily query budget exceeded. Remaining: {remaining:.0f} cost units. Resets at midnight UTC."
        )

    # Update usage
    # TTL = seconds until midnight
    now = datetime.utcnow()
    midnight = datetime.utcnow().replace(hour=23, minute=59, second=59)
    ttl = int((midnight - now).total_seconds()) + 1

    await redis.setex(budget_key, ttl, str(new_usage))
    logger.info(f"Budget update: {user_id} {new_usage:.0f} / {settings.daily_budget_default}")
