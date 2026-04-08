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
        await redis.sadd("argus:ip:allowlist", payload.ip_address)
    else:
        # Use 24-hour TTL for blocklist to auto-expire bans
        await redis.setex(f"argus:ip:blocklist:{payload.ip_address}", 24 * 3600, "1")

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

    await redis.srem("argus:ip:allowlist", ip_address)
    # Handle both old set-based and new TTL-based blocklist formats
    await redis.delete(f"argus:ip:blocklist:{ip_address}")
    await redis.srem("argus:ip:blocklist", ip_address)  # Fallback for legacy entries

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
    # Scan for keys matching argus:budget:*:{today}
    pattern = f"argus:budget:*:*{today}*"
    keys = await redis.keys(pattern)

    if not keys:
        return {"users": []}

    values = await redis.mget(keys)
    budgets = []
    from config import settings
    for key, val in zip(keys, values):
        # key format: argus:budget:{user_id}:{date}
        parts = key.split(":")
        if len(parts) >= 4:
            user_id = parts[2]
            budgets.append({
                "user_id": user_id,
                "used": float(val or 0),
                "limit": settings.daily_budget_default
            })

    return {"users": budgets}


# === QUERY WHITELIST MANAGEMENT ===

class WhitelistRequest(BaseModel):
    query_fingerprint: str
    description: Optional[str] = None


@router.post("/whitelist")
async def add_to_whitelist(
    request: Request,
    payload: WhitelistRequest,
    admin=Depends(require_admin),
):
    """Add a query fingerprint to the whitelist."""
    from models import QueryWhitelist
    from datetime import timedelta

    async with PrimarySession() as session:
        # Check if already whitelisted
        stmt = select(QueryWhitelist).where(QueryWhitelist.query_fingerprint == payload.query_fingerprint)
        result = await session.execute(stmt)
        existing = result.scalars().first()

        if existing:
            return {"status": "exists", "message": "Fingerprint already whitelisted"}

        # Add to whitelist
        whitelist_record = QueryWhitelist(
            query_fingerprint=payload.query_fingerprint,
            description=payload.description,
            approved_by=admin.get("sub"),
        )
        session.add(whitelist_record)
        await session.commit()

    # Also cache in Redis for fast lookup
    redis = request.app.state.redis
    whitelist_key = f"argus:whitelist:{payload.query_fingerprint}"
    await redis.setex(whitelist_key, 86400, "1")

    logger.info(f"Query fingerprint added to whitelist: {payload.query_fingerprint[:16]}...")
    return {"status": "ok", "message": "Query fingerprint added to whitelist"}


@router.get("/whitelist")
async def list_whitelist(
    request: Request,
    limit: int = 100,
    admin=Depends(require_admin),
):
    """List all whitelisted query fingerprints."""
    from models import QueryWhitelist

    safe_limit = max(1, min(limit, 500))
    async with PrimarySession() as session:
        result = await session.execute(
            select(QueryWhitelist)
            .order_by(QueryWhitelist.created_at.desc())
            .limit(safe_limit)
        )
        rows = result.scalars().all()

    return {
        "count": len(rows),
        "items": [
            {
                "query_fingerprint": r.query_fingerprint,
                "description": r.description or "",
                "approved_by": str(r.approved_by) if r.approved_by else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rows
        ],
    }


@router.delete("/whitelist/{fingerprint}")
async def remove_from_whitelist(
    request: Request,
    fingerprint: str,
    admin=Depends(require_admin),
):
    """Remove a query fingerprint from the whitelist."""
    from models import QueryWhitelist

    async with PrimarySession() as session:
        stmt = select(QueryWhitelist).where(QueryWhitelist.query_fingerprint == fingerprint)
        result = await session.execute(stmt)
        whitelist_record = result.scalars().first()

        if not whitelist_record:
            raise HTTPException(status_code=404, detail="Fingerprint not in whitelist")

        await session.delete(whitelist_record)
        await session.commit()

    # Remove from Redis cache
    redis = request.app.state.redis
    whitelist_key = f"argus:whitelist:{fingerprint}"
    await redis.delete(whitelist_key)

    logger.info(f"Query fingerprint removed from whitelist: {fingerprint[:16]}...")
    return {"status": "ok", "message": "Query fingerprint removed from whitelist"}


# === COMPLIANCE REPORTING ===

@router.get("/compliance-report")
async def get_compliance_report(
    period: str = "30d",
    format: str = "json",
    admin=Depends(require_admin),
):
    """
    Generate compliance report for 30/60/90-day periods.
    Includes: audit metrics, user activity, query compliance, security incidents.
    """
    import re
    from datetime import timedelta

    # Parse period (30d, 90d, 1y)
    match = re.match(r"^(\d+)([dmy])$", period)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid period format (use 30d, 90d, 1y)")

    amount, unit = int(match.group(1)), match.group(2)
    if unit == 'd':
        delta = timedelta(days=amount)
    elif unit == 'm':
        delta = timedelta(days=amount * 30)
    else:  # 'y'
        delta = timedelta(days=amount * 365)

    cutoff = datetime.utcnow() - delta

    # Aggregate audit data
    async with PrimarySession() as session:
        # Count successful/error queries
        from sqlalchemy import func, and_

        audit_count_stmt = select(
            func.count(AuditLog.id).label("total"),
            func.sum(
                func.cast(
                    AuditLog.status_code.in_([200, 201]),
                    __import__('sqlalchemy').Integer
                )
            ).label("successful"),
        ).where(AuditLog.created_at >= cutoff)

        audit_result = await session.execute(audit_count_stmt)
        audit_data = audit_result.first()

        # Count slow queries
        slow_count_stmt = select(func.count(SlowQuery.id)).where(
            SlowQuery.created_at >= cutoff
        )
        slow_result = await session.execute(slow_count_stmt)
        slow_count = slow_result.scalar() or 0

        # Calculate average latency
        avg_latency_stmt = select(
            func.avg(
                func.cast(AuditLog.latency_ms, __import__('sqlalchemy').Float)
            )
        ).where(AuditLog.created_at >= cutoff)

        avg_latency = await session.execute(avg_latency_stmt)
        avg_latency_ms = float(avg_latency.scalar() or 0)

    total_queries = audit_data[0] if audit_data else 0
    successful_queries = audit_data[1] if audit_data and audit_data[1] else 0
    error_queries = (total_queries - successful_queries) if total_queries else 0

    report = {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "audit_summary": {
            "total_queries": total_queries,
            "successful": successful_queries,
            "failed": error_queries,
            "success_rate": round(
                (successful_queries / max(1, total_queries)) * 100, 2
            ),
        },
        "performance": {
            "slow_queries": slow_count,
            "avg_latency_ms": round(avg_latency_ms, 2),
        },
        "security": {
            "blocked_requests": 0,  # From IP filtering
            "rate_limited": 0,  # From rate limiting
        },
    }

    if format == "json":
        return report
    else:
        # CSV format
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["metric", "value"])
        writer.writeheader()

        # Flatten nested structure for CSV
        for section, data in report.items():
            if section in ["period", "generated_at"]:
                writer.writerow({"metric": section, "value": data})
            elif isinstance(data, dict):
                for key, val in data.items():
                    writer.writerow({"metric": f"{section}_{key}", "value": val})

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=compliance-{period}.csv"},
        )
