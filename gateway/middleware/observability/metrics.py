from fastapi import Request
import time

async def increment(request: Request, key: str, amount: float = 1):
    redis = request.app.state.redis
    await redis.incrbyfloat(f"argus:metrics:{key}", amount)

async def record_latency(request: Request, latency_ms: float):
    redis = request.app.state.redis
    # Keep last 1000 latency values for percentile calculation
    pipe = redis.pipeline()
    pipe.lpush("argus:metrics:latency_samples", latency_ms)
    pipe.ltrim("argus:metrics:latency_samples", 0, 999)
    await pipe.execute()

async def get_live_metrics(redis) -> dict:
    keys = [
        "argus:metrics:requests_total",
        "argus:metrics:cache_hits",
        "argus:metrics:cache_misses",
        "argus:metrics:rate_limit_hits",
        "argus:metrics:slow_queries",
        "argus:metrics:errors",
        "argus:metrics:entries_cached",
        "argus:metrics:entries_invalidated",
    ]
    values = await redis.mget(*keys)
    metrics = {k.split(":")[-1]: float(v or 0) for k, v in zip(keys, values)}

    # Latency percentiles
    samples = await redis.lrange("argus:metrics:latency_samples", 0, -1)
    if samples:
        sorted_samples = sorted(float(s) for s in samples)
        n = len(sorted_samples)
        metrics["latency_p50"] = sorted_samples[int(n * 0.5)]
        metrics["latency_p95"] = sorted_samples[int(n * 0.95)]
        metrics["latency_p99"] = sorted_samples[int(n * 0.99)]
    else:
        metrics["latency_p50"] = 0
        metrics["latency_p95"] = 0
        metrics["latency_p99"] = 0

    # Cache hit ratio
    hits = metrics.get("cache_hits", 0)
    misses = metrics.get("cache_misses", 0)
    total = hits + misses
    metrics["cache_hit_ratio"] = round(hits / total * 100, 1) if total > 0 else 0
    metrics["cache_miss_ratio"] = round(misses / total * 100, 1) if total > 0 else 0
    
    # Average Invalidation Latency
    invalidation_samples = await redis.lrange("argus:metrics:invalidation_latency_samples", 0, -1)
    if invalidation_samples:
        metrics["avg_invalidation_ms"] = round(sum(float(s) for s in invalidation_samples) / len(invalidation_samples), 1)
    else:
        metrics["avg_invalidation_ms"] = 0

    return metrics
