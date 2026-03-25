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


def fingerprint_query(query: str) -> str:
    """
    Generate a SHA-256 fingerprint of a normalized query.
    Used as cache key.
    """
    normalized = normalize_query(query)
    return hashlib.sha256(normalized.encode()).hexdigest()


def extract_tables_from_query(query: str) -> Tuple[str, ...]:
    """
    Rough extraction of table names from query.
    Used for cache invalidation when tables are written to.
    
    This is a simple regex-based approach. For production, use sqlparse.
    """
    # Find FROM and JOIN clauses
    pattern = r'(?:FROM|JOIN)\s+(\w+)'
    matches = re.findall(pattern, query, re.IGNORECASE)
    return tuple(set(m.lower() for m in matches))
