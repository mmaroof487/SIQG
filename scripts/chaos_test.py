"""
Argus Chaos Test
================
Injects real infrastructure faults by killing and restarting Docker containers,
then verifies the gateway recovers within a configurable SLA window.

Requires:
    pip install docker httpx
    Docker socket accessible (run from host, not inside a container)

Usage:
    python scripts/chaos_test.py
    python scripts/chaos_test.py --token <JWT> --project siqg --recovery-sla 30
"""
import asyncio
import argparse
import time
import sys

import httpx

try:
    import docker
except ImportError:
    print("❌ 'docker' package not found. Run: pip install docker")
    sys.exit(1)

API_BASE = "http://localhost:8000"

# Container name format: <compose-project>-<service>-<replica>
# Adjust --project if your docker compose project name differs from 'siqg'
SERVICES = {
    "redis": "{project}-redis-1",
    "postgres": "{project}-postgres-1",
    "gateway": "{project}-gateway-1",
}

KILL_DURATION_SECONDS = 10   # how long the container stays stopped
POLL_INTERVAL_SECONDS = 2    # how often to probe /health/ready during recovery


async def wait_for_recovery(
    base_url: str,
    token: str | None,
    sla_seconds: int,
    label: str,
) -> tuple[bool, float]:
    """
    Poll /health/ready until it returns 200 or SLA expires.
    Returns (recovered: bool, elapsed_seconds: float).
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    start = time.perf_counter()
    deadline = start + sla_seconds
    attempt = 0

    async with httpx.AsyncClient(base_url=base_url, timeout=5.0, headers=headers) as client:
        while time.perf_counter() < deadline:
            attempt += 1
            try:
                resp = await client.get("/health/ready")
                if resp.status_code == 200:
                    elapsed = time.perf_counter() - start
                    print(f"      ✅ [{label}] Recovered in {elapsed:.1f}s (attempt {attempt})")
                    return True, elapsed
                else:
                    print(f"      ⏳ [{label}] Attempt {attempt}: status {resp.status_code}")
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                print(f"      ⏳ [{label}] Attempt {attempt}: {type(exc).__name__}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    elapsed = time.perf_counter() - start
    print(f"      ❌ [{label}] DID NOT recover within {sla_seconds}s")
    return False, elapsed


def run_chaos_scenario(
    docker_client,
    container_name: str,
    label: str,
    kill_duration: int,
    recovery_sla: int,
    token: str | None,
) -> dict:
    """Kill a container, wait, restart it, then verify recovery."""
    print(f"\n{'='*55}")
    print(f"  SCENARIO: Kill {label} ({container_name})")
    print(f"{'='*55}")

    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        msg = f"Container '{container_name}' not found. Run 'docker ps' to confirm name."
        print(f"  ⚠️  SKIP: {msg}")
        return {"service": label, "skipped": True, "reason": msg}

    # 1. Kill
    print(f"  🔪 Stopping {container_name}...")
    container.stop(timeout=5)
    killed_at = time.perf_counter()

    # 2. Confirm gateway notices the fault
    print(f"  ⏸️  Container stopped. Waiting {kill_duration}s before restart...")
    time.sleep(kill_duration)

    # 3. Restart
    print(f"  ▶️  Restarting {container_name}...")
    container.start()
    restarted_at = time.perf_counter()
    print(f"  🔄 Container restarted. Waiting for gateway to recover...")

    # 4. Poll for recovery
    recovered, elapsed = asyncio.run(
        wait_for_recovery(API_BASE, token, recovery_sla, label)
    )

    return {
        "service": label,
        "container": container_name,
        "skipped": False,
        "recovered": recovered,
        "kill_duration_s": kill_duration,
        "recovery_time_s": round(elapsed, 1),
        "sla_s": recovery_sla,
        "sla_met": recovered and elapsed <= recovery_sla,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Argus chaos engineering test")
    parser.add_argument("--token", default=None, help="JWT token for health check auth (optional)")
    parser.add_argument("--project", default="siqg", help="Docker Compose project name (default: siqg)")
    parser.add_argument("--kill-duration", type=int, default=KILL_DURATION_SECONDS,
                        help=f"Seconds to keep container stopped (default: {KILL_DURATION_SECONDS})")
    parser.add_argument("--recovery-sla", type=int, default=30,
                        help="Max seconds to consider recovery successful (default: 30)")
    parser.add_argument("--services", nargs="+", default=["redis", "postgres"],
                        choices=list(SERVICES.keys()),
                        help="Which services to kill (default: redis postgres). 'gateway' requires --token.")
    args = parser.parse_args()

    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as exc:
        print(f"❌ Cannot connect to Docker daemon: {exc}")
        sys.exit(1)

    print(f"\n🌀 Argus Chaos Test")
    print(f"   Project  : {args.project}")
    print(f"   Services : {', '.join(args.services)}")
    print(f"   Kill for : {args.kill_duration}s per service")
    print(f"   SLA      : {args.recovery_sla}s")

    results = []
    for svc in args.services:
        container_name = SERVICES[svc].format(project=args.project)
        result = run_chaos_scenario(
            docker_client=docker_client,
            container_name=container_name,
            label=svc,
            kill_duration=args.kill_duration,
            recovery_sla=args.recovery_sla,
            token=args.token,
        )
        results.append(result)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print("  CHAOS TEST SUMMARY")
    print(f"{'='*55}")
    all_passed = True
    for r in results:
        if r.get("skipped"):
            icon = "⚠️ "
            status = f"SKIPPED ({r['reason']})"
        elif r.get("sla_met"):
            icon = "✅"
            status = f"PASS — recovered in {r['recovery_time_s']}s (SLA: {r['sla_s']}s)"
        else:
            icon = "❌"
            status = f"FAIL — took {r['recovery_time_s']}s (SLA: {r['sla_s']}s)"
            all_passed = False
        print(f"  {icon}  {r['service']:20s} {status}")

    print()
    if all_passed:
        print("✅ All chaos scenarios passed.")
    else:
        print("❌ One or more scenarios failed. Review gateway circuit-breaker and restart config.")
        sys.exit(1)


if __name__ == "__main__":
    main()
