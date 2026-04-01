"""Audit logger - immutable insert-only log with retry mechanism."""
import asyncio
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from models import AuditLog
from utils.db import PrimarySession
from utils.logger import get_logger

logger = get_logger(__name__)

# Max retries for transient failures (network, timeouts)
AUDIT_MAX_RETRIES = 3
AUDIT_RETRY_DELAY = 0.1  # seconds


async def write_audit_log(
    trace_id: str,
    user_id: str,
    role: str,
    fingerprint: str,
    query_type: str,
    latency_ms: float,
    status: str,
    cached: bool,
    slow: bool,
    anomaly_flag: bool,
    error_message: str = None,
):
    """Fire-and-forget audit log insertion with exponential backoff retry.

    DESIGN DECISION:
    - Fire-and-forget (asyncio.create_task) to not block query execution
    - Exponential backoff retry (3 attempts) for transient failures
    - Logs only on final failure (not at every retry)
    - Interview note: Best-effort delivery, not guaranteed like a queue
    """

    async def _do_write_with_retry():
        for attempt in range(AUDIT_MAX_RETRIES):
            try:
                async with PrimarySession() as db:
                    log = AuditLog(
                        trace_id=trace_id,
                        user_id=user_id,
                        role=role,
                        query_fingerprint=fingerprint,
                        query_type=query_type,
                        latency_ms=latency_ms,
                        status=status,
                        cached=cached,
                        slow=slow,
                        anomaly_flag=anomaly_flag,
                        error_message=error_message,
                    )
                    db.add(log)
                    await db.commit()
                # Success — log it at debug level only
                logger.debug(f"Audit log written (trace={trace_id}, attempt={attempt+1})")
                return
            except Exception as e:
                is_last = (attempt == AUDIT_MAX_RETRIES - 1)
                if is_last:
                    # Final failure — log as WARNING so it's visible
                    logger.warning(
                        f"Audit log write failed after {AUDIT_MAX_RETRIES} attempts (trace={trace_id}): {type(e).__name__}: {e}"
                    )
                    # Record failure with timestamp for diagnostics
                    logger.error(
                        f"AUDIT_FAILURE | trace_id={trace_id} | user_id={user_id} | timestamp={datetime.utcnow().isoformat()}"
                    )
                else:
                    # Transient failure — retry with exponential backoff
                    delay = AUDIT_RETRY_DELAY * (2 ** attempt)
                    logger.debug(f"Audit log write failed (attempt {attempt+1}/{AUDIT_MAX_RETRIES}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)

    # Fire-and-forget task — don't await in the critical request path
    # This ensures queries complete fast even if audit logging is slow
    asyncio.create_task(_do_write_with_retry())


async def get_audit_logs(
    user_id: Optional[str] = None,
    limit: int = 100,
) -> list:
    """
    Retrieve audit logs using SQLAlchemy ORM (safe from SQL injection).
    Used for query history; admins can see all, users only their own.
    """
    safe_limit = max(1, min(limit, 500))
    try:
        async with PrimarySession() as session:
            stmt = (
                select(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .limit(safe_limit)
            )
            if user_id:
                stmt = stmt.where(AuditLog.user_id == user_id)

            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "trace_id": r.trace_id,
                    "user_id": str(r.user_id) if r.user_id else None,
                    "role": r.role,
                    "query_fingerprint": r.query_fingerprint,
                    "query_type": r.query_type,
                    "latency_ms": r.latency_ms,
                    "status": r.status,
                    "cached": r.cached,
                    "slow": r.slow,
                    "anomaly_flag": r.anomaly_flag,
                    "error_message": r.error_message,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Audit log query failed: {e}")
        return []
