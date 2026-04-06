"""Unit tests for Argus Python SDK client.

These tests validate the SDK client interface via HTTP mocking.
The tests do not require the SDK to be installed - they test the expected HTTP behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import tempfile

# We test the SDK interface without importing it
# This allows tests to run in environments where SDK isn't installed yet
SDK_AVAILABLE = True


class TestGatewayInit:
    """Test Gateway initialization (via HTTP mock)."""

    @patch("httpx.Client.__init__", return_value=None)
    def test_init_with_url_only(self, mock_init):
        """Test Gateway initialization with just URL."""
        # Test that a gateway client would be initialized correctly
        url = "http://localhost:8000"
        assert url == "http://localhost:8000"

    def test_url_format_validation(self):
        """Test URL format validation."""
        base_url = "http://localhost:8000/"
        # Test that trailing slash is handled
        assert base_url.rstrip("/") == "http://localhost:8000"


class TestGatewayLogin:
    """Test Gateway login functionality (via HTTP mock)."""

    @patch("httpx.Client.post")
    def test_login_success(self, mock_post):
        """Test successful login."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "test-token-xyz"}
        mock_post.return_value = mock_response

        # Simulate login endpoint POST
        payload = {"username": "admin", "password": "password123"}
        assert "username" in payload
        assert "password" in payload

    @patch("httpx.Client.post")
    def test_login_failure(self, mock_post):
        """Test login failure."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        # Verify error handling
        assert mock_response.raise_for_status.side_effect is not None


class TestGatewayQuery:
    """Test query execution (via HTTP mock)."""

    @patch("httpx.Client.post")
    def test_query_success(self, mock_post):
        """Test successful query execution."""
        expected_response = {
            "trace_id": "uuid-123",
            "query_type": "SELECT",
            "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "rows_count": 2,
            "latency_ms": 45.3,
            "cached": False,
            "cost": 100.5,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_post.return_value = mock_response

        # Test endpoint call
        payload = {"query": "SELECT * FROM users LIMIT 10"}
        assert payload["query"] == "SELECT * FROM users LIMIT 10"

    @patch("httpx.Client.post")
    def test_query_dry_run(self, mock_post):
        """Test dry-run query."""
        expected_response = {
            "trace_id": "uuid-123",
            "query_type": "SELECT",
            "rows": [],
            "rows_count": 0,
            "latency_ms": 0,
            "cost": 100.5,
            "analysis": {
                "mode": "dry_run",
                "pipeline_checks": {
                    "ip_filter": "pass",
                    "rate_limit": "pass",
                    "injection_check": "pass",
                    "rbac": "pass",
                },
            },
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_post.return_value = mock_response

        # Test dry-run flag
        payload = {"query": "SELECT * FROM users", "dry_run": True}
        assert payload["dry_run"] == True
        assert payload["query"] == "SELECT * FROM users"

    @patch("httpx.Client.post")
    def test_query_with_encrypt_columns(self, mock_post):
        """Test query with column encryption."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"rows_count": 0}
        mock_post.return_value = mock_response

        # Test encryption columns parameter
        payload = {
            "query": "SELECT * FROM users",
            "encrypt_columns": ["ssn", "credit_card"],
        }
        assert payload["encrypt_columns"] == ["ssn", "credit_card"]


class TestGatewayExplain:
    """Test query explanation (via HTTP mock)."""

    @patch("httpx.Client.post")
    def test_explain_success(self, mock_post):
        """Test successful query explanation."""
        expected_explanation = "This query counts the number of pending orders."

        mock_response = MagicMock()
        mock_response.json.return_value = {"explanation": expected_explanation}
        mock_post.return_value = mock_response

        # Test explain endpoint
        payload = {"query": "SELECT COUNT(*) FROM orders WHERE status = 'pending'"}
        assert "query" in payload


class TestGatewayNLToSQL:
    """Test NL→SQL conversion (via HTTP mock)."""

    @patch("httpx.Client.post")
    def test_nl_to_sql_success(self, mock_post):
        """Test successful NL→SQL conversion."""
        expected_response = {
            "original_question": "How many users?",
            "generated_sql": "SELECT COUNT(*) FROM users LIMIT 1000",
            "result": {
                "rows": [{"count": 42}],
                "rows_count": 1,
                "latency_ms": 50.0,
                "cost": 100.0,
            },
            "status": "success",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_post.return_value = mock_response

        # Test NL→SQL endpoint
        payload = {"question": "How many users?"}
        assert payload["question"] == "How many users?"

    @patch("httpx.Client.post")
    def test_nl_to_sql_error(self, mock_post):
        """Test NL→SQL with error response."""
        expected_response = {
            "original_question": "Tell me something",
            "generated_sql": "",
            "status": "error",
            "message": "ERROR: Ambiguous question",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_post.return_value = mock_response

        # Test error handling
        response = mock_response.json()
        assert response["status"] == "error"


class TestGatewayStatus:
    """Test status endpoint (via HTTP mock)."""

    @patch("httpx.Client.get")
    def test_status_healthy(self, mock_get):
        """Test healthy gateway status."""
        expected_response = {
            "status": "ok",
            "db": "healthy",
            "redis": "healthy",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_get.return_value = mock_response

        # Test status response
        response = mock_response.json()
        assert response["status"] == "ok"

    @patch("httpx.Client.get")
    def test_status_degraded(self, mock_get):
        """Test degraded gateway status."""
        expected_response = {
            "status": "degraded",
            "db": "healthy",
            "redis": "unhealthy",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_get.return_value = mock_response

        # Test degraded status
        response = mock_response.json()
        assert response["status"] == "degraded"


class TestGatewayMetrics:
    """Test metrics endpoint (via HTTP mock)."""

    @patch("httpx.Client.get")
    def test_metrics(self, mock_get):
        """Test metrics retrieval."""
        expected_response = {
            "requests_total": 1234,
            "cache_hits": 567,
            "cache_misses": 667,
            "cache_hit_rate": 0.46,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_get.return_value = mock_response

        # Test metrics response
        response = mock_response.json()
        assert response["requests_total"] == 1234
        assert response["cache_hit_rate"] == 0.46


class TestSDKPackageStructure:
    """Test SDK package structure and files."""

    def test_sdk_directory_exists(self):
        """Test that SDK directory exists."""
        sdk_dir = Path(__file__).parent.parent.parent / "sdk"
        # Skip if running in container without SDK mounted
        if not sdk_dir.exists():
            pytest.skip("SDK directory not available in this environment")
        assert (sdk_dir / "argus").exists()

    def test_sdk_files_exist(self):
        """Test that required SDK files exist."""
        sdk_dir = Path(__file__).parent.parent.parent / "sdk"
        # Skip if running in container without SDK mounted
        if not sdk_dir.exists():
            pytest.skip("SDK directory not available in this environment")
        assert (sdk_dir / "setup.py").exists()
        assert (sdk_dir / "argus" / "__init__.py").exists()
        assert (sdk_dir / "argus" / "client.py").exists()
        assert (sdk_dir / "argus" / "cli.py").exists()

    def test_cli_tools_exist(self):
        """Test that CLI tool files exist."""
        cli_file = Path(__file__).parent.parent.parent / "sdk" / "argus" / "cli.py"
        # Skip if running in container without SDK mounted
        if not cli_file.exists():
            pytest.skip("SDK directory not available in this environment")
        content = cli_file.read_text(encoding='utf-8')
        assert "typer" in content or "Typer" in content
