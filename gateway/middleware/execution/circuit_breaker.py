"""Circuit breaker pattern for DB resilience."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
import time

logger = get_logger(__name__)


class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


async def check_circuit_breaker(request: Request) -> str:
    """
    Check circuit breaker state.

    States:
    - CLOSED: normal operation (all requests allowed)
    - OPEN: DB is down (reject all with 503)
    - HALF_OPEN: testing recovery (probe 1 request)

    Returns: state
    """
    redis = request.app.state.redis
    cb_state_key = "circuit_breaker:state"
    cb_count_key = "circuit_breaker:failure_count"

    state = await redis.get(cb_state_key) or CircuitBreakerState.CLOSED

    # If OPEN, check if cooldown period has passed
    if state == CircuitBreakerState.OPEN:
        opened_at = await redis.get("circuit_breaker:opened_at")
        if opened_at:
            opened_time = float(opened_at)
            elapsed = time.time() - opened_time
            if elapsed > settings.circuit_cooldown_seconds:
                # Transition to HALF_OPEN
                logger.info(f"Circuit breaker: OPEN → HALF_OPEN (cooldown {elapsed:.0f}s passed)")
                await redis.setex(cb_state_key, settings.circuit_cooldown_seconds * 10, CircuitBreakerState.HALF_OPEN)
                return CircuitBreakerState.HALF_OPEN

        # Still OPEN, reject request
        logger.warning("Circuit breaker OPEN: rejecting request with 503")
        raise HTTPException(status_code=503, detail="Database temporarily unavailable. Circuit breaker is OPEN.")

    return state


async def record_success(request: Request):
    """Record successful query execution. Reset failure count."""
    redis = request.app.state.redis
    cb_state_key = "circuit_breaker:state"
    cb_count_key = "circuit_breaker:failure_count"

    # If HALF_OPEN, transition back to CLOSED
    state = await redis.get(cb_state_key) or CircuitBreakerState.CLOSED
    if state == CircuitBreakerState.HALF_OPEN:
        await redis.delete(cb_state_key)  # Back to CLOSED (default)
        await redis.delete(cb_count_key)
        logger.info("Circuit breaker: HALF_OPEN → CLOSED (recovery successful)")
        return

    # If CLOSED, just ensure counter is cleared
    await redis.delete(cb_count_key)


async def record_failure(request: Request):
    """Record failed query execution. Increment failure count and check threshold."""
    redis = request.app.state.redis
    cb_state_key = "circuit_breaker:state"
    cb_count_key = "circuit_breaker:failure_count"

    # Increment failure count
    count = await redis.incr(cb_count_key)
    await redis.expire(cb_count_key, 60)  # Reset count every 60s

    logger.warning(f"DB failure recorded: {count} consecutive failures")

    if count >= settings.circuit_failure_threshold:
        # Open circuit breaker
        logger.error(f"Circuit breaker OPEN: {count} >= {settings.circuit_failure_threshold} failures")
        await redis.setex(cb_state_key, settings.circuit_cooldown_seconds * 10, CircuitBreakerState.OPEN)
        await redis.setex("circuit_breaker:opened_at", settings.circuit_cooldown_seconds * 10, str(time.time()))
