"""Query fingerprinting for caching."""
import hashlib
import re
from typing import Tuple


def normalize_query(query: str) -> str:
    """
    Normalize a SQL query for fingerprinting.
    - Replace string literals with placeholders
    - Replace numbers with placeholders
    - Normalize whitespace
    - Convert to uppercase for consistent hashing
    """
    # Remove comments
    query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

    # Replace string literals with ?
    query = re.sub(r"'[^']*'", '?', query)
    query = re.sub(r'"[^"]*"', '?', query)

    # Replace numbers with ?
    query = re.sub(r'\d+\.?\d*', '?', query)

    # Normalize whitespace
    query = ' '.join(query.split())

    # Case-insensitive for matching
    return query.upper()


def normalize_for_cache(query: str) -> str:
    """
    Normalize a SQL query for caching without stripping literal parameters.
    - Remove comments
    - Normalize whitespace
    - Convert to uppercase for consistent hashing
    """
    # Remove comments
    query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

    # Normalize whitespace
    query = ' '.join(query.split())

    # Case-insensitive for matching
    return query.upper()


def fingerprint_query(query: str) -> str:
    """
    Generate a SHA-256 fingerprint of a normalized query (with parameters stripped).
    Used for query whitelisting and metrics.
    """
    normalized = normalize_query(query)
    return hashlib.sha256(normalized.encode()).hexdigest()

def fingerprint_cache_key(query: str) -> str:
    """
    Generate a SHA-256 fingerprint of a normalized query (with parameters intact).
    Used as the cache key so queries with different parameters do not collide.
    """
    normalized = normalize_for_cache(query)
    return hashlib.sha256(normalized.encode()).hexdigest()


def extract_tables_from_query(query: str) -> Tuple[str, ...]:
    """
    Robust extraction of table names from query using sqlglot.
    Used for cache invalidation and honeypot checks.
    """
    try:
        import sqlglot
        from sqlglot import exp
        
        parsed = sqlglot.parse_one(query, read="postgres")
        tables = set()
        for table in parsed.find_all(exp.Table):
            if table.name:
                tables.add(table.name.lower())
        return tuple(tables)
    except Exception:
        # Fallback to regex if sqlglot fails
        pattern = r'(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z0-9_]+)'
        matches = re.findall(pattern, query, re.IGNORECASE)
        return tuple(set(m.lower() for m in matches))
