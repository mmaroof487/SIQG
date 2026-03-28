"""Unit tests for auto-LIMIT injection."""
import pytest
from middleware.performance.auto_limit import inject_limit_clause


def test_inject_limit_on_select_without_limit():
    """SELECT without LIMIT should get LIMIT injected."""
    result = inject_limit_clause("SELECT * FROM users", limit=1000)
    assert "LIMIT 1000" in result


def test_no_inject_when_limit_exists():
    """SELECT with existing LIMIT should not be modified."""
    query = "SELECT * FROM users LIMIT 50"
    result = inject_limit_clause(query, limit=1000)
    assert result == query  # Unchanged


def test_no_inject_on_insert():
    """INSERT queries should never get LIMIT injected."""
    query = "INSERT INTO users (name) VALUES ('test')"
    result = inject_limit_clause(query, limit=1000)
    assert result == query


def test_limit_check_case_insensitive():
    """LIMIT keyword detection should be case-insensitive."""
    query = "SELECT * FROM users limit 25"
    result = inject_limit_clause(query, limit=1000)
    assert result == query  # Already has limit


def test_inject_uses_configurable_limit():
    """Injected LIMIT should use the provided value."""
    result = inject_limit_clause("SELECT * FROM users", limit=500)
    assert "LIMIT 500" in result


def test_semicolon_stripped_before_limit():
    """Trailing semicolon should be removed before appending LIMIT."""
    result = inject_limit_clause("SELECT * FROM users;", limit=1000)
    assert result.endswith("LIMIT 1000")
    assert not result.endswith(";LIMIT 1000")


def test_preserves_where_clause():
    """Complex queries with WHERE should still get LIMIT injected correctly."""
    query = "SELECT id, name FROM users WHERE active = true ORDER BY name"
    result = inject_limit_clause(query, limit=100)
    assert result.endswith("LIMIT 100")
    assert "WHERE active = true" in result
