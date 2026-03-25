"""EXPLAIN ANALYZE parser and index recommendation engine."""
from utils.logger import get_logger
from utils.db import PrimarySession
import json
import re

logger = get_logger(__name__)


async def analyze_query_plan(query: str) -> dict:
    """
    Run EXPLAIN ANALYZE post-execution to analyze actual execution plan.
    Returns: plan analysis with recommendations.
    """
    query_upper = query.upper().strip()
    if not query_upper.startswith("SELECT"):
        return {}

    try:
        async with PrimarySession() as session:
            explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE) {query}"
            result = await session.execute(explain_query)
            rows = result.fetchall()

            if rows:
                plan = json.loads(rows[0][0]) if isinstance(rows[0][0], str) else rows[0][0]
                if isinstance(plan, list) and len(plan) > 0:
                    plan_data = plan[0].get("Plan", {})
                    return {
                        "node_type": plan_data.get("Node Type", "Unknown"),
                        "total_cost": plan_data.get("Total Cost", 0),
                        "planning_time": plan[0].get("Planning Time", 0),
                        "execution_time": plan[0].get("Execution Time", 0),
                        "rows_scanned": plan_data.get("Actual Rows", 0),
                        "rows_returned": plan_data.get("Actual Rows", 0),
                        "full_plan": plan_data,
                    }
    except Exception as e:
        logger.warning(f"EXPLAIN ANALYZE error: {e}")

    return {}


def recommend_indexes(query: str, plan: dict) -> list:
    """
    Suggest indexes based on EXPLAIN plan.
    Rule-based engine:
    - Seq Scan on column used in WHERE → suggest index on that column
    - Multiple Seq Scans → suggest composite index
    """
    recommendations = []
    
    node_type = plan.get("node_type", "")
    
    # Rule 1: Seq Scan + WHERE clause → suggest index
    if "Seq Scan" in node_type:
        # Try to extract table name from query
        table_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if table_match:
            table = table_match.group(1)
            
            # Try to find WHERE columns
            where_match = re.search(r'WHERE\s+(.*?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE)
            if where_match:
                where_clause = where_match.group(1)
                # Extract column names (rough heuristic)
                columns = re.findall(r'\b(\w+)\s*[=<>]', where_clause)
                for col in columns[:1]:  # Just first column for simplicity
                    ddl = f"CREATE INDEX idx_{table}_{col} ON {table}({col});"
                    recommendations.append({
                        "type": "index",
                        "reason": f"Seq Scan on {col} in WHERE clause",
                        "ddl": ddl,
                        "estimated_improvement": "Could reduce scan from Seq Scan to Index Scan"
                    })
    
    return recommendations
