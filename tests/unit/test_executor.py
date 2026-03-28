"""Unit tests for query executor."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from middleware.execution.executor import _first_keyword, get_session_for_query


class TestFirstKeyword:
    def test_select(self):
        assert _first_keyword("SELECT * FROM users") == "SELECT"

    def test_insert(self):
        assert _first_keyword("INSERT INTO users VALUES(1)") == "INSERT"

    def test_with_cte(self):
        assert _first_keyword("WITH cte AS (SELECT 1) SELECT * FROM cte") == "WITH"

    def test_empty_query(self):
        assert _first_keyword("") == ""

    def test_whitespace_prefix(self):
        assert _first_keyword("  SELECT 1") == "SELECT"

    def test_lowercase(self):
        assert _first_keyword("select * from t") == "SELECT"


class TestSessionRouting:
    @patch("middleware.execution.executor.ReplicaSession")
    @patch("middleware.execution.executor.PrimarySession")
    def test_select_goes_to_replica(self, mock_primary, mock_replica):
        request = MagicMock()
        get_session_for_query("SELECT * FROM users", request)
        mock_replica.assert_called_once()
        mock_primary.assert_not_called()

    @patch("middleware.execution.executor.ReplicaSession")
    @patch("middleware.execution.executor.PrimarySession")
    def test_insert_goes_to_primary(self, mock_primary, mock_replica):
        request = MagicMock()
        get_session_for_query("INSERT INTO users VALUES(1)", request)
        mock_primary.assert_called_once()
        mock_replica.assert_not_called()

    @patch("middleware.execution.executor.ReplicaSession")
    @patch("middleware.execution.executor.PrimarySession")
    def test_with_cte_goes_to_primary(self, mock_primary, mock_replica):
        request = MagicMock()
        get_session_for_query("WITH t AS (SELECT 1) SELECT * FROM t", request)
        mock_primary.assert_called_once()
        mock_replica.assert_not_called()

    @patch("middleware.execution.executor.ReplicaSession")
    @patch("middleware.execution.executor.PrimarySession")
    def test_update_goes_to_primary(self, mock_primary, mock_replica):
        request = MagicMock()
        get_session_for_query("UPDATE users SET name = 'x' WHERE id = 1", request)
        mock_primary.assert_called_once()
        mock_replica.assert_not_called()
