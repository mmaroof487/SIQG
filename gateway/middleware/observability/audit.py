"""Audit logger - immutable insert-only log."""
from fastapi import Request
from utils.db import PrimarySession
from models import AuditLog
from utils.logger import get_logger
import time

logger = get_logger(__name__)


async def log_audit(
    request: Request,
    trace_id: str,
    query_type: str,
    query_fingerprint: str,
    latency_ms: float,
    status: str,
    cached: bool = False,
    slow: bool = False,
    error_message: str = None,
    execution_plan: dict = None,
):
    """
    Write immutable audit log entry.
    Append-only, never UPDATE or DELETE.
    """
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)

    try:
        async with PrimarySession() as session:
            audit = AuditLog(
                trace_id=trace_id,
                user_id=user_id,
                role=role,
                query_type=query_type,
                query_fingerprint=query_fingerprint,
                latency_ms=latency_ms,
                status=status,
                cached=cached,
                slow=slow,
                anomaly_flag=getattr(request.state, "anomaly_flag", False),
                error_message=error_message,
                execution_plan=execution_plan,
            )
            session.add(audit)
            await session.commit()
            logger.info(f"Audit log: {trace_id} {status} {latency_ms:.1f}ms")
    except Exception as e:
        logger.error(f"Audit log write failed: {e}")


async def get_audit_logs(
    user_id: str = None,
    limit: int = 100,
) -> list:
    """
    Retrieve audit logs.
    Used for query history, admins can see all, users only their own.
    """
    try:
        async with PrimarySession() as session:
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)

            query += f" ORDER BY created_at DESC LIMIT {limit}"

            result = await session.execute(query, params)
            return result.fetchall()
    except Exception as e:
        logger.error(f"Audit log query failed: {e}")
        return []
