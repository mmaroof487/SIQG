"""Redis cache middleware with table-tagged invalidation."""
from fastapi import Request
from typing import Any, Optional
import json
from utils.logger import get_logger
from .fingerprinter import fingerprint_query, extract_tables_from_query

logger = get_logger(__name__)


async def check_cache(
    request: Request,
    query: str,
    role: str,
) -> Optional[Any]:
    """
    Check if query result is in cache.
    Cache key includes: query_fingerprint + role
    """
    redis = request.app.state.redis
    fingerprint = fingerprint_query(query)
    cache_key = f"argus:cache:{fingerprint}:{role}"

    try:
        cached_result = await redis.get(cache_key)
        if cached_result:
            logger.info(f"Cache HIT: {fingerprint[:8]}...")
            result = json.loads(cached_result)
            return result
    except Exception as e:
        logger.warning(f"Cache get error: {e}")

    logger.info(f"Cache MISS: {fingerprint[:8]}...")
    return None


async def write_cache(
    request: Request,
    query: str,
    role: str,
    result: Any,
    ttl: int = None,
):
    """
    Write query result to cache with table-tagged invalidation.
    """
    if ttl is None:
        from config import settings
        ttl = settings.cache_default_ttl

    redis = request.app.state.redis
    fingerprint = fingerprint_query(query)

    # Extract affected tables
    tables = extract_tables_from_query(query)

    # Cache key: argus:cache:{fingerprint}:{role}
    cache_key = f"argus:cache:{fingerprint}:{role}"

    try:
        # Store result
        await redis.setex(
            cache_key,
            ttl,
            json.dumps(result, default=str),
        )

        # Tag cache key with each table for invalidation
        for table in tables:
            tag_key = f"argus:cache_tags:{table}"
            await redis.sadd(tag_key, cache_key)
            # Set TTL on tag key as well
            await redis.expire(tag_key, ttl * 2)  # 2x TTL for cleanup

        logger.info(f"Cache SET: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


async def invalidate_table_cache(
    request: Request,
    table_names: tuple,
):
    """
    Invalidate all cache entries for given tables using SCAN pattern.
    Avoids loading all keys into memory with SMEMBERS on large sets.
    Used after INSERT/UPDATE/DELETE.
    """
    redis = request.app.state.redis

    for table in table_names:
        tag_key = f"argus:cache_tags:{table}"
        try:
            # Use SCAN to efficiently iterate over cache keys without loading all at once
            cursor = 0
            deleted_count = 0

            while True:
                # SSCAN the tag key set with COUNT hint for batching
                cursor, cache_keys = await redis.sscan(tag_key, cursor, count=100)

                if cache_keys:
                    # Delete all cache keys in one pipeline for efficiency
                    for cache_key in cache_keys:
                        await redis.delete(cache_key)
                    deleted_count += len(cache_keys)

                # Continue if cursor is not 0
                if cursor == 0:
                    break

            if deleted_count > 0:
                logger.info(f"Invalidated {deleted_count} cache entries for table '{table}'")

            # Delete the tag key itself
            await redis.delete(tag_key)
        except Exception as e:
            logger.warning(f"Cache invalidation error for '{table}': {e}")
