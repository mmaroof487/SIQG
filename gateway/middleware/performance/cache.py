"""Redis cache middleware with table-tagged invalidation."""
from fastapi import Request
from typing import Any, Optional
import json
from utils.logger import get_logger
from .fingerprinter import fingerprint_query, fingerprint_cache_key, extract_tables_from_query

logger = get_logger(__name__)


async def check_cache(
    request: Request,
    query: str,
    role: str,
    conn_scope: str = "default",
) -> Optional[Any]:
    """
    Check if query result is in cache.
    Cache key includes: conn_scope + query_fingerprint + role
    conn_scope is 'default' for internal queries, or connection_id for external ones.
    """
    redis = request.app.state.redis
    fingerprint = fingerprint_cache_key(query)
    cache_key = f"argus:cache:{conn_scope}:{fingerprint}:{role}"
    meta_key = f"argus:cache_meta:{conn_scope}:{fingerprint}:{role}"

    try:
        cached_result = await redis.get(cache_key)
        if cached_result:
            logger.info(f"Cache HIT: {fingerprint[:8]}...")
            
            # Increment hits in metadata and valuable_caches
            try:
                meta_raw = await redis.get(meta_key)
                if meta_raw:
                    meta = json.loads(meta_raw)
                    meta["hits"] = meta.get("hits", 0) + 1
                    # Keep the same TTL or just overwrite without TTL, but better to use existing
                    await redis.set(meta_key, json.dumps(meta))
                
                # Track most valuable cache entries
                await redis.zincrby("argus:stats:valuable_caches", 1, cache_key)
            except Exception as meta_e:
                logger.warning(f"Failed to update cache metadata: {meta_e}")
                
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
    conn_scope: str = "default",
):
    """
    Write query result to cache with table-tagged invalidation.
    Periodically cleans stale tag references to prevent unbounded tag set growth.
    conn_scope is 'default' for internal queries, or connection_id for external ones.
    """
    if ttl is None:
        from config import settings
        ttl = settings.cache_default_ttl

    redis = request.app.state.redis
    fingerprint = fingerprint_cache_key(query)

    # Extract affected tables
    tables = extract_tables_from_query(query)

    # Cache key: argus:cache:{conn_scope}:{fingerprint}:{role}
    cache_key = f"argus:cache:{conn_scope}:{fingerprint}:{role}"
    meta_key = f"argus:cache_meta:{conn_scope}:{fingerprint}:{role}"

    try:
        # Store result
        await redis.setex(
            cache_key,
            ttl,
            json.dumps(result, default=str),
        )

        # Store metadata alongside
        from datetime import datetime, timezone
        meta_data = {
            "tables": list(tables),
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "hits": 0
        }
        await redis.setex(
            meta_key,
            ttl,
            json.dumps(meta_data),
        )

        # Tag cache key with each table for invalidation
        for table in tables:
            tag_key = f"argus:cache_tags:{conn_scope}:{table}"
            await redis.sadd(tag_key, cache_key)
            # Set TTL on tag key as well
            await redis.expire(tag_key, ttl * 2)  # 2x TTL for cleanup
            
            # Track most cached tables
            await redis.zincrby("argus:stats:cached_tables", 1, table)

            # Periodically clean stale tags: if tag set size > 1000, run cleanup
            # Note: SIZE is O(1) in Redis, so safe to call frequently
            try:
                tag_size = await redis.scard(tag_key)
                if tag_size > 1000:
                    # Run cleanup asynchronously without blocking
                    import asyncio
                    asyncio.create_task(cleanup_stale_tags(request, table, conn_scope))
            except Exception:
                pass  # If size check fails, continue anyway

        # Increment entries cached metric
        await redis.incrby("argus:metrics:entries_cached", 1)

        logger.info(f"Cache SET: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


async def cleanup_stale_tags(
    request: Request,
    table: str,
    conn_scope: str = "default",
):
    """
    Remove stale/expired cache key references from a table's tag set.
    Called when tag set grows to prevent unbounded memory usage.
    Uses SSCAN to avoid loading all members into memory at once.
    """
    redis = request.app.state.redis
    tag_key = f"argus:cache_tags:{conn_scope}:{table}"

    try:
        cursor = 0
        stale_count = 0

        while True:
            # SSCAN the tag key set with COUNT hint
            cursor, cache_keys = await redis.sscan(tag_key, cursor, count=100)

            if cache_keys:
                # Check which cache keys still exist
                for cache_key in cache_keys:
                    exists = await redis.exists(cache_key)
                    if not exists:
                        # Key expired; remove from tag set
                        await redis.srem(tag_key, cache_key)
                        stale_count += 1

            # Continue if cursor is not 0
            if cursor == 0:
                break

        if stale_count > 0:
            logger.info(f"Cleaned {stale_count} stale tags from '{table}'")

    except Exception as e:
        logger.warning(f"Tag cleanup error for '{table}': {e}")


async def invalidate_table_cache(
    request: Request,
    table_names: tuple,
    conn_scope: str = "default",
):
    """
    Invalidate all cache entries for given tables using SCAN pattern.
    Avoids loading all keys into memory with SMEMBERS on large sets.
    Used after INSERT/UPDATE/DELETE.
    """
    redis = request.app.state.redis

    for table in table_names:
        tag_key = f"argus:cache_tags:{conn_scope}:{table}"
        try:
            import time
            start_time = time.time()
            
            # Use SCAN to efficiently iterate over cache keys without loading all at once
            cursor = 0
            deleted_count = 0

            while True:
                # SSCAN the tag key set with COUNT hint for batching
                cursor, cache_keys = await redis.sscan(tag_key, cursor, count=100)

                if cache_keys:
                    # Delete all cache keys in one pipeline for efficiency
                    for cache_key in cache_keys:
                        # Decode if cache_key is bytes
                        if isinstance(cache_key, bytes):
                            cache_key = cache_key.decode("utf-8")
                        await redis.delete(cache_key)
                        meta_key = cache_key.replace("argus:cache:", "argus:cache_meta:")
                        await redis.delete(meta_key)
                        # optionally clean from valuable_caches to keep it tidy
                        await redis.zrem("argus:stats:valuable_caches", cache_key)
                    deleted_count += len(cache_keys)

                # Continue if cursor is not 0
                if cursor == 0:
                    break

            if deleted_count > 0:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Track most invalidated tables
                await redis.zincrby("argus:stats:invalidated_tables", 1, table)
                
                # Trace invalidation metric
                audit_event = {
                    "event": "CACHE_INVALIDATION",
                    "tables": [table],
                    "keys_deleted": deleted_count,
                    "duration_ms": duration_ms,
                    "conn_scope": conn_scope
                }
                
                logger.info(f"Cache Invalidation Trace:\n{json.dumps(audit_event, indent=2)}")

                # Track metrics
                await redis.incrby("argus:metrics:entries_invalidated", deleted_count)
                pipe = redis.pipeline()
                pipe.lpush("argus:metrics:invalidation_latency_samples", duration_ms)
                pipe.ltrim("argus:metrics:invalidation_latency_samples", 0, 99) # Keep last 100
                await pipe.execute()

            # Delete the tag key itself
            await redis.delete(tag_key)
        except Exception as e:
            logger.warning(f"Cache invalidation error for '{table}': {e}")
