"""
Argus Stress Test
=================
Performs real concurrent HTTP requests against the query endpoint.

Usage:
    # From project root, with the stack running:
    python scripts/stress_test.py --token <JWT_OR_API_KEY> --connection-id <UUID>

    # Ramp up concurrency:
    python scripts/stress_test.py --token <tok> --connection-id <uuid> --workers 50 --duration 60
"""
import asyncio
import argparse
import time
import statistics
import sys
import httpx

API_BASE = "http://localhost:8000/api/v1"

# Queries cycled through during the test — chosen to exercise different code paths
QUERY_POOL = [
    "SELECT 1",
    "SELECT NOW()",
    "SELECT COUNT(*) FROM information_schema.tables",
    "SELECT table_name FROM information_schema.tables LIMIT 5",
]


async def single_request(
    client: httpx.AsyncClient,
    connection_id: str,
    query: str,
    results: list,
) -> None:
    """Fire one POST /query/execute and record latency + status."""
    start = time.perf_counter()
    status = 0
    error = None
    try:
        resp = await client.post(
            "/query/execute",
            json={"connection_id": connection_id, "query": query, "limit": 10},
        )
        status = resp.status_code
    except httpx.TimeoutException:
        error = "timeout"
    except Exception as exc:
        error = str(exc)
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        results.append({"latency_ms": elapsed_ms, "status": status, "error": error})


async def worker(
    client: httpx.AsyncClient,
    connection_id: str,
    stop_event: asyncio.Event,
    results: list,
    worker_id: int,
) -> None:
    """Continuously fire requests until stop_event is set."""
    idx = worker_id  # stagger query selection across workers
    while not stop_event.is_set():
        query = QUERY_POOL[idx % len(QUERY_POOL)]
        await single_request(client, connection_id, query, results)
        idx += 1
        # Small yield so the event loop can check stop_event
        await asyncio.sleep(0)


async def run_stress_test(
    token: str,
    connection_id: str,
    workers: int,
    duration: int,
    ramp_seconds: int,
) -> None:
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\n🔥 Argus Stress Test")
    print(f"   Workers  : {workers}")
    print(f"   Duration : {duration}s  (ramp: {ramp_seconds}s)")
    print(f"   Target   : {API_BASE}/query/execute")
    print(f"   Conn ID  : {connection_id}\n")

    results: list = []
    stop_event = asyncio.Event()

    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers=headers,
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(max_connections=workers + 10, max_keepalive_connections=workers),
    ) as client:
        # Ramp: launch workers in batches over ramp_seconds
        tasks = []
        batch_size = max(1, workers // max(1, ramp_seconds))
        launched = 0
        wall_start = time.perf_counter()

        for i in range(workers):
            tasks.append(asyncio.create_task(worker(client, connection_id, stop_event, results, i)))
            launched += 1
            if ramp_seconds > 0 and launched % batch_size == 0:
                await asyncio.sleep(ramp_seconds / max(1, workers // batch_size))

        print(f"✅ All {workers} workers running. Stress testing for {duration}s...")
        await asyncio.sleep(duration)
        stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    wall_elapsed = time.perf_counter() - wall_start

    # ── Report ────────────────────────────────────────────────────────────────
    total = len(results)
    if total == 0:
        print("❌ No requests completed. Check that the stack is running and token is valid.")
        sys.exit(1)

    latencies = [r["latency_ms"] for r in results]
    statuses = [r["status"] for r in results]
    errors = [r for r in results if r["error"]]
    successes = sum(1 for s in statuses if 200 <= s < 300)
    rate_limited = sum(1 for s in statuses if s == 429)
    server_errors = sum(1 for s in statuses if s >= 500)

    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if total >= 20 else max(latencies)
    p99 = statistics.quantiles(latencies, n=100)[98] if total >= 100 else max(latencies)
    throughput = total / wall_elapsed

    print("\n" + "=" * 50)
    print("📊 STRESS TEST RESULTS")
    print("=" * 50)
    print(f"  Total requests   : {total}")
    print(f"  Elapsed          : {wall_elapsed:.1f}s")
    print(f"  Throughput       : {throughput:.1f} req/s")
    print(f"  Successes (2xx)  : {successes}  ({successes/total*100:.1f}%)")
    print(f"  Rate limited 429 : {rate_limited}")
    print(f"  Server errors 5xx: {server_errors}")
    print(f"  Network errors   : {len(errors)}")
    print(f"\n  Latency (ms)")
    print(f"    p50  : {p50:.1f}")
    print(f"    p95  : {p95:.1f}")
    print(f"    p99  : {p99:.1f}")
    print(f"    min  : {min(latencies):.1f}")
    print(f"    max  : {max(latencies):.1f}")
    print("=" * 50)

    if server_errors > 0:
        print(f"\n⚠️  {server_errors} server errors — check gateway logs.")
    if throughput < 10:
        print("\n⚠️  Throughput below 10 req/s — possible bottleneck or auth failure.")
    else:
        print("\n✅ Stress test complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Argus concurrent stress test")
    parser.add_argument("--token", required=True, help="JWT or API key for auth")
    parser.add_argument("--connection-id", required=True, help="UserDatabase connection UUID")
    parser.add_argument("--workers", type=int, default=20, help="Concurrent workers (default: 20)")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds (default: 30)")
    parser.add_argument("--ramp", type=int, default=5, help="Ramp-up seconds (default: 5)")
    args = parser.parse_args()

    asyncio.run(run_stress_test(
        token=args.token,
        connection_id=args.connection_id,
        workers=args.workers,
        duration=args.duration,
        ramp_seconds=args.ramp,
    ))


if __name__ == "__main__":
    main()
