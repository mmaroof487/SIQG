"""
Argus Performance Benchmark
============================
Measures real latency, throughput, and encryption overhead against a live stack.

Usage:
    python scripts/benchmark.py --token <JWT> --connection-id <UUID>
    python scripts/benchmark.py --token <JWT> --connection-id <UUID> --requests 500
"""
import asyncio
import argparse
import time
import statistics
import json
import sys

import httpx

API_BASE = "http://localhost:8000/api/v1"

PLAINTEXT_QUERY = "SELECT 1"
# A query that exercises the encryption/decryption path if encrypt_columns is set
# Adjust table name to one that exists in your test DB
ENCRYPTED_QUERY = "SELECT id FROM users LIMIT 1"


async def measure_latency(
    client: httpx.AsyncClient,
    endpoint: str,
    method: str = "GET",
    json_body: dict | None = None,
    n: int = 100,
    label: str = "",
) -> list[float]:
    """Fire n sequential requests and collect latency in ms."""
    latencies = []
    print(f"  → {label} ({n} sequential requests)...", end="", flush=True)
    for _ in range(n):
        start = time.perf_counter()
        try:
            if method == "GET":
                await client.get(endpoint)
            else:
                await client.post(endpoint, json=json_body)
        except Exception:
            pass
        latencies.append((time.perf_counter() - start) * 1000)
    print(f" done (p50={statistics.median(latencies):.1f}ms)")
    return latencies


async def measure_throughput(
    client: httpx.AsyncClient,
    endpoint: str,
    json_body: dict | None,
    concurrent: int = 20,
    duration: int = 10,
) -> float:
    """Fire concurrent requests for `duration` seconds, return req/s."""
    print(f"  → Throughput ({concurrent} workers, {duration}s)...", end="", flush=True)
    stop = asyncio.Event()
    count = 0

    async def _worker():
        nonlocal count
        while not stop.is_set():
            try:
                if json_body:
                    await client.post(endpoint, json=json_body)
                else:
                    await client.get(endpoint)
                count += 1
            except Exception:
                pass

    tasks = [asyncio.create_task(_worker()) for _ in range(concurrent)]
    await asyncio.sleep(duration)
    stop.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    rps = count / duration
    print(f" done ({count} req in {duration}s = {rps:.1f} req/s)")
    return round(rps, 1)


async def measure_cache_ratio(
    client: httpx.AsyncClient,
    connection_id: str,
    n: int = 50,
) -> str:
    """
    Run the same query twice per iteration. First call is a cache miss,
    second should be a cache hit (gateway caches identical queries in Redis).
    Compare average latency of first vs second call as a proxy for hit ratio.
    """
    print(f"  → Cache hit ratio proxy ({n} pairs)...", end="", flush=True)
    first_latencies, second_latencies = [], []
    body = {"connection_id": connection_id, "query": PLAINTEXT_QUERY, "limit": 1}
    for _ in range(n):
        t0 = time.perf_counter()
        await client.post("/query/execute", json=body)
        first_latencies.append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        await client.post("/query/execute", json=body)
        second_latencies.append((time.perf_counter() - t0) * 1000)

    avg_first = statistics.mean(first_latencies)
    avg_second = statistics.mean(second_latencies)
    speedup = avg_first / avg_second if avg_second > 0 else 1.0
    # If second call is materially faster, cache is working
    ratio = min(99, max(0, int((1 - 1 / speedup) * 100))) if speedup > 1.1 else 0
    result = f"~{ratio}% (first={avg_first:.1f}ms, second={avg_second:.1f}ms)"
    print(f" done ({result})")
    return result


async def run_benchmark(
    token: str,
    connection_id: str,
    n_requests: int,
    throughput_workers: int,
    throughput_duration: int,
) -> None:
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\n🚀 Argus Performance Benchmark")
    print(f"   Target      : {API_BASE}")
    print(f"   Conn ID     : {connection_id}")
    print(f"   Req per run : {n_requests}\n")

    query_body = {
        "connection_id": connection_id,
        "query": PLAINTEXT_QUERY,
        "limit": 1,
    }

    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers=headers,
        timeout=httpx.Timeout(15.0, connect=5.0),
        limits=httpx.Limits(
            max_connections=throughput_workers + 10,
            max_keepalive_connections=throughput_workers,
        ),
    ) as client:
        # 1. Health endpoint latency (no auth overhead — pure infra)
        health_latencies = await measure_latency(
            client, "/health/ready", method="GET", n=n_requests, label="Health latency"
        )

        # 2. Query endpoint latency (full stack: auth + SQL + encryption)
        query_latencies = await measure_latency(
            client, "/query/execute", method="POST",
            json_body=query_body, n=n_requests, label="Query latency (full stack)"
        )

        # 3. Encryption overhead: difference between health and query p50
        health_p50 = statistics.median(health_latencies)
        query_p50 = statistics.median(query_latencies)
        enc_overhead = max(0.0, query_p50 - health_p50)

        # 4. Throughput
        rps = await measure_throughput(
            client, "/query/execute", query_body,
            concurrent=throughput_workers, duration=throughput_duration
        )

        # 5. Cache ratio proxy
        cache_ratio = await measure_cache_ratio(client, connection_id, n=min(50, n_requests))

    def percentiles(data: list[float]) -> dict:
        n = len(data)
        return {
            "p50": round(statistics.median(data), 2),
            "p95": round(statistics.quantiles(data, n=20)[18] if n >= 20 else max(data), 2),
            "p99": round(statistics.quantiles(data, n=100)[98] if n >= 100 else max(data), 2),
            "min": round(min(data), 2),
            "max": round(max(data), 2),
        }

    report = {
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "n_requests": n_requests,
            "throughput_workers": throughput_workers,
            "throughput_duration_s": throughput_duration,
        },
        "metrics": {
            "health_latency_ms": percentiles(health_latencies),
            "query_latency_ms": percentiles(query_latencies),
            "throughput_req_sec": rps,
            "encryption_overhead_ms": round(enc_overhead, 2),
            "cache_hit_ratio": cache_ratio,
        },
    }

    print("\n" + "=" * 50)
    print(json.dumps(report, indent=2))
    print("=" * 50)

    with open("benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n✅ Benchmark report saved to benchmark_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Argus performance benchmark")
    parser.add_argument("--token", required=True, help="JWT or API key")
    parser.add_argument("--connection-id", required=True, help="UserDatabase connection UUID")
    parser.add_argument("--requests", type=int, default=100, help="Requests per latency run (default: 100)")
    parser.add_argument("--throughput-workers", type=int, default=20, help="Concurrent workers for throughput (default: 20)")
    parser.add_argument("--throughput-duration", type=int, default=10, help="Throughput test duration seconds (default: 10)")
    args = parser.parse_args()

    asyncio.run(run_benchmark(
        token=args.token,
        connection_id=args.connection_id,
        n_requests=args.requests,
        throughput_workers=args.throughput_workers,
        throughput_duration=args.throughput_duration,
    ))


if __name__ == "__main__":
    main()
