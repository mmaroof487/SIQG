"""Query execution router with full 6-layer pipeline.

Layer 1: Security (IP filtering, auth, validation, rate limits, RBAC, honeypot)
Layer 2: Performance (fingerprinting, cache, cost estimation, auto-limit, budget)
Layer 3: Execution (circuit breaker, routing, timeout, retry logic)
Layer 4: Observability (audit logging, metrics, slow query detection)
Layer 5: Hardening (AES-256-GCM encryption, DLP masking)
Layer 6: AI Intelligence (NL→SQL, query explanation)
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, Any, List, Dict
import uuid
import asyncpg
import asyncio
import time
import json
from config import settings
from middleware.security.auth import get_current_user, validate_api_key_scope
from middleware.security.ip_filter import check_ip_filter
from middleware.security.validator import validate_query
from middleware.security.rate_limiter import check_rate_limit
from middleware.security.rbac import check_rbac, apply_rbac_masking, check_time_based_access
from middleware.security.encryption import encrypt_query_values, decrypt_rows, encrypt_value, decrypt_value
from middleware.performance.fingerprinter import fingerprint_query, extract_tables_from_query
from middleware.performance.cache import check_cache, write_cache, invalidate_table_cache
from middleware.performance.cost_estimator import estimate_query_cost
from middleware.performance.auto_limit import inject_limit_clause
from middleware.performance.budget import check_budget, deduct_budget
from middleware.performance.complexity import score_complexity
from middleware.observability.metrics import increment, record_latency
from middleware.observability.heatmap import record_table_access
from middleware.observability.webhooks import send_alert
from middleware.execution.analyzer import run_explain_analyze, generate_index_suggestions, log_slow_query, build_query_recommendation
from middleware.execution.executor import execute_with_timeout
from middleware.observability.audit import write_audit_log
from utils.honeypot import check_honeypot
from models import AuditLog
from utils.db import PrimarySession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/query", tags=["queries"])
logger = get_logger(__name__)


class QueryRequest(BaseModel):
    query: str
    dry_run: bool = False  # If true, validate and estimate cost, but don't execute
    connection_id: Optional[str] = None  # External DB connection ID (Phase B)


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
    analysis: Optional[Dict[str, Any]] = None


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

    request_start_time = time.time()

    query_type = "UNKNOWN"
    is_select = False
    cost = None
    recommended_index = None
    cached_result = False

    # Phase B: external connection state
    external_conn = None
    encrypted_cols = settings.encrypt_columns_list  # default: env config
    allow_ddl = False  # DDL blocked by default on internal connection
    conn_scope = "default"  # used in cache key to isolate per-connection caches

    logger.info(f"[{trace_id}] Query: {payload.query[:100]}")
    clean_query = payload.query

    # Record total requests (fire-and-forget)
    asyncio.create_task(increment(request, "requests_total"))

    # Variables referenced in except/finally blocks must be declared here
    fingerprint = ""
    affected_tables = ()

    try:
        # === MULTI-DATABASE ROUTING (Phase B) ===
        # If connection_id present, route to user's external DB
        if payload.connection_id:
            from utils.connection_manager import get_user_database, get_connection_encrypted_columns
            conn_scope = payload.connection_id
            async with PrimarySession() as db:
                user_db = await get_user_database(
                    session=db,
                    connection_id=payload.connection_id,
                    user_id=str(request.state.user_id),
                )
            if not user_db or not user_db.is_active:
                raise HTTPException(status_code=404, detail="Connection not found")

            # Decrypt connection string and open external asyncpg connection
            conn_str = decrypt_value(user_db.conn_str_enc)
            try:
                external_conn = await asyncio.wait_for(
                    asyncpg.connect(conn_str), timeout=10
                )
            except Exception as conn_err:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "External connection failed", "detail": str(conn_err)},
                )

            # Fetch per-connection encrypted column list
            # (rough table name extraction from query)
            _tables_hint = extract_tables_from_query(payload.query)
            _table_hint = _tables_hint[0] if _tables_hint else ""
            async with PrimarySession() as db:
                encrypted_cols = await get_connection_encrypted_columns(
                    db, payload.connection_id, _table_hint
                )

            # DDL allowed on user-owned external connections
            allow_ddl = True
            logger.info(f"[{trace_id}] Routing to external connection {payload.connection_id}")

        # === LAYER 1: SECURITY ===
        # Check IP filter first (before auth)
        await check_ip_filter(request)
        logger.debug(f"[{trace_id}] ✅ IP filter check passed")

        # Validate query for SQL injection, dangerous operations
        # Gap fix #1: capture and use the cleaned/validated query
        clean_query = await validate_query(payload.query, allow_ddl=allow_ddl)
        logger.debug(f"[{trace_id}] ✅ Query validation passed")

        # Check honeypot tables BEFORE rate limiting (403 > 429 priority)
        # Honeypot is intrusion detection and should block at perimeter
        await check_honeypot(request, clean_query)
        logger.debug(f"[{trace_id}] ✅ Honeypot check passed")

        # GUARDRAIL: Sensitive field protection (centralized via settings.sensitive_fields)
        # Block explicit references to sensitive fields in queries
        # Allow SELECT * (denied columns will be filtered after execution)
        query_upper = payload.query.strip().upper()
        is_select = query_upper.startswith("SELECT")
        query_lower = payload.query.lower()

        # Check: Does the query explicitly name a sensitive field?
        # (not just in comments, but as actual column reference)
        has_select_star = "SELECT *" in query_upper or "SELECT  *" in query_upper

        if not has_select_star:
            # Query doesn't have SELECT * — check if it explicitly names sensitive fields
            for field in settings.sensitive_fields:
                if field in query_lower:
                    logger.warning(f"[{trace_id}] ⚠️ Sensitive field '{field}' detected in query")
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "blocked": True,
                            "block_reasons": [f"Query references sensitive field: {field}"],
                            "suggested_fix": "Remove the sensitive field from your query. Safe columns: id, username, email, role, is_active, created_at",
                        }
                    )

        logger.debug(f"[{trace_id}] ✅ Sensitive field check passed")

        # Check rate limit (with per-role limits: admin=500, readonly=60, guest=10)
        await check_rate_limit(request, request.state.user_id, request.state.role)
        logger.debug(f"[{trace_id}] ✅ Rate limit check passed ({request.state.role} tier)")

        # Check RBAC permissions
        await check_rbac(request)
        logger.debug(f"[{trace_id}] ✅ RBAC check passed")

        # Check time-based access rules (e.g., readonly only 09:00-17:00)
        await check_time_based_access(request)
        logger.debug(f"[{trace_id}] ✅ Time-based access check passed")

        # === LAYER 2: PERFORMANCE OPTIMIZATIONS ===
        # Determine query type (SELECT, INSERT, etc.)
        is_select = clean_query.strip().upper().startswith("SELECT")
        first_kw = clean_query.strip().split()[0].upper() if clean_query.strip() else "SELECT"
        query_type = first_kw if first_kw else "SELECT"

        # Generate query fingerprint (normalized hash)
        fingerprint = fingerprint_query(clean_query)
        affected_tables = extract_tables_from_query(clean_query)
        logger.debug(f"[{trace_id}] Fingerprint: {fingerprint[:8]}... Tables: {affected_tables}")

        # Check API key scoping restrictions (if authenticated with API key)
        await validate_api_key_scope(request, clean_query, affected_tables)
        logger.debug(f"[{trace_id}] ✅ API key scope check passed")

        # Check query whitelist mode (if enabled, only approved fingerprints execute)
        if settings.whitelist_mode_enabled:
            redis = request.app.state.redis
            whitelist_key = f"argus:whitelist:{fingerprint}"

            # Check Redis cache first (fast path)
            is_whitelisted = await redis.exists(whitelist_key)

            if not is_whitelisted:
                # Fall back to database check
                try:
                    from models import QueryWhitelist
                    from sqlalchemy import select

                    async with PrimarySession() as session:
                        stmt = select(QueryWhitelist).where(QueryWhitelist.query_fingerprint == fingerprint)
                        result = await session.execute(stmt)
                        whitelist_record = result.scalars().first()

                        if whitelist_record:
                            # Cache the whitelist status
                            await redis.setex(whitelist_key, 86400, "1")  # Cache for 24h
                            is_whitelisted = True
                except Exception as e:
                    logger.warning(f"Whitelist check error: {e}")

            if not is_whitelisted:
                logger.warning(f"[{trace_id}] ❌ Query blocked by whitelist mode")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "blocked": True,
                        "block_reasons": ["Query fingerprint not in whitelist. System is in locked mode."],
                        "suggested_fix": f"Fingerprint: {fingerprint}. Contact admin to approve this query pattern.",
                    }
                )

        logger.debug(f"[{trace_id}] ✅ Whitelist check passed")

        # **Cache Check** - For SELECT queries, check cache first
        # Cache key includes conn_scope to isolate per-connection caches (Phase B Gap Fix)
        if is_select:
            cached_data = await check_cache(
                request,
                clean_query,
                request.state.role,
                conn_scope=conn_scope,
            )
            if cached_data is not None:
                logger.info(f"[{trace_id}] ✅ Cache HIT - returning cached result")
                # Record cache hit metric
                await increment(request, "cache_hits")
                # Pull analysis metadata directly from cache to completely avoid DB hits
                cached_analysis = cached_data.get("analysis", {})
                return QueryResult(
                    trace_id=trace_id,
                    query_type=query_type,
                    rows=cached_data.get("rows", []),
                    rows_count=cached_data.get("rows_count", 0),
                    latency_ms=(time.time() - request_start_time) * 1000,
                    cached=True,
                    slow=False,
                    cost=cached_data.get("cost", 0),
                    analysis={
                        "scan_type": cached_analysis.get("scan_type", "Unknown"),
                        "execution_time_ms": cached_analysis.get("execution_time_ms", 0.0),
                        "rows_processed": cached_analysis.get("rows_processed", 0),
                        "total_cost": cached_analysis.get("total_cost", cost if cost is not None else 0.0),
                        "slow_query": False,
                        "index_suggestions": cached_analysis.get("index_suggestions", []),
                        "complexity": score_complexity(clean_query),
                        "recommendation": cached_analysis.get("recommendation", "✅ Query is cached."),
                    },
                )

        # Record cache miss if it is a SELECT query
        if is_select:
            await increment(request, "cache_misses")

        # **Cost Estimation** - EXPLAIN before execution (skip for external connections — no EXPLAIN on arbitrary DBs)
        if not external_conn:
            cost, cost_warning = await estimate_query_cost(
                request,
                clean_query,
                is_select=is_select
            )
        else:
            cost, cost_warning = (0.0, False)
        logger.debug(f"[{trace_id}] Cost estimate: {cost:.2f}")

        if cost_warning:
            logger.warning(f"[{trace_id}] ⚠️ High cost query: {cost:.2f}")

        # Gap fix #2: enforce cost_threshold_block for non-admin users
        role = getattr(request.state, "role", "guest")
        if is_select and cost > settings.cost_threshold_block and role != "admin":
            logger.warning(f"[{trace_id}] ❌ Query cost {cost:.2f} exceeds block threshold {settings.cost_threshold_block}")
            raise HTTPException(
                status_code=400,
                detail={
                    "blocked": True,
                    "block_reasons": [f"Query estimated cost ({cost:.0f}) exceeds threshold ({settings.cost_threshold_block})"],
                    "suggested_fix": "Add WHERE clauses or indexes to reduce query cost",
                }
            )

        # **Budget Check** - Ensure user has cost budget remaining
        if is_select:
            await check_budget(request, request.state.user_id, cost)
            logger.debug(f"[{trace_id}] ✅ Budget check passed")

        # **Auto-Limit Injection** - Prevent unbounded SELECT queries
        execution_query = clean_query
        if is_select:
            execution_query = inject_limit_clause(clean_query)
            if execution_query != clean_query:
                logger.debug(f"[{trace_id}] ✅ Injected LIMIT clause")

        # Encrypt configured columns before write execution.
        # For external connections, use per-connection encrypted_cols list.
        if not is_select:
            if external_conn and encrypted_cols:
                # Pass the per-connection column list to encrypt_query_values
                from middleware.security.encryption import encrypt_query_values_for_columns
                execution_query = encrypt_query_values_for_columns(execution_query, encrypted_cols)
            else:
                execution_query = encrypt_query_values(execution_query)

        # === DRY RUN MODE ===
        if payload.dry_run:
            logger.info(f"[{trace_id}] Dry run mode - skipping execution")
            complexity_dict = score_complexity(clean_query)
            return QueryResult(
                trace_id=trace_id,
                query_type=query_type,
                rows=[],  # No actual execution in dry-run
                rows_count=0,
                latency_ms=0,
                cost=cost,
                analysis={
                    "mode": "dry_run",
                    "status": "would_execute",
                    "scan_type": None,
                    "execution_time_ms": 0,
                    "rows_processed": 0,
                    "total_cost": cost if cost is not None else 0.0,
                    "slow_query": False,
                    "complexity": complexity_dict,
                    "index_suggestions": [],
                    "pipeline_checks": {
                        "ip_filter": "pass",
                        "rate_limit": "pass",
                        "injection_check": "pass",
                        "rbac": "pass",
                        "honeypot": "pass",
                    },
                    "query_diff": {
                        "original": clean_query,
                        "would_execute": execution_query if cost > settings.cost_threshold_warn else clean_query,
                    },
                    "message": "No query was executed. All pipeline checks passed.",
                },
            )

        # === LAYER 3: EXECUTION ===
        # Circuit breaker and retry logic handled inside execute_with_timeout
        start_time = time.time()
        rows_dict = []

        if external_conn:
            # Execute directly on external asyncpg connection
            # Circuit breaker uses per-connection key for external connections
            cb_key = f"argus:circuit:{payload.connection_id}"
            try:
                if is_select:
                    raw_rows = await external_conn.fetch(execution_query)
                    rows_dict = [dict(row) for row in raw_rows]
                    # Decrypt encrypted columns using per-connection config
                    if encrypted_cols:
                        from middleware.security.encryption import decrypt_rows_for_columns
                        rows_dict = decrypt_rows_for_columns(rows_dict, encrypted_cols)
                else:
                    await external_conn.execute(execution_query)
                    rows_dict = []
            except Exception as ext_err:
                raise HTTPException(status_code=400, detail=str(ext_err)[:200])
        else:
            rows, _ = await execute_with_timeout(request, execution_query)
            if is_select:
                rows_dict = [dict(row._mapping) for row in rows]
                # Decrypt first, then apply RBAC masking.
                rows_dict = decrypt_rows(rows_dict)

        # Measure full end-to-end turnaround latency for API metrics
        latency_ms = (time.time() - request_start_time) * 1000

        logger.debug(f"[{trace_id}] ✅ Query executed in {latency_ms:.1f}ms")

        # **Cache Invalidation** - For INSERT/UPDATE/DELETE, invalidate affected tables
        # Fire-and-forget: don't block the response waiting for cache cleanup
        if not is_select and affected_tables:
            asyncio.create_task(invalidate_table_cache(request, affected_tables))
            # Also invalidate connection-scoped cache keys for external connections
            if payload.connection_id:
                from utils.connection_manager import invalidate_connection_cache
                asyncio.create_task(invalidate_connection_cache(request.app.state.redis, payload.connection_id))
            logger.debug(f"[{trace_id}] ✅ Cache invalidation scheduled for tables: {affected_tables}")

        # **RBAC Result Masking** - Apply PII masking to results based on role
        if is_select and rows_dict:
            rows_dict = apply_rbac_masking(request.state.role, rows_dict)
            logger.debug(f"[{trace_id}] ✅ PII masking applied")

        # **Deduct Budget** - For SELECT queries, deduct cost from budget
        if is_select:
            await deduct_budget(request, request.state.user_id, cost)

        # === LAYER 4: OBSERVABILITY + INTELLIGENCE ===
        explain_result = {}
        suggestions = []
        complexity_dict = score_complexity(clean_query)
        complexity = complexity_dict.get("score", 0)  # Extract numeric score for recommendations

        if is_select:
            try:
                async with PrimarySession() as analysis_db:
                    analysis_conn = await analysis_db.connection()
                    raw = await analysis_conn.get_raw_connection()
                    explain_result = await run_explain_analyze(raw.driver_connection, execution_query)
            except Exception as e:
                logger.warning(f"[{trace_id}] EXPLAIN ANALYZE failed: {e}")
                explain_result = {"error": str(e)}

            suggestions = generate_index_suggestions(explain_result, clean_query)
            explain_result["index_suggestions"] = suggestions

        # Determine if slow query (Phase 3: based on execution analysis time)
        analyzed_time = explain_result.get("execution_time_ms", 0) if is_select else latency_ms
        is_slow = analyzed_time > settings.slow_query_threshold_ms

        if is_select and is_slow:
            asyncio.create_task(increment(request, "slow_queries"))
            # Gap fix #6: send_alert fire-and-forget
            asyncio.create_task(send_alert(
                event_type="slow_query",
                trace_id=trace_id,
                user_id=str(request.state.user_id),
                message=f"Query exceeded slow threshold. Latency: {analyzed_time}ms",
                extra={"query": clean_query[:200]}
            ))
            async with PrimarySession() as session:
                await log_slow_query(
                    session,
                    trace_id=trace_id,
                    user_id=request.state.user_id,
                    fingerprint=fingerprint,
                    analysis=explain_result,
                )

        if getattr(request.state, "anomaly_flag", False):
            # Gap fix #6: send_alert fire-and-forget
            asyncio.create_task(send_alert(
                event_type="anomaly",
                trace_id=trace_id,
                user_id=str(request.state.user_id),
                message="Anomaly flag triggered for request spike",
                extra={"query": clean_query[:50]}
            ))

        # Log to audit log (fire-and-forget via asyncio task)
        asyncio.create_task(write_audit_log(
            trace_id=trace_id,
            user_id=request.state.user_id,
            role=request.state.role,
            fingerprint=fingerprint,
            query_type=query_type,
            latency_ms=latency_ms,
            status="success",
            cached=cached_result,
            slow=is_slow,
            anomaly_flag=getattr(request.state, "anomaly_flag", False),
            connection_id=payload.connection_id,
        ))
        logger.debug(f"[{trace_id}] ✅ Audit log scheduled")

        # Cache store - Store results in cache for future queries (with table tags)
        if is_select and not is_slow:
            cache_data = {
                "rows": rows_dict,
                "rows_count": len(rows_dict),
                "latency_ms": latency_ms,
                "cost": cost,
                "analysis": {
                    "scan_type": explain_result.get("scan_type", "Unknown"),
                    "execution_time_ms": explain_result.get("execution_time_ms", 0.0),
                    "rows_processed": explain_result.get("rows_processed", 0),
                    "total_cost": explain_result.get("total_cost", cost if cost is not None else 0.0),
                    "index_suggestions": suggestions,
                    "recommendation": build_query_recommendation(
                        clean_query,
                        complexity,
                        explain_result.get("execution_time_ms", latency_ms),
                        {
                            "node_type": explain_result.get("scan_type", "Unknown"),
                            "total_cost": explain_result.get("total_cost", 0),
                            "planning_time": 0,
                            "execution_time": explain_result.get("execution_time_ms", 0),
                            "rows_scanned": explain_result.get("rows_processed", 0),
                            "rows_returned": explain_result.get("rows_processed", 0),
                            "full_plan": explain_result.get("raw_plan"),
                        },
                        settings.slow_query_threshold_ms,
                    ),
                }
            }
            await write_cache(
                request,
                clean_query,
                request.state.role,
                cache_data,
                ttl=settings.cache_default_ttl,
                conn_scope=conn_scope,
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
            analysis={
                "scan_type": explain_result.get("scan_type", "Unknown"),
                "execution_time_ms": explain_result.get("execution_time_ms", 0.0),
                "rows_processed": explain_result.get("rows_processed", 0),
                "total_cost": explain_result.get("total_cost", cost if cost is not None else 0.0),
                "slow_query": is_slow,
                "index_suggestions": suggestions,
                "complexity": complexity,
                "recommendation": build_query_recommendation(
                    clean_query,
                    complexity,
                    explain_result.get("execution_time_ms", latency_ms),
                    {
                        "node_type": explain_result.get("scan_type", "Unknown"),
                        "total_cost": explain_result.get("total_cost", 0),
                        "planning_time": 0,
                        "execution_time": explain_result.get("execution_time_ms", 0),
                        "rows_scanned": explain_result.get("rows_processed", 0),
                        "rows_returned": explain_result.get("rows_processed", 0),
                        "full_plan": explain_result.get("raw_plan"),
                    },
                    settings.slow_query_threshold_ms,
                ) if is_select else None,
            } if is_select else None,
        )

    except HTTPException as e:
        status_code = getattr(e, "status_code", 500)
        if status_code == 429:
            # Gap fix #5: fire-and-forget increment
            asyncio.create_task(increment(request, "rate_limit_hits"))
            # Gap fix #6: fire-and-forget send_alert
            asyncio.create_task(send_alert(
                event_type="rate_limit",
                trace_id=trace_id,
                user_id=str(getattr(request.state, "user_id", "Unknown")),
                message="Rate limit exceeded",
            ))
        elif status_code == 403 and "honeypot" in str(getattr(e, "detail", "")).lower():
            asyncio.create_task(send_alert(
                event_type="honeypot_hit",
                trace_id=trace_id,
                user_id=str(getattr(request.state, "user_id", "Unknown")),
                message="Honeypot table accessed",
                extra={"query": clean_query[:200]}
            ))
            asyncio.create_task(increment(request, "errors"))
        else:
            asyncio.create_task(increment(request, "errors"))

        # Gap fix #3: audit log for ALL blocked/rejected queries
        _uid = getattr(request.state, "user_id", "unknown")
        _role = getattr(request.state, "role", "unknown")
        _latency = (time.time() - request_start_time) * 1000
        asyncio.create_task(write_audit_log(
            trace_id=trace_id,
            user_id=_uid,
            role=_role,
            fingerprint=fingerprint or "",
            query_type=query_type,
            latency_ms=_latency,
            status="blocked",
            cached=False,
            slow=False,
            anomaly_flag=getattr(request.state, "anomaly_flag", False),
            error_message=str(getattr(e, "detail", str(e)))[:500],
            connection_id=payload.connection_id,
        ))
        raise
    except Exception as e:
        asyncio.create_task(increment(request, "errors"))
        logger.error(f"[{trace_id}] ❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Final latency and metrics
        latency_ms = (time.time() - request_start_time) * 1000
        await record_latency(request, latency_ms)

        # Close external connection if opened (Phase B)
        if external_conn:
            try:
                await external_conn.close()
            except Exception as close_err:
                logger.warning(f"[{trace_id}] External connection close error: {close_err}")

        # Heatmap updates inside finally to capture all tables extracted
        try:
            if affected_tables:
                for table in affected_tables:
                    await record_table_access(request, table)
        except Exception as heatmap_e:
            logger.warning(f"[{trace_id}] Heatmap recording failed: {heatmap_e}")


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
    budget_key = f"argus:budget:{user_id}:{today.isoformat()}"

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
