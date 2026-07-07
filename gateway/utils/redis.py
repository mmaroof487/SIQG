"""Redis connection utilities."""
import redis.asyncio as aioredis
from config import settings


_redis_instance = None

async def get_redis():
    """Get Redis client instance (singleton)."""
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = await aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_instance
