import pytest
from unittest.mock import AsyncMock, MagicMock
from middleware.execution.circuit_breaker import check_circuit_breaker, record_failure, record_success
from fastapi import HTTPException

@pytest.fixture
def mock_request():
    req = MagicMock()
    req.app.state.redis = AsyncMock()
    return req

@pytest.mark.asyncio
async def test_circuit_breaker_closed(mock_request):
    mock_request.app.state.redis.get.return_value = None
    # Should not raise exception
    await check_circuit_breaker(mock_request)

@pytest.mark.asyncio
async def test_circuit_breaker_open(mock_request):
    mock_request.app.state.redis.get.return_value = b"OPEN"
    with pytest.raises(HTTPException) as exc:
        await check_circuit_breaker(mock_request)
    assert exc.value.status_code == 503

@pytest.mark.asyncio
async def test_record_failure(mock_request):
    mock_request.app.state.redis.incr.return_value = 5 # Simulate hitting threshold
    await record_failure(mock_request)
    # Check if state is forced to OPEN
    mock_request.app.state.redis.setex.assert_called_with("siqg:circuit:state", 30, "OPEN")
