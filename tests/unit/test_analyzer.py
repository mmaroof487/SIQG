"""Unit tests for EXPLAIN ANALYZE parser and index recommendation engine."""
import pytest
from middleware.execution.analyzer import (
    _extract_all_nodes,
    _extract_where_columns,
    generate_index_suggestions,
    recommend_indexes,
)


class TestExtractAllNodes:
    def test_empty_plan(self):
        assert _extract_all_nodes({}) == [{}]

    def test_none_plan(self):
        assert _extract_all_nodes(None) == []

    def test_flat_plan(self):
        plan = {"Node Type": "Seq Scan", "Relation Name": "users"}
        nodes = _extract_all_nodes(plan)
        assert len(nodes) == 1
        assert nodes[0]["Node Type"] == "Seq Scan"

    def test_nested_plan(self):
        plan = {
            "Node Type": "Hash Join",
            "Plans": [
                {"Node Type": "Seq Scan", "Relation Name": "orders"},
                {"Node Type": "Index Scan", "Relation Name": "users"},
            ],
        }
        nodes = _extract_all_nodes(plan)
        assert len(nodes) == 3
        node_types = [n.get("Node Type") for n in nodes]
        assert "Hash Join" in node_types
        assert "Seq Scan" in node_types
        assert "Index Scan" in node_types


class TestExtractWhereColumns:
    def test_simple_where(self):
        cols = _extract_where_columns("SELECT * FROM users WHERE id = 1")
        assert "id" in cols

    def test_multiple_columns(self):
        cols = _extract_where_columns(
            "SELECT * FROM users WHERE id = 1 AND name LIKE 'foo%'"
        )
        assert "id" in cols
        assert "name" in cols

    def test_no_where(self):
        cols = _extract_where_columns("SELECT * FROM users")
        assert cols == []

    def test_where_with_limit(self):
        cols = _extract_where_columns(
            "SELECT * FROM users WHERE status = 'active' LIMIT 10"
        )
        assert "status" in cols


class TestGenerateIndexSuggestions:
    def test_seq_scan_with_where_match(self):
        explain = {
            "seq_scans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "users",
                    "Filter": "(status = 'active')",
                }
            ]
        }
        query = "SELECT * FROM users WHERE status = 'active'"
        suggestions = generate_index_suggestions(explain, query)
        assert len(suggestions) == 1
        assert suggestions[0]["table"] == "users"
        assert suggestions[0]["column"] == "status"
        assert "CREATE INDEX" in suggestions[0]["ddl"]

    def test_no_suggestions_for_index_scan(self):
        explain = {"seq_scans": []}
        query = "SELECT * FROM users WHERE id = 1"
        suggestions = generate_index_suggestions(explain, query)
        assert suggestions == []

    def test_deduplication(self):
        explain = {
            "seq_scans": [
                {"Node Type": "Seq Scan", "Relation Name": "users", "Filter": "(id = 1)"},
                {"Node Type": "Seq Scan", "Relation Name": "users", "Filter": "(id = 2)"},
            ]
        }
        query = "SELECT * FROM users WHERE id = 1"
        suggestions = generate_index_suggestions(explain, query)
        assert len(suggestions) == 1  # Deduped


class TestRecommendIndexesWrapper:
    def test_handles_list_full_plan(self):
        """recommend_indexes should handle full_plan as a list (EXPLAIN JSON format)."""
        plan = {
            "full_plan": [
                {
                    "Plan": {
                        "Node Type": "Seq Scan",
                        "Relation Name": "orders",
                        "Filter": "(user_id = 5)",
                    }
                }
            ]
        }
        query = "SELECT * FROM orders WHERE user_id = 5"
        suggestions = recommend_indexes(query, plan)
        assert len(suggestions) >= 1
        assert suggestions[0]["table"] == "orders"

    def test_handles_empty_plan(self):
        plan = {"full_plan": None}
        suggestions = recommend_indexes("SELECT 1", plan)
        assert suggestions == []
