"""Query complexity scoring helpers."""


def score_complexity(query: str) -> dict:
    score = 0
    reasons = []
    query_upper = query.upper()

    join_count = query_upper.count(" JOIN ")
    if join_count > 0:
        points = join_count * 2
        score += points
        reasons.append(f"{join_count} JOIN(s) (+{points})")

    # Count nested SELECTs by subtracting the first query SELECT.
    total_selects = query_upper.count("SELECT")
    subquery_count = max(total_selects - 1, 0)
    if subquery_count > 0:
        points = subquery_count * 3
        score += points
        reasons.append(f"{subquery_count} subquery(s) (+{points})")

    if "SELECT *" in query_upper:
        score += 1
        reasons.append("SELECT * used (+1)")

    has_where = "WHERE" in query_upper
    if not has_where and "FROM" in query_upper:
        score += 2
        reasons.append("No WHERE clause - full table scan risk (+2)")

    level = "low" if score <= 2 else "medium" if score <= 6 else "high"

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
    }

