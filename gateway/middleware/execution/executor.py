"""Query execution with routing, timeout, and retry."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from utils.db import PrimarySession, ReplicaSession
import asyncio
from sqlalchemy import text
from middleware.execution.circuit_breaker import check_circuit_breaker, record_failure, record_success

logger = get_logger(__name__)


def _first_keyword(query: str) -> str:
    parts = query.strip().split()
    return parts[0].upper() if parts else ""


def get_session_for_query(query: str, request: Request):
    """
    Route queries to correct database:
    - SELECT → Replica (read-only)
    - INSERT/UPDATE → Primary (write)

    Returns async context manager for session.
    """
    keyword = _first_keyword(query)
    query_upper = query.strip().upper()

    # Route CTEs to primary for safety because CTEs can include writes.
    if keyword == "WITH":
        return PrimarySession()
    if keyword == "SELECT":
        return ReplicaSession()
    return PrimarySession()


def _timeout_for_role(request: Request) -> int:
    role = getattr(request.state, "role", "guest")
    if role == "admin":
        return settings.admin_query_timeout_seconds
    return settings.query_timeout_seconds


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
        timeout_seconds = _timeout_for_role(request)

    # Retry logic: 100ms, 200ms, 400ms (3 attempts)
    retry_delays = [0.1, 0.2, 0.4]
    last_error = None

    for attempt in range(len(retry_delays) + 1):
        try:
            await check_circuit_breaker(request)
            session_ctx = get_session_for_query(query, request)
            async with session_ctx as session:
                # Set query timeout (skip for SQLite as it doesn't support it)
                try:
                    await session.execute(text(f"SET statement_timeout = {timeout_seconds * 1000}"))
                except Exception:
                    # SQLite and other databases may not support statement_timeout
                    pass

                # Execute query. Escape colons to prevent SQLAlchemy from treating them as bind parameters
                # (which would crash native Postgres casting like ::uuid or JSON ops).
                safe_query = query.replace(':', '\\:')
                logger.info(f"[EXECUTOR] Executing: {safe_query[:100]}")
                result = await asyncio.wait_for(
                    session.execute(text(safe_query)),
                    timeout=timeout_seconds
                )

                logger.info(f"[EXECUTOR] Result type: {type(result).__name__}")
                try:
                    rows = result.fetchall()
                    logger.info(f"[EXECUTOR] fetchall() succeeded - got {len(rows)} rows")
                    if len(rows) > 0:
                        logger.info(f"[EXECUTOR] First row: {rows[0]}")
                except Exception as e:
                    logger.error(f"[EXECUTOR] ❌ fetchall() failed: {type(e).__name__}: {e}")
                    rows = []

                try:
                    column_names = list(result.keys()) if result.keys() else []
                except Exception as e:
                    logger.error(f"[EXECUTOR] Error getting column names: {e}")
                    column_names = []

                logger.info(f"[EXECUTOR] Final result: {len(rows)} rows, columns: {column_names}")
                await record_success(request)
                return rows, column_names

        except asyncio.TimeoutError:
            last_error = f"Query timeout ({timeout_seconds}s)"
            logger.warning(f"Query timeout (attempt {attempt + 1}): {last_error}")
            if attempt < len(retry_delays):
                await asyncio.sleep(retry_delays[attempt])
                continue
            await record_failure(request)
            raise HTTPException(status_code=504, detail="Gateway Timeout")

        except Exception as e:
            last_error = str(e)
            # Retry on transient errors
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                logger.warning(f"Transient error (attempt {attempt + 1}): {e}")
                if attempt < len(retry_delays):
                    await asyncio.sleep(retry_delays[attempt])
                else:
                    await record_failure(request)
                continue
            else:
                # Non-transient error, fail immediately
                logger.error(f"Query execution error: {e}")
                raise HTTPException(status_code=400, detail=str(e)[:100])

    # All retries failed
    await record_failure(request)
    logger.error(f"Query failed after {len(retry_delays) + 1} attempts: {last_error}")
    raise HTTPException(status_code=500, detail=f"Database error: {last_error}")
