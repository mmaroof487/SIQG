"""Query execution with routing, timeout, and retry."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from utils.db import PrimarySession, ReplicaSession
import asyncio
import json

logger = get_logger(__name__)


def get_session_for_query(query: str, request: Request):
    """
    Route queries to correct database:
    - SELECT → Replica (read-only)
    - INSERT/UPDATE → Primary (write)
    
    Returns async context manager for session.
    """
    query_upper = query.upper().strip()

    if query_upper.startswith("SELECT"):
        return ReplicaSession()
    else:
        return PrimarySession()


async def execute_with_timeout(
    request: Request,
    query: str,
    timeout_seconds: int = None,
) -> tuple:
    """
    Execute query with timeout and exponential backoff retry.
    
    Returns: (rows, column_names)
    """
    if timeout_seconds is None:
        timeout_seconds = settings.query_timeout_seconds

    # Retry logic: 100ms, 200ms, 400ms (3 attempts)
    retry_delays = [0.1, 0.2, 0.4]
    last_error = None

    for attempt in range(len(retry_delays) + 1):
        try:
            session_ctx = get_session_for_query(query, request)
            async with session_ctx as session:
                # Set query timeout
                await session.execute(f"SET statement_timeout = {timeout_seconds * 1000}")

                # Execute query
                result = await asyncio.wait_for(
                    session.execute(query),
                    timeout=timeout_seconds
                )
                
                rows = result.fetchall()
                column_names = list(result.keys()) if result.keys() else []
                
                logger.info(f"Query executed: {len(rows)} rows")
                return rows, column_names

        except asyncio.TimeoutError:
            last_error = f"Query timeout ({timeout_seconds}s)"
            logger.warning(f"Query timeout (attempt {attempt + 1}): {last_error}")
            if attempt < len(retry_delays):
                await asyncio.sleep(retry_delays[attempt])

        except Exception as e:
            last_error = str(e)
            # Retry on transient errors
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                logger.warning(f"Transient error (attempt {attempt + 1}): {e}")
                if attempt < len(retry_delays):
                    await asyncio.sleep(retry_delays[attempt])
                continue
            else:
                # Non-transient error, fail immediately
                logger.error(f"Query execution error: {e}")
                raise HTTPException(status_code=400, detail=str(e)[:100])

    # All retries failed
    logger.error(f"Query failed after {len(retry_delays) + 1} attempts: {last_error}")
    raise HTTPException(status_code=500, detail=f"Database error: {last_error}")
