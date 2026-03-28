from fastapi import Request
import time

async def increment(request: Request, key: str, amount: float = 1):
    redis = request.app.state.redis
    await redis.incrbyfloat(f"siqg:metrics:{key}", amount)

async def record_latency(request: Request, latency_ms: float):
    redis = request.app.state.redis
    # Keep last 1000 latency values for percentile calculation
    pipe = redis.pipeline()
    pipe.lpush("siqg:metrics:latency_samples", latency_ms)
    pipe.ltrim("siqg:metrics:latency_samples", 0, 999)
    await pipe.execute()

async def get_live_metrics(redis) -> dict:
    keys = [
        "siqg:metrics:requests_total",
        "siqg:metrics:cache_hits",
        "siqg:metrics:cache_misses",
        "siqg:metrics:rate_limit_hits",
        "siqg:metrics:slow_queries",
        "siqg:metrics:errors",
    ]
    values = await redis.mget(*keys)
    metrics = {k.split(":")[-1]: float(v or 0) for k, v in zip(keys, values)}

    # Latency percentiles
    samples = await redis.lrange("siqg:metrics:latency_samples", 0, -1)
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

    return metrics
