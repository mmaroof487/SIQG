"""Redis connection utilities."""
import redis.asyncio as aioredis
from config import settings


async def get_redis():
    """Get Redis client instance."""
    return await aioredis.from_url(settings.redis_url, decode_responses=True)
