"""Unit tests for Phase 3 complexity scoring."""
from middleware.performance.complexity import score_complexity


def test_complexity_low_simple_select():
    result = score_complexity("SELECT id FROM users WHERE id = 1")
    assert result["level"] == "low"
    assert result["score"] <= 2


def test_complexity_medium_join_and_star():
    result = score_complexity("SELECT * FROM users u JOIN roles r ON u.role_id = r.id")
    assert result["score"] >= 3
    assert result["level"] in {"medium", "high"}
    assert any("JOIN" in reason for reason in result["reasons"])


def test_complexity_high_subqueries_no_where():
    query = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 10)"
    result = score_complexity(query)
    assert result["score"] >= 4
    assert result["level"] in {"medium", "high"}
