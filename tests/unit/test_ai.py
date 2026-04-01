"""Unit tests for AI endpoints (NL→SQL and Explain)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from routers.v1.ai import nl_to_sql, explain_query, call_llm, NLRequest, ExplainRequest
from config import settings


@pytest.mark.asyncio
async def test_nl_to_sql_success():
    """Test successful NL→SQL conversion."""
    # Mock the LLM response
    with patch("routers.v1.ai.call_llm") as mock_llm, \
         patch("routers.v1.ai.execute_query") as mock_execute:

        mock_llm.return_value = "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '7 days' LIMIT 1000"

        # Mock execute_query response
        mock_result = MagicMock()
        mock_result.rows = [{"count": 42}]
        mock_result.rows_count = 1
        mock_result.latency_ms = 50.5
        mock_result.cached = False
        mock_result.cost = 100.0
        mock_execute.return_value = mock_result

        # Create mock request and user
        request = MagicMock()
        request.state.trace_id = "test-trace-id"
        user = {"user_id": 1}

        body = NLRequest(question="How many users signed up in the last 7 days?")

        result = await nl_to_sql(body, request, user)

        assert result.status == "success"
        assert "SELECT" in result.generated_sql
        assert result.original_question == "How many users signed up in the last 7 days?"


@pytest.mark.asyncio
async def test_nl_to_sql_llm_error():
    """Test NL→SQL when LLM returns error."""
    with patch("routers.v1.ai.call_llm") as mock_llm:
        mock_llm.return_value = "ERROR: Ambiguous question"

        request = MagicMock()
        request.state.trace_id = "test-trace-id"
        user = {"user_id": 1}

        body = NLRequest(question="Tell me something")

        result = await nl_to_sql(body, request, user)

        assert result.status == "error"
        assert "Ambiguous" in result.message


@pytest.mark.asyncio
async def test_explain_query_success():
    """Test successful query explanation."""
    with patch("routers.v1.ai.call_llm") as mock_llm:
        expected_explanation = "This query counts the number of orders that are currently in pending status."
        mock_llm.return_value = expected_explanation

        user = {"user_id": 1}
        body = ExplainRequest(query="SELECT COUNT(*) FROM orders WHERE status = 'pending'")

        result = await explain_query(body, user)

        assert result.query == body.query
        assert result.explanation == expected_explanation


@pytest.mark.asyncio
async def test_call_llm_disabled():
    """Test LLM call when AI is disabled."""
    with patch("routers.v1.ai.settings.ai_enabled", False):
        result = await call_llm("test system", "test user message")
        assert "disabled" in result.lower()


@pytest.mark.asyncio
async def test_call_llm_api_error():
    """Test LLM call with API error."""
    with patch("routers.v1.ai.settings.ai_enabled", True), \
         patch("routers.v1.ai.settings.openai_api_key", "test-key"), \
         patch("routers.v1.ai.httpx.AsyncClient") as mock_client_class:

        # Create a mock async context manager
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Mock the post method to raise an exception
        mock_client.post.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        result = await call_llm("system", "user message")
        assert "ERROR" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_nl_to_sql_with_schema_hint():
    """Test NL→SQL with schema hint."""
    with patch("routers.v1.ai.call_llm") as mock_llm, \
         patch("routers.v1.ai.execute_query") as mock_execute:

        mock_llm.return_value = "SELECT * FROM users WHERE id = 1"

        mock_result = MagicMock()
        mock_result.rows = [{"id": 1, "name": "Alice"}]
        mock_result.rows_count = 1
        mock_result.latency_ms = 25.0
        mock_result.cached = False
        mock_result.cost = 50.0
        mock_execute.return_value = mock_result

        request = MagicMock()
        request.state.trace_id = "test-trace-id"
        user = {"user_id": 1}

        schema_hint = "table users(id, name, email)"
        body = NLRequest(
            question="Find user with id 1",
            schema_hint=schema_hint,
        )

        result = await nl_to_sql(body, request, user)

        # Verify that schema hint was passed to LLM
        call_args = mock_llm.call_args
        assert schema_hint in str(call_args)
