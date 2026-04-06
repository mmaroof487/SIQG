"""Query validation and SQL injection detection."""
import re
from fastapi import HTTPException
from utils.logger import get_logger

logger = get_logger(__name__)

# SQL injection patterns (regex-based detection) — 13 patterns
INJECTION_PATTERNS = [
    r"(?i)(\bOR\b\s+\d+\s*=\s*\d+)",  # OR 1=1
    r"(?i)(\bOR\b\s+'[^']*'\s*=\s*'[^']*')",  # OR 'a'='a'
    r"(?i)(UNION\s+SELECT)",  # UNION SELECT
    r"(?i)(EXEC\s*\()",  # EXEC
    r"(?i)(EXECUTE\s*\()",  # EXECUTE
    r"(?i)(;\s*DROP)",  # ; DROP
    r"(?i)(/\*.*\*/)",  # /* */ comments
    r"(?i)(--\s*)",  # -- comments
    r"(?i)(\bSLEEP\s*\()",  # Time-based blind: SLEEP()
    r"(?i)(\bWAITFOR\s+DELAY\b)",  # Time-based blind: WAITFOR DELAY
    r"(?i)(\bBENCHMARK\s*\()",  # Time-based blind: BENCHMARK()
    r"(?i)(\binformation_schema\b)",  # Schema enumeration
    r"(?i)(;\s*SELECT)",  # Stacked queries: ;SELECT
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
    Validate query (executed in this order):
    1. Block dangerous keywords (DROP, DELETE, TRUNCATE, ALTER)
    2. Detect SQL injection patterns (13 regex patterns)
    3. Whitelist allowed query types (SELECT, INSERT only)
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
            detail={
                "blocked": True,
                "block_reasons": [f"Query type '{first_word}' is dangerous and not allowed"],
                "suggested_fix": f"Use SELECT or INSERT instead of {first_word}",
            }
        )

    # Check for SQL injection after query type gate.
    if detect_sql_injection(query):
        raise HTTPException(
            status_code=400,
            detail={
                "blocked": True,
                "block_reasons": ["Potential SQL injection pattern detected"],
                "suggested_fix": "Remove SQL injection patterns (OR 1=1, UNION SELECT, SLEEP, etc.) from your query",
            }
        )

    # Only allow SELECT and INSERT by default
    allowed_types = {"SELECT", "INSERT"}
    if first_word not in allowed_types:
        logger.warning(f"Disallowed query type: {first_word}")
        raise HTTPException(
            status_code=400,
            detail={
                "blocked": True,
                "block_reasons": [f"Query type '{first_word}' is not in the allowed list"],
                "suggested_fix": "Only SELECT and INSERT queries are allowed",
            }
        )


def contains_sensitive_column(sql: str, sensitive_fields: set[str]) -> str | None:
    """
    Check if a SQL query references any sensitive column.
    Returns the field name if found, None otherwise.

    Used for pre-execution blocking and testing.
    """
    lowered = sql.lower()
    for field in sensitive_fields:
        if field in lowered:
            return field
    return None
