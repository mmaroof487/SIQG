import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from middleware.performance.cache import check_cache, write_cache

@pytest.fixture
def mock_request():
    req = MagicMock()
    req.app.state.redis = AsyncMock()
    return req

@pytest.mark.asyncio
async def test_cache_miss(mock_request):
    mock_request.app.state.redis.get.return_value = None
    res = await check_cache(mock_request, "SELECT 1", "admin")
    assert res is None

@pytest.mark.asyncio
async def test_cache_hit(mock_request):
    mock_request.app.state.redis.get.return_value = json.dumps({"rows": [1]})
    res = await check_cache(mock_request, "SELECT 1", "admin")
    assert res == {"rows": [1]}

@pytest.mark.asyncio
async def test_write_cache(mock_request):
    await write_cache(mock_request, "SELECT 1", "admin", {"rows": [1]}, ttl=300)
    mock_request.app.state.redis.setex.assert_called_once()
