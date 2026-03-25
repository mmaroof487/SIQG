"""Auto-LIMIT injection middleware."""
from fastapi import HTTPException
from utils.logger import get_logger
import re

logger = get_logger(__name__)


def inject_auto_limit(query: str, default_limit: int) -> tuple[str, bool]:
    """
    Inject LIMIT clause if query is SELECT without LIMIT.
    
    Returns: (query, was_modified)
    """
    query_upper = query.upper().strip()

    # Only SELECT queries
    if not query_upper.startswith("SELECT"):
        return query, False

    # Check if already has LIMIT
    if re.search(r'\bLIMIT\b', query_upper):
        return query, False

    # Inject LIMIT
    modified = f"{query.rstrip(';')} LIMIT {default_limit}"
    logger.info(f"Auto-LIMIT injected: {default_limit}")
    return modified, True


async def check_auto_limit(query: str, request) -> tuple[str, bool]:
    """Async wrapper for auto-limit injection."""
    from config import settings
    return inject_auto_limit(query, settings.auto_limit_default)
