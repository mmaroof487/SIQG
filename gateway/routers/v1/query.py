"""Query execution router with full 4-layer pipeline.

Layer 1: Security (IP filtering, auth, validation, rate limits, RBAC)
Layer 2: Performance (fingerprinting, cache, cost estimation, auto-limit, budget)
Layer 3: Execution (circuit breaker, routing, timeout, retry logic)
Layer 4: Observability (audit logging, metrics, slow query detection)
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
from sqlalchemy import select, text
import uuid
import asyncpg
import time
import json
from config import settings
from middleware.security.auth import get_current_user
from middleware.security.ip_filter import check_ip_filter
from middleware.security.validator import validate_query
from middleware.security.rate_limiter import check_rate_limit
from middleware.security.rbac import check_rbac, apply_rbac_masking
from middleware.performance.fingerprinter import fingerprint_query, extract_tables_from_query
from middleware.performance.cache import check_cache, write_cache, invalidate_table_cache
from middleware.performance.cost_estimator import estimate_query_cost
from middleware.performance.auto_limit import inject_limit_clause
from middleware.performance.budget import check_budget, deduct_budget
from models import AuditLog
from utils.db import PrimarySession, ReplicaSession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/query", tags=["queries"])
logger = get_logger(__name__)


class QueryRequest(BaseModel):
    query: str
    dry_run: bool = False  # If true, validate and estimate cost, but don't execute


class QueryResult(BaseModel):
    trace_id: str
    query_type: str
    rows: List[Any]
    rows_count: int
    latency_ms: float
    cached: bool = False
    slow: bool = False
    cost: Optional[float] = None
    recommended_index: Optional[str] = None


@router.post("/execute", response_model=QueryResult)
async def execute_query(
    request: Request,
    payload: QueryRequest,
    user=Depends(get_current_user),
):
    """
    Execute a query through the full 4-layer pipeline.

    Phase 2: Performance Optimizations
    - Query fingerprinting for caching
    - Cache checking before execution
    - Cost estimation and budget enforcement
    - Auto-limit injection for unbounded queries
    - Result masking for PII protection
    """

    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    query_type = "UNKNOWN"
    is_select = False
    cost = None
    recommended_index = None
    cached_result = False

    logger.info(f"[{trace_id}] Query: {payload.query[:100]}")

    try:
        # === LAYER 1: SECURITY ===
        # Check IP filter first (before auth)
        await check_ip_filter(request)
        logger.debug(f"[{trace_id}] ✅ IP filter check passed")

        # Validate query for SQL injection, dangerous operations
        await validate_query(payload.query)
        logger.debug(f"[{trace_id}] ✅ Query validation passed")

        # Check rate limit
        await check_rate_limit(request, request.state.user_id)
        logger.debug(f"[{trace_id}] ✅ Rate limit check passed")

        # Check RBAC permissions
        await check_rbac(request)
        logger.debug(f"[{trace_id}] ✅ RBAC check passed")

        # === LAYER 2: PERFORMANCE OPTIMIZATIONS ===
        # Determine query type (SELECT, INSERT, etc.)
        is_select = payload.query.strip().upper().startswith("SELECT")
        query_type = "SELECT" if is_select else "INSERT"

        # Generate query fingerprint (normalized hash)
        fingerprint = fingerprint_query(payload.query)
        affected_tables = extract_tables_from_query(payload.query)
        logger.debug(f"[{trace_id}] Fingerprint: {fingerprint[:8]}... Tables: {affected_tables}")

        # **Cache Check** - For SELECT queries, check cache first
        if is_select:
            cached_data = await check_cache(
                request,
                payload.query,
                str(request.state.user_id),
                request.state.role,
            )
            if cached_data is not None:
                logger.info(f"[{trace_id}] ✅ Cache HIT - returning cached result")
                return QueryResult(
                    trace_id=trace_id,
                    query_type=query_type,
                    rows=cached_data.get("rows", []),
                    rows_count=cached_data.get("rows_count", 0),
                    latency_ms=cached_data.get("latency_ms", 0),
                    cached=True,
                    slow=False,
                    cost=cached_data.get("cost", 0),
                )

        # **Cost Estimation** - EXPLAIN before execution
        cost, cost_warning = await estimate_query_cost(
            request,
            payload.query,
            is_select=is_select
        )
        logger.debug(f"[{trace_id}] Cost estimate: {cost:.2f}")

        if cost_warning:
            logger.warning(f"[{trace_id}] ⚠️ High cost query: {cost:.2f}")

        # **Budget Check** - Ensure user has cost budget remaining
        if is_select:
            await check_budget(request, request.state.user_id, cost)
            logger.debug(f"[{trace_id}] ✅ Budget check passed")

        # **Auto-Limit Injection** - Prevent unbounded queries
        if is_select and cost > settings.cost_threshold_warn:
            payload.query = inject_limit_clause(payload.query)
            logger.debug(f"[{trace_id}] ✅ Injected LIMIT clause")

        # === DRY RUN MODE ===
        if payload.dry_run:
            logger.info(f"[{trace_id}] Dry run mode - skipping execution")
            return QueryResult(
                trace_id=trace_id,
                query_type=query_type,
                rows=[],
                rows_count=0,
                latency_ms=0,
                cost=cost,
            )

        # === LAYER 3: EXECUTION ===
        start_time = time.time()
        rows_dict = []

        # Route to appropriate database (replica for SELECT, primary for writes)
        session_class = ReplicaSession if is_select else PrimarySession

        async with session_class() as session:
            result = await session.execute(text(payload.query))

            if is_select:
                # Fetch results and convert to dicts for JSON serialization
                rows = result.fetchall()
                rows_dict = [dict(row._mapping) for row in rows]
            else:
                # Write operations return nothing
                rows_dict = []

        latency_ms = (time.time() - start_time) * 1000

        logger.debug(f"[{trace_id}] ✅ Query executed in {latency_ms:.1f}ms")

        # **Cache Invalidation** - For INSERT/UPDATE/DELETE, invalidate affected tables
        if not is_select and affected_tables:
            await invalidate_table_cache(request, affected_tables)
            logger.debug(f"[{trace_id}] ✅ Invalidated cache for tables: {affected_tables}")

        # **RBAC Result Masking** - Apply PII masking to results based on role
        if is_select and rows_dict:
            rows_dict = apply_rbac_masking(request.state.role, rows_dict)
            logger.debug(f"[{trace_id}] ✅ PII masking applied")

        # **Deduct Budget** - For SELECT queries, deduct cost from budget
        if is_select:
            await deduct_budget(request, request.state.user_id, cost)

        # === LAYER 4: OBSERVABILITY ===
        # Determine if slow query (exceeds threshold)
        is_slow = latency_ms > settings.slow_query_threshold_ms

        # Log to audit log
        async with PrimarySession() as session:
            audit = AuditLog(
                trace_id=trace_id,
                user_id=request.state.user_id,
                role=request.state.role,
                query_type=query_type,
                query_fingerprint=fingerprint,
                latency_ms=latency_ms,
                status="success",
                cached=cached_result,
                slow=is_slow,
                anomaly_flag=getattr(request.state, "anomaly_flag", False),
            )
            session.add(audit)
            await session.commit()

        # Cache store - Store results in cache for future queries (with table tags)
        if is_select and not is_slow:
            cache_data = {
                "rows": rows_dict,
                "rows_count": len(rows_dict),
                "latency_ms": latency_ms,
                "cost": cost,
            }
            await write_cache(
                request,
                payload.query,
                str(request.state.user_id),
                request.state.role,
                cache_data,
                ttl=settings.cache_default_ttl,
            )

        logger.info(
            f"[{trace_id}] ✅ Success: {len(rows_dict)} rows in {latency_ms:.1f}ms "
            f"(cost: {cost:.2f}, slow: {is_slow})"
        )

        return QueryResult(
            trace_id=trace_id,
            query_type=query_type,
            rows=rows_dict,
            rows_count=len(rows_dict),
            latency_ms=latency_ms,
            cached=False,
            slow=is_slow,
            cost=cost,
            recommended_index=recommended_index,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget")
async def get_budget(request: Request, user=Depends(get_current_user)):
    """
    Get user's daily query budget status.

    Returns:
        - daily_budget: Daily cost limit per user
        - current_usage: Total cost units used today
        - remaining: Cost units left for today
        - resets_at: Time when budget resets (midnight UTC)
    """
    from datetime import datetime, timedelta

    redis = request.app.state.redis
    user_id = str(user.get("sub", request.state.user_id))
    today = datetime.utcnow().date()
    budget_key = f"siqg:budget:{user_id}:{today.isoformat()}"

    # Get current usage
    current_usage = await redis.get(budget_key)
    current_usage = float(current_usage) if current_usage else 0.0

    # Calculate remaining
    daily_budget = settings.daily_budget_default
    remaining = daily_budget - current_usage

    # Calculate reset time (next midnight UTC)
    now = datetime.utcnow()
    tomorrow_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "user_id": user_id,
        "daily_budget": daily_budget,
        "current_usage": current_usage,
        "remaining": max(0, remaining),
        "resets_at": tomorrow_midnight.isoformat() + "Z"
    }
