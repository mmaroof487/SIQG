"""Auto-LIMIT injection middleware."""
from fastapi import HTTPException
from config import settings
from utils.logger import get_logger
import re

logger = get_logger(__name__)


def inject_limit_clause(query: str, limit: int = None) -> str:
    """
    Inject LIMIT clause if query is SELECT without LIMIT.
    Prevents unbounded queries from consuming excessive resources.

    Args:
        query: SQL query string
        limit: Maximum rows to return (default from settings)

    Returns:
        Modified query with LIMIT clause (if needed)
    """
    if limit is None:
        limit = settings.query_auto_limit  # Default: 1000

    query_upper = query.upper().strip()

    # Only SELECT queries
    if not query_upper.startswith("SELECT"):
        return query

    # Check if already has LIMIT (case-insensitive)
    if re.search(r'\bLIMIT\b', query_upper, re.IGNORECASE):
        return query

    # Inject LIMIT
    modified = f"{query.rstrip(';')} LIMIT {limit}"
    logger.info(f"Auto-LIMIT injected: {limit}")
    return modified


async def check_auto_limit(query: str, request) -> str:
    """Async wrapper for auto-limit injection."""
    from config import settings
    return inject_limit_clause(query, settings.auto_limit_default)
