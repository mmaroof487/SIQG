"""Query validation and SQL injection detection."""
import re
from fastapi import HTTPException
from utils.logger import get_logger

logger = get_logger(__name__)

# SQL injection patterns (regex-based detection)
INJECTION_PATTERNS = [
    r"(?i)(\bOR\b\s+\d+\s*=\s*\d+)",  # OR 1=1
    r"(?i)(\bOR\b\s+'[^']*'\s*=\s*'[^']*')",  # OR 'a'='a'
    r"(?i)(UNION\s+SELECT)",  # UNION SELECT
    r"(?i)(EXEC\s*\()",  # EXEC
    r"(?i)(EXECUTE\s*\()",  # EXECUTE
    r"(?i)(;\s*DROP)",  # ; DROP
    r"(?i)(/\*.*\*/)",  # /* */ comments
    r"(?i)(--\s*)",  # -- comments
]

# Dangerous query types
DANGEROUS_QUERY_TYPES = {"DROP", "DELETE", "TRUNCATE", "ALTER"}


def detect_sql_injection(query: str) -> bool:
    """Detect common SQL injection patterns."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query):
            logger.warning(f"SQL injection detected: {query[:100]}")
            return True
    return False


async def validate_query(query: str):
    """
    Validate query:
    - Check for SQL injection
    - Check query type is allowed
    - Check no dangerous keywords
    """
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=400, detail="Invalid query")

    query = query.strip()

    # Extract query type
    first_word = query.split()[0].upper() if query else ""

    # Check if query type is in dangerous list
    if first_word in DANGEROUS_QUERY_TYPES:
        logger.warning(f"Dangerous query blocked: {first_word}")
        raise HTTPException(
            status_code=400,
            detail=f"Query type not allowed: {first_word}"
        )

    # Check for SQL injection after query type gate.
    if detect_sql_injection(query):
        raise HTTPException(
            status_code=400,
            detail="Potential SQL injection detected"
        )

    # Check for honeypot table access (early attack detection)
    from config import settings
    honeypot_tables = settings.honeypot_tables_list
    query_upper = query.upper()
    for honeypot_table in honeypot_tables:
        if honeypot_table.upper() in query_upper:
            logger.critical(f"HONEYPOT HIT: Attack attempt on table '{honeypot_table}': {query[:100]}")
            raise HTTPException(
                status_code=403,
                detail="Access to this resource is forbidden"
            )

    # Only allow SELECT and INSERT by default
    allowed_types = {"SELECT", "INSERT"}
    if first_word not in allowed_types:
        logger.warning(f"Disallowed query type: {first_word}")
        raise HTTPException(
            status_code=400,
            detail=f"Query type '{first_word}' is not allowed. Only SELECT and INSERT are allowed."
        )
