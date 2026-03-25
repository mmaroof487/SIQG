"""Query execution router."""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, Any, List
import uuid
import asyncpg
from middleware.security.auth import get_current_user
from middleware.security.validator import validate_query
from middleware.security.rate_limiter import check_rate_limit
from middleware.security.rbac import check_rbac
from models import AuditLog
from utils.db import PrimarySession, ReplicaSession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/query", tags=["queries"])
logger = get_logger(__name__)


class QueryRequest(BaseModel):
    query: str
    dry_run: bool = False  # If true, validate but don't execute


class QueryResult(BaseModel):
    trace_id: str
    query_type: str
    rows: List[Any]
    rows_count: int
    latency_ms: float
    cached: bool = False
    slow: bool = False


@router.post("/execute", response_model=QueryResult)
async def execute_query(
    request: Request,
    payload: QueryRequest,
    user=Depends(get_current_user),
):
    """
    Execute a query through the full 4-layer pipeline.
    
    Layer 1: Security (done in auth dependency)
    Layer 2: Performance checks (fingerprinting, cache)
    Layer 3: Execution (routing, timeout)
    Layer 4: Observability (audit log, metrics)
    """
    
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    
    logger.info(f"[{trace_id}] Query: {payload.query[:100]}")
    
    try:
        # === LAYER 1: SECURITY ===
        # Validate query
        await validate_query(payload.query)
        
        # Check rate limit
        await check_rate_limit(request, request.state.user_id)
        
        # Check RBAC
        await check_rbac(request)
        
        # === DRY RUN MODE ===
        if payload.dry_run:
            return QueryResult(
                trace_id=trace_id,
                query_type="DRY_RUN",
                rows=[],
                rows_count=0,
                latency_ms=0,
            )
        
        # === LAYER 3: EXECUTION ===
        # For now, simple execution on replica (if SELECT) or primary (if INSERT)
        is_select = payload.query.strip().upper().startswith("SELECT")
        
        # Get connection
        session_class = ReplicaSession if is_select else PrimarySession
        
        import time
        start_time = time.time()
        
        async with session_class() as session:
            # Convert SQLAlchemy text query to raw asyncpg
            if is_select:
                # Use replica
                result = await session.execute(payload.query)
                rows = result.mappings().all()
            else:
                # Use primary
                result = await session.execute(payload.query)
                rows = []
            
            latency_ms = (time.time() - start_time) * 1000
        
        rows_dict = [dict(row) for row in rows] if rows else []
        
        # === LAYER 4: OBSERVABILITY ===
        # Log to audit log
        async with PrimarySession() as session:
            audit = AuditLog(
                trace_id=trace_id,
                user_id=request.state.user_id,
                role=request.state.role,
                query_type="SELECT" if is_select else "INSERT",
                query_fingerprint="",  # To be implemented in Phase 2
                latency_ms=latency_ms,
                status="success",
                cached=False,
                slow=latency_ms > settings.slow_query_threshold_ms,
                anomaly_flag=getattr(request.state, "anomaly_flag", False),
            )
            session.add(audit)
            await session.commit()
        
        logger.info(f"[{trace_id}] Success: {len(rows_dict)} rows in {latency_ms:.1f}ms")
        
        return QueryResult(
            trace_id=trace_id,
            query_type="SELECT" if is_select else "INSERT",
            rows=rows_dict,
            rows_count=len(rows_dict),
            latency_ms=latency_ms,
            slow=latency_ms > settings.slow_query_threshold_ms,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Fix import
from config import settings
