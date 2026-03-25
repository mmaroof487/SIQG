"""Cost estimation using EXPLAIN."""
from fastapi import Request, HTTPException
from config import settings
from utils.logger import get_logger
from utils.db import PrimarySession
import json

logger = get_logger(__name__)


async def estimate_query_cost(request: Request, query: str) -> dict:
    """
    Run EXPLAIN (without ANALYZE) to estimate cost.
    Returns: {"cost": N, "scan_type": "...", ...}
    """
    # Only for SELECT queries
    query_upper = query.upper().strip()
    if not query_upper.startswith("SELECT"):
        return {"cost": 0, "scan_type": "N/A"}

    try:
        async with PrimarySession() as session:
            # Run EXPLAIN (no ANALYZE - doesn't execute)
            explain_query = f"EXPLAIN (FORMAT JSON) {query}"
            result = await session.execute(explain_query)
            rows = result.fetchall()

            if rows:
                plan = json.loads(rows[0][0]) if isinstance(rows[0][0], str) else rows[0][0]
                if isinstance(plan, list) and len(plan) > 0:
                    plan_data = plan[0].get("Plan", {})
                    cost = plan_data.get("Total Cost", 0)
                    scan_type = plan_data.get("Node Type", "Unknown")
                    return {
                        "cost": cost,
                        "scan_type": scan_type,
                        "rows": plan_data.get("Actual Rows", 0),
                        "plan": plan_data,
                    }
    except Exception as e:
        logger.warning(f"Cost estimation error: {e}")

    return {"cost": 0, "scan_type": "Error"}


async def check_cost_threshold(request: Request, cost_estimate: dict):
    """
    Check if estimated cost exceeds threshold.
    - WARN: threshold_warn
    - BLOCK: threshold_block (unless admin)
    """
    cost = cost_estimate.get("cost", 0)
    role = getattr(request.state, "role", "guest")

    if cost > settings.cost_threshold_warn:
        logger.warning(f"Query cost {cost} exceeds warning threshold {settings.cost_threshold_warn}")
        request.state.cost_warning = True

    if cost > settings.cost_threshold_block and role != "admin":
        logger.warning(f"Query cost {cost} exceeds block threshold {settings.cost_threshold_block}")
        raise HTTPException(
            status_code=400,
            detail=f"Query cost ({cost}) exceeds limit ({settings.cost_threshold_block}). Admin users can bypass this."
        )
