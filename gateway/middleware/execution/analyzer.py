"""EXPLAIN ANALYZE parser and index recommendation engine."""
import json
import re
from utils.db import PrimarySession
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_explain_analyze(conn, query: str) -> dict:
    """
    Run EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS) and return parsed insights.
    """
    try:
        explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS) {query}"
        result = await conn.fetchval(explain_query)
        plan_data = json.loads(result) if isinstance(result, str) else result

        if not plan_data:
            return {"error": "Empty EXPLAIN result"}

        plan = plan_data[0].get("Plan", {})
        all_nodes = _extract_all_nodes(plan)
        seq_scans = [n for n in all_nodes if n.get("Node Type") == "Seq Scan"]

        return {
            "scan_type": plan.get("Node Type", "Unknown"),
            "execution_time_ms": round(float(plan.get("Actual Total Time", 0)), 3),
            "rows_processed": int(plan.get("Actual Rows", 0)),
            "total_cost": round(float(plan.get("Total Cost", 0)), 2),
            "seq_scans": seq_scans,
            "raw_plan": plan_data,
        }
    except Exception as e:
        logger.warning(f"EXPLAIN ANALYZE error: {e}")
        return {"error": str(e)}


def _extract_all_nodes(plan: dict) -> list:
    if plan is None:
        return []
    nodes = [plan]
    for child in plan.get("Plans", []):
        nodes.extend(_extract_all_nodes(child))
    return nodes


def _extract_where_columns(query: str) -> list:
    where_match = re.search(
        r"WHERE\s+(.+?)(?:ORDER\s+BY|GROUP\s+BY|LIMIT|OFFSET|$)",
        query,
        re.IGNORECASE | re.DOTALL,
    )
    if not where_match:
        return []
    where_clause = where_match.group(1)
    cols = re.findall(r"\b(\w+)\s*(?:=|<|>|LIKE|IN\s*\()", where_clause, re.IGNORECASE)
    return sorted(set(cols))


def generate_index_suggestions(explain_result: dict, original_query: str) -> list:
    suggestions = []
    seq_scans = explain_result.get("seq_scans", [])
    where_cols = _extract_where_columns(original_query)
    seen = set()

    for scan in seq_scans:
        table = scan.get("Relation Name", "")
        if not table:
            continue

        # Fire only when Seq Scan filter references WHERE column.
        filter_text = str(scan.get("Filter", "")).lower()
        scan_cols = {c for c in where_cols if re.search(rf"\b{re.escape(c.lower())}\b", filter_text)}
        for col in sorted(scan_cols):
            key = (table, col)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    "table": table,
                    "column": col,
                    "reason": (
                        f"Seq Scan detected on '{table}'. "
                        f"Column '{col}' appears in WHERE clause."
                    ),
                    "ddl": f"CREATE INDEX idx_{table}_{col} ON {table}({col});",
                    "estimated_improvement": (
                        "Seq Scan -> Index Scan (typically 10-100x faster on large tables)"
                    ),
                }
            )
    return suggestions


async def log_slow_query(db_session, trace_id: str, user_id, fingerprint: str, analysis: dict):
    from models import SlowQuery

    suggestion = ""
    if analysis.get("index_suggestions"):
        suggestion = analysis["index_suggestions"][0].get("ddl", "")

    record = SlowQuery(
        trace_id=trace_id,
        user_id=user_id,
        query_fingerprint=fingerprint,
        latency_ms=analysis.get("execution_time_ms", 0),
        scan_type=analysis.get("scan_type", ""),
        rows_scanned=analysis.get("rows_processed", 0),
        rows_returned=analysis.get("rows_processed", 0),
        recommended_index=suggestion,
        execution_plan=analysis.get("raw_plan"),
    )
    db_session.add(record)
    await db_session.commit()


async def analyze_query_plan(query: str) -> dict:
    """
    Backward-compatible wrapper around run_explain_analyze.
    """
    query_upper = query.upper().strip()
    if not query_upper.startswith("SELECT"):
        return {}

    try:
        async with PrimarySession() as session:
            conn = await session.connection()
            raw = await conn.get_raw_connection()
            explain = await run_explain_analyze(raw.driver_connection, query)
            return {
                "node_type": explain.get("scan_type"),
                "total_cost": explain.get("total_cost", 0),
                "planning_time": 0,
                "execution_time": explain.get("execution_time_ms", 0),
                "rows_scanned": explain.get("rows_processed", 0),
                "rows_returned": explain.get("rows_processed", 0),
                "full_plan": explain.get("raw_plan"),
            }
    except Exception as e:
        logger.warning(f"analyze_query_plan wrapper error: {e}")
    return {}


def recommend_indexes(query: str, plan: dict) -> list:
    """
    Backward-compatible wrapper around generate_index_suggestions.
    Handles full_plan as either a list (from EXPLAIN JSON) or a dict.
    """
    full_plan = plan.get("full_plan")
    root_plan = {}
    if isinstance(full_plan, list) and full_plan:
        root_plan = full_plan[0].get("Plan", {})
    elif isinstance(full_plan, dict):
        root_plan = full_plan

    mapped = {
        "seq_scans": _extract_all_nodes(root_plan) if root_plan else [],
    }
    return generate_index_suggestions(mapped, query)


def build_query_recommendation(
    query: str,
    complexity_score: float,
    execution_time_ms: float,
    plan_analysis: dict,
    slow_threshold_ms: int = 200,
) -> str:
    """
    Merge complexity score, index suggestions, and execution analysis into one
    actionable recommendation string for slow queries.

    Args:
        query: SQL query string
        complexity_score: Numerical complexity (0-100+)
        execution_time_ms: Actual execution time in milliseconds
        plan_analysis: Dict with execution plan, sqans, costs (from analyze_query_plan)
        slow_threshold_ms: Threshold for slow query classification

    Returns:
        Single human-readable recommendation string with actionable fixes
    """
    recommendations = []

    # Complexity-based recommendation
    if complexity_score >= 80:
        recommendations.append(f"⚠️ High query complexity ({complexity_score:.0f}/100). Simplify with JOINs or subqueries.")
    elif complexity_score >= 50:
        recommendations.append(f"⚠️ Moderate query complexity ({complexity_score:.0f}/100). Consider optimization.")

    # Execution time recommendation
    if execution_time_ms > slow_threshold_ms:
        recommendations.append(
            f"⏱️ Query took {execution_time_ms}ms (threshold: {slow_threshold_ms}ms). "
            f"Slow queries may benefit from indexing."
        )

    # Index suggestions from plan analysis
    index_suggestions = recommend_indexes(query, plan_analysis)
    if index_suggestions:
        # Take the first (most impactful) suggestion
        top_suggestion = index_suggestions[0]
        recommendations.append(
            f"📊 {top_suggestion['reason']}. "
            f"Suggested index: {top_suggestion['ddl']}"
        )

    # Seq scan warning
    if plan_analysis.get("node_type") == "Seq Scan":
        recommendations.append(
            "🔍 Full table scan detected. Add indexes on filtered/joined columns."
        )

    # Cost-based warning
    total_cost = plan_analysis.get("total_cost", 0)
    if total_cost > 1000:
        recommendations.append(
            f"💰 Query cost: {total_cost:.0f} (high). "
            f"Consider schema optimization or query restructuring."
        )

    # Join the recommendations
    if not recommendations:
        return "✅ Query is well-optimized. No immediate recommendations."

    return " | ".join(recommendations)
