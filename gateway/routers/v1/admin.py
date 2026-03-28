"""Admin management router."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from fastapi.responses import StreamingResponse
import csv
import io
from datetime import datetime

from middleware.security.auth import get_current_user
from middleware.observability.heatmap import get_heatmap
from middleware.observability.metrics import get_live_metrics
from models import Role, SlowQuery, AuditLog
from utils.db import PrimarySession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = get_logger(__name__)


def require_admin(user=Depends(get_current_user)):
    """Check that user is admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class IPRuleRequest(BaseModel):
    ip_address: str
    rule_type: str  # "allow" or "block"
    description: Optional[str] = None


@router.post("/ip-rules")
async def add_ip_rule(
    request: Request,
    payload: IPRuleRequest,
    admin=Depends(require_admin),
):
    """Add IP allow/blocklist rule."""
    if payload.rule_type not in ["allow", "block"]:
        raise HTTPException(status_code=400, detail="rule_type must be 'allow' or 'block'")

    redis = request.app.state.redis

    if payload.rule_type == "allow":
        await redis.sadd("ip:allowlist", payload.ip_address)
    else:
        await redis.sadd("ip:blocklist", payload.ip_address)

    logger.info(f"IP rule added: {payload.ip_address} {payload.rule_type}")

    return {"status": "ok", "message": f"IP {payload.ip_address} added to {payload.rule_type}list"}


@router.delete("/ip-rules/{ip_address}")
async def remove_ip_rule(
    request: Request,
    ip_address: str,
    admin=Depends(require_admin),
):
    """Remove IP rule from both lists."""
    redis = request.app.state.redis

    await redis.srem("ip:allowlist", ip_address)
    await redis.srem("ip:blocklist", ip_address)

    logger.info(f"IP rule removed: {ip_address}")

    return {"status": "ok", "message": f"IP {ip_address} removed from all lists"}


@router.get("/heatmap")
async def table_heatmap(request: Request, user=Depends(require_admin)):
    return await get_heatmap(request.app.state.redis)

@router.get("/audit")
async def audit_log(
    request: Request,
    user=Depends(require_admin),
    limit: int = 50,
    offset: int = 0,
    status: str = None,
):
    safe_limit = max(1, min(limit, 200))
    async with PrimarySession() as session:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(safe_limit)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        result = await session.execute(stmt)
        rows = result.scalars().all()
    
    return [
        {
            "trace_id": r.trace_id,
            "user_id": str(r.user_id) if r.user_id else None,
            "query_type": r.query_type,
            "latency_ms": r.latency_ms,
            "status": r.status,
            "cached": r.cached,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in rows
    ]

@router.get("/audit/export")
async def export_audit(request: Request, user=Depends(require_admin)):
    """Stream audit log as CSV using cursor-based pagination to avoid memory spikes."""
    CHUNK_SIZE = 200
    fieldnames = [
        "trace_id", "user_id", "role", "query_type",
        "latency_ms", "status", "cached", "slow",
        "anomaly_flag", "error_message", "created_at",
    ]

    async def generate():
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        offset = 0
        while True:
            async with PrimarySession() as session:
                result = await session.execute(
                    select(AuditLog)
                    .order_by(AuditLog.created_at.desc())
                    .offset(offset)
                    .limit(CHUNK_SIZE)
                )
                rows = result.scalars().all()

            if not rows:
                break

            for r in rows:
                writer.writerow({
                    "trace_id": r.trace_id,
                    "user_id": str(r.user_id) if r.user_id else "",
                    "role": r.role or "",
                    "query_type": r.query_type or "",
                    "latency_ms": r.latency_ms,
                    "status": r.status or "",
                    "cached": r.cached,
                    "slow": r.slow,
                    "anomaly_flag": r.anomaly_flag,
                    "error_message": r.error_message or "",
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                })
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

            offset += CHUNK_SIZE
            if len(rows) < CHUNK_SIZE:
                break

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )


@router.get("/slow-queries")
async def get_slow_queries(limit: int = 50, admin=Depends(require_admin)):
    """Get latest slow query records."""
    safe_limit = max(1, min(limit, 200))
    async with PrimarySession() as session:
        result = await session.execute(
            select(SlowQuery).order_by(SlowQuery.created_at.desc()).limit(safe_limit)
        )
        rows = result.scalars().all()

    return {
        "count": len(rows),
        "items": [
            {
                "trace_id": r.trace_id,
                "user_id": str(r.user_id) if r.user_id else None,
                "query_fingerprint": r.query_fingerprint,
                "latency_ms": r.latency_ms,
                "scan_type": r.scan_type,
                "rows_scanned": r.rows_scanned,
                "rows_returned": r.rows_returned,
                "recommended_index": r.recommended_index,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }

@router.get("/budget")
async def budget_usage(request: Request, user=Depends(require_admin)):
    redis = request.app.state.redis
    today = datetime.utcnow().date().isoformat()
    # Scan for keys matching siqg:budget:*:{today}
    pattern = f"siqg:budget:*:*{today}*"
    keys = await redis.keys(pattern)
    
    if not keys:
        return {"users": []}
        
    values = await redis.mget(keys)
    budgets = []
    from config import settings
    for key, val in zip(keys, values):
        # key format: siqg:budget:{user_id}:{date}
        parts = key.split(":")
        if len(parts) >= 4:
            user_id = parts[2]
            budgets.append({
                "user_id": user_id,
                "used": float(val or 0),
                "limit": settings.daily_budget_default
            })
            
    return {"users": budgets}
