# Argus Testing Guide (Phases 1-4)

## Quick Start
The fastest way to verify the entire system (Security, Performance, and Intelligence layers) is to use the integrated test orchestration script:

```bash
bash test_all_phases.sh
```
This script will automatically rebuild the gateway, provision the primary and replica databases, flush the Redis persistent cache, and run every feature test sequentially.

---

## What Each Phase Tests

### Phase 1: Security Layer
✅ JWT authentication
✅ Brute force protection (5 attempts → 15min lockout)
✅ IP filtering (allow/blocklist)
✅ Rate limiting (60 queries/min)
✅ SQL injection detection (regex patterns)
✅ RBAC permission checks (Admin/Readonly/Guest)
✅ Query type allowlist (SELECT+INSERT allowed, DROP blocked)

### Phase 2: Performance Layer
✅ Query fingerprinting (SHA-256 of normalized query)
✅ Redis True Cache (2-5ms hits, DB fully bypassed by inline analysis metadata)
✅ Cache invalidation (table-tagged, triggers on INSERT/UPDATE/DELETE)
✅ Cost estimation (EXPLAIN without execution)
✅ Budget enforcement (daily per-user cost limit)
✅ Auto-LIMIT injection (prevents unbounded SELECT)
✅ Database routing (SELECT→replica, writes→primary)

### Phase 3: Intelligence & Resilience Layer
✅ EXPLAIN ANALYZE parsing in response metadata
✅ Recursive Seq Scan extraction & Index Recommendations
✅ Query complexity scoring (`low`/`medium`/`high`)
✅ Circuit Breaker State Management (Open/Half-Open/Closed)
✅ Column Encryption (AES-256-GCM) & Blind DLP Pattern Masking (Defeats SQL Aliasing)
✅ Native SQLAlchemy colon escaping for raw Postgres casting (`::uuid`) & JSON operators
✅ Slow query detection + persistence

### Phase 4: Observability Layer
✅ Structured JSON tracing with `trace_id` assignment
✅ Fire-and-forget background audit log insertion
✅ Redis cumulative analytic counters (Rate limits, requests, cached)
✅ Real-time pipeline calculation of live P50, P95, and P99 queries via sliding Lists
✅ Asynchronous HTTPX unified webhooks alerting system (Slow queries, Security honeypot hits, Anomalies)
✅ Heatmaps for monitoring dynamic table densities
✅ Dynamic degradation health statuses supporting Redis/Database PING routines

---

## Manual Testing with curl

### Setup: Get a Token

1. **Start services**:
```bash
docker-compose up -d --build
```

2. **Register a test user**:
```bash
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "Test@1234"}' | jq -r '.access_token')

echo $TOKEN
```

---

## Phase 1 Manual Tests

### Test 1: SQL Injection Detection
```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE id = 1 OR 1=1; DROP TABLE users;"}'
# Expected: 400 Bad Request, "SQL injection pattern detected"
```

### Test 2: Dangerous Query Blocking
```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "DROP TABLE users"}'
# Expected: 400 Bad Request, "DROP queries are not allowed"
```

---

## Phase 2 Manual Tests

### Test 1: Cache Hit (2-5ms)
**First execution (CACHE MISS):**
```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "SELECT 1 as test_value"}' | jq '{latency_ms, cached}'
# Expected: cached=false, latency_ms=~45.0
```

**Identical query (CACHE HIT):**
```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "SELECT 1 as test_value"}' | jq '{latency_ms, cached}'
# Expected: cached=true, latency_ms=~2.0
```

### Test 2: Budget Enforcement
```bash
# View current usage:
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN"
# Expected: Shows daily_budget, current_usage, remaining, and resets_at
```

---

## Phase 3 Manual Tests

### Test 1: Analysis Payload & Complexity Scoring
```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT 1 as phase3_test"}' | jq '.analysis'
# Expected keys: scan_type, execution_time_ms, rows_processed, total_cost, slow_query, index_suggestions, complexity
```

### Test 2: Index Suggestions (Engine Check)
```bash
# Querying a native system table to force the analyzer to profile it
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT * FROM pg_database WHERE datname = '\'postgres\''"}' | jq '.analysis.index_suggestions'
# Expected: Array of suggestions if a Seq Scan was forced containing DDL create statements
```

---

## Phase 4 Manual Tests

### Test 1: Live Polling Metrics
Observe continuous unauthenticated telemetry metrics (e.g., performance counters, p50/p95/p99) generated across recent traffic behavior.

```bash
curl -X GET http://localhost:8000/api/v1/metrics/live
# Expected: JSON containing keys like `request_count`, `latency_p50`, `latency_p99`, `cache_hit_ratio`
```

### Test 2: Heatmap Visualizations
Execute a few structural queries that read from specific SQL schemas, then analyze the heatmap output.

```bash
# Step 1: Query an arbitrary table to build an index event
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT * FROM public_data LIMIT 1"}'

# Step 2: Retrieve the heatmap (Admin Required)
curl -X GET http://localhost:8000/api/v1/admin/heatmap \
  -H "Authorization: Bearer $TOKEN" 
# Expected: JSON Array matching `[{"table": "public_data", "score": 1}]`
```

### Test 3: Exporting the Streaming Audit Log
Test whether the pagination/CSV streams efficiently generate an isolated `.csv` download stream carrying structural audit queries.

```bash
curl -X GET http://localhost:8000/api/v1/admin/audit/export \
  -H "Authorization: Bearer $TOKEN" \
  --output audit_logs.csv
# Expected: a validly formatted `audit_logs.csv` downloaded containing trailing audit states
```

### Test 4: Dynamic Integrated Health Check
Ensure `gateway` can appropriately identify internal service isolation breakdowns by validating connection states toward databases AND caching layers.

```bash
curl -X GET http://localhost:8000/health
# Expected: 200 OK — {"status": "ok", "db": "ok", "redis": "ok"}
```

---

## Load Testing (Phase 1-4)
If you want to view the behavior of rate-limiting, circuit breakers, and connection pooling under extreme pressure:

```bash
# Start Locust with 100 concurrent users, 10 spawn rate, 60s duration
make load-test
# Or manually:
cd tests/load
locust -f locustfile.py --headless -u 100 -r 10 -t 60s
```
Metrics Observed: Cache hit rate, API lockouts (429s for budget/rate limits), and Circuit Breaker pop events (503s).
