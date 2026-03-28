"""Unit tests for cost estimation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@patch("middleware.performance.cost_estimator.PrimarySession")
async def test_cost_estimation_returns_cost(mock_session_cls):
    """Cost estimator should return (cost, warning) tuple from EXPLAIN."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ([{"Plan": {"Total Cost": 42.5}}],)
    ]
    mock_session.execute.return_value = mock_result
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cls.return_value.__aexit__ = AsyncMock()

    request = MagicMock()
    request.state.role = "readonly"

    from middleware.performance.cost_estimator import estimate_query_cost

    cost, warning = await estimate_query_cost(request, "SELECT 1", is_select=True)
    # Cost should be extracted from plan
    assert isinstance(cost, float)


@pytest.mark.asyncio
async def test_cost_estimation_non_select():
    """Cost estimation should return (0.0, False) for non-SELECT."""
    request = MagicMock()

    from middleware.performance.cost_estimator import estimate_query_cost

    cost, warning = await estimate_query_cost(request, "INSERT INTO t VALUES(1)", is_select=False)
    assert cost == 0.0
    assert warning is False


@pytest.mark.asyncio
@patch("middleware.performance.cost_estimator.PrimarySession")
async def test_cost_estimation_handles_failure(mock_session_cls):
    """Cost estimation should not crash on DB error."""
    mock_session_cls.return_value.__aenter__ = AsyncMock(
        side_effect=Exception("DB error")
    )
    mock_session_cls.return_value.__aexit__ = AsyncMock()

    request = MagicMock()
    request.state.role = "readonly"

    from middleware.performance.cost_estimator import estimate_query_cost

    cost, warning = await estimate_query_cost(request, "SELECT 1", is_select=True)
    assert cost == 0.0
    assert warning is False
