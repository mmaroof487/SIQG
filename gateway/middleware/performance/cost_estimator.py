"""Cost estimation using EXPLAIN."""
from fastapi import Request, HTTPException
from sqlalchemy import text
from config import settings
from utils.logger import get_logger
from utils.db import PrimarySession
import json

logger = get_logger(__name__)


async def estimate_query_cost(request: Request, query: str, is_select: bool = True) -> tuple:
    """
    Run EXPLAIN (without ANALYZE) to estimate cost.
    Returns: (cost_value, warning_flag)
    """
    # Only for SELECT queries
    if not is_select:
        return (0.0, False)

    try:
        async with PrimarySession() as session:
            # Run EXPLAIN (no ANALYZE - doesn't execute the query)
            explain_query = f"EXPLAIN (FORMAT JSON) {query}"
            result = await session.execute(text(explain_query))
            rows = result.fetchall()

            if rows:
                # Parse the JSON plan
                plan_json = rows[0][0]
                if isinstance(plan_json, str):
                    plan = json.loads(plan_json)
                else:
                    plan = plan_json

                if isinstance(plan, list) and len(plan) > 0:
                    plan_data = plan[0].get("Plan", {})
                    cost = float(plan_data.get("Total Cost", 0))

                    # Check thresholds
                    warning = cost > settings.cost_threshold_warn

                    logger.debug(f"Cost estimate: {cost:.2f} (warning: {warning})")
                    return (cost, warning)
    except Exception as e:
        logger.warning(f"Cost estimation error: {e}")

    return (0.0, False)
