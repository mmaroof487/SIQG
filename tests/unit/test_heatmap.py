"""Unit tests for heatmap tracking."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_record_table_access():
    """Table access should increment ZSET score."""
    request = MagicMock()
    redis = AsyncMock()
    request.app.state.redis = redis

    from middleware.observability.heatmap import record_table_access

    await record_table_access(request, "users")
    redis.zincrby.assert_called_once_with("siqg:heatmap:tables", 1, "users")


@pytest.mark.asyncio
async def test_get_heatmap_empty():
    """Heatmap should return empty list when no data."""
    redis = AsyncMock()
    redis.zrevrange.return_value = []

    from middleware.observability.heatmap import get_heatmap

    result = await get_heatmap(redis)
    assert result == []


@pytest.mark.asyncio
async def test_get_heatmap_with_data():
    """Heatmap should return sorted list of table access counts."""
    redis = AsyncMock()
    redis.zrevrange.return_value = [
        ("users", 50.0),
        ("orders", 30.0),
        ("products", 10.0),
    ]

    from middleware.observability.heatmap import get_heatmap

    result = await get_heatmap(redis)
    assert len(result) == 3
    assert result[0] == {"table": "users", "query_count": 50}
    assert result[1] == {"table": "orders", "query_count": 30}
    assert result[2] == {"table": "products", "query_count": 10}
