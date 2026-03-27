# Testing Phase 1, Phase 2, and Phase 3 — Complete Guide

## Quick Start

```bash
# 1. Start all services (Gateway + Postgres + Redis)
docker-compose up -d

# 2. Run unit + integration tests
make test

# 3. Check logs
make logs

# 4. Stop services
make down
```

---

## What Each Phase Tests

### Phase 1: Security Layer

✅ JWT authentication
✅ API key hashing
✅ Brute force protection (5 attempts → 15min lockout)
✅ IP filtering (allow/blocklist)
✅ Rate limiting (60 queries/min)
✅ SQL injection detection (regex patterns)
✅ RBAC permission checks (Admin/Readonly/Guest)
✅ Query type allowlist (SELECT+INSERT allowed, DROP/ALTER blocked)

### Phase 2: Performance Layer

✅ Query fingerprinting (SHA-256 of normalized query)
✅ Redis cache (2-5ms hits on identical queries)
✅ Cache invalidation (table-tagged, triggers on INSERT/UPDATE/DELETE)
✅ Cost estimation (EXPLAIN without execution)
✅ Budget enforcement (daily per-user cost limit)
✅ Auto-LIMIT injection (prevents unbounded SELECT)
✅ Database routing (SELECT→replica, writes→primary)

### Phase 3: Intelligence Layer

✅ EXPLAIN ANALYZE parsing in response metadata  
✅ Recursive Seq Scan extraction  
✅ Index recommendation generation and dedupe  
✅ Query complexity scoring (`low`/`medium`/`high`)  
✅ Slow query detection + persistence  
✅ Admin slow query retrieval endpoint

---

## Testing Setup

### Prerequisites

```bash
# Ensure Docker & Docker Compose installed
docker --version
docker-compose --version

# Python 3.11+ with pytest + pytest-asyncio
python --version
pip install pytest pytest-asyncio pytest-cov
```

### Environment Configuration

Create `.env` in project root (if not exists):

```env
SECRET_KEY=test_secret_key_12345
JWT_EXPIRY_MINUTES=60
ENVIRONMENT=development

DB_PRIMARY_URL=postgresql+asyncpg://queryx:queryx@postgres:5432/queryx
DB_REPLICA_URL=postgresql+asyncpg://queryx:queryx@postgres_replica:5432/queryx
REDIS_URL=redis://redis:6379

RATE_LIMIT_PER_MINUTE=60
BRUTE_FORCE_MAX_ATTEMPTS=5
BRUTE_FORCE_LOCKOUT_MINUTES=15
ENCRYPTION_KEY=test_key_32_bytes_long_exactly!
HONEYPOT_TABLES=secret_keys,admin_passwords
QUERY_TIMEOUT_SECONDS=5
CACHE_DEFAULT_TTL=60
AUTO_LIMIT_DEFAULT=1000
COST_THRESHOLD_WARN=1000
COST_THRESHOLD_BLOCK=10000
SLOW_QUERY_THRESHOLD_MS=200
DAILY_BUDGET_DEFAULT=50000
CIRCUIT_FAILURE_THRESHOLD=5
CIRCUIT_COOLDOWN_SECONDS=30
```

---

## Running Tests

### 0. Run Phases One-by-One

```bash
# All phases
bash test_phase1_phase2.sh all

# Or one phase at a time:
bash test_phase1_phase2.sh phase1
bash test_phase1_phase2.sh phase2
bash test_phase1_phase2.sh phase3

# One-command sequential runner with summary
bash test_all_phases.sh
```

### 1. All Tests (Unit + Integration)

```bash
make test
# Output:
# tests/unit/test_auth.py::test_hash_api_key PASSED
# tests/unit/test_auth.py::test_create_and_decode_jwt PASSED
# tests/unit/test_rate_limiter.py::test_rate_limit_within_limit PASSED
# tests/integration/test_full_pipeline.py::test_health_endpoint PASSED
# ====== N passed in 2.34s [coverage: 72%] ======
```

### 2. Unit Tests Only

```bash
pytest tests/unit/ -v --cov=gateway.middleware

# By Phase:
# PHASE 1 SECURITY:
pytest tests/unit/test_auth.py -v
pytest tests/unit/test_validator.py -v
pytest tests/unit/test_rate_limiter.py -v
pytest tests/unit/test_rbac.py -v

# PHASE 2 PERFORMANCE:
pytest tests/unit/test_fingerprinter.py -v
pytest tests/unit/test_cache.py -v [if created]
pytest tests/unit/test_budget.py -v [if created]

# PHASE 3 INTELLIGENCE:
pytest tests/unit/test_complexity.py -v
pytest tests/unit/test_encryption.py -v
```

### 3. Integration Tests

```bash
pytest tests/integration/test_full_pipeline.py -v

# Watch real database + cache behavior
docker-compose logs -f gateway
```

### 4. Coverage Report

```bash
pytest tests/ -v --cov=gateway --cov-report=html
# Opens htmlcov/index.html in browser
```

---

## Manual Testing with curl

### Setup: Get a Token

1. **Start services**:

```bash
docker-compose up -d
sleep 10  # Wait for postgres to be ready
```

2. **Create a test user** (via login endpoint):

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'

# Response:
# {
#   "access_token": "eyJhbGc...",
#   "token_type": "bearer"
# }

# Save token for next requests:
export TOKEN="eyJhbGc..."
```

---

## Phase 1 Manual Tests

### Test 1: SQL Injection Detection

```bash
# Attempt malicious query
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM users WHERE id = 1 OR 1=1; DROP TABLE users;"
  }'

# Expected: 400 Bad Request
# Error: "SQL injection pattern detected"
```

### Test 2: Dangerous Query Blocking

```bash
# Try DROP TABLE
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "DROP TABLE users"}'

# Expected: 400 Bad Request
# Error: "Query type not allowed. Allowed: SELECT, INSERT"
```

### Test 3: Rate Limiting (60 reqs/min)

```bash
# Make 61 requests in rapid succession
for i in {1..61}; do
  curl -X POST http://localhost:8000/api/v1/query/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query": "SELECT 1"}' &
done
wait

# After 60: 429 Too Many Requests
```

### Test 4: RBAC Permission Check

```bash
# Create READONLY user token
readonly_token=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "readonly_user", "password": "pass", "role": "readonly"}' | jq -r '.access_token')

# Try INSERT with readonly token
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $readonly_token" \
  -H "Content-Type: application/json" \
  -d '{"query": "INSERT INTO users (name) VALUES (\"Bob\")"}'

# Expected: 403 Forbidden
# Error: "Insufficient permissions. Role: readonly cannot INSERT"
```

---

## Phase 2 Manual Tests

### Setup: Create Test Table

```bash
# Enter postgres container
docker-compose exec postgres psql -U queryx -d queryx

# Create test table
CREATE TABLE test_products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  price DECIMAL(10,2),
  category VARCHAR(50)
);

INSERT INTO test_products (name, price, category) VALUES
  ('Laptop', 999.99, 'Electronics'),
  ('Mouse', 29.99, 'Electronics'),
  ('Desk', 299.99, 'Furniture');

EXIT;
```

### Test 1: Cache Hit (2-5ms)

**First execution (CACHE MISS):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM test_products WHERE category = \"Electronics\""
  }'

# Response:
# {
#   "trace_id": "abc-123...",
#   "query_type": "SELECT",
#   "rows": [
#     {"id": 1, "name": "Laptop", "price": 999.99, "category": "Electronics"},
#     {"id": 2, "name": "Mouse", "price": 29.99, "category": "Electronics"}
#   ],
#   "rows_count": 2,
#   "latency_ms": 45.2,      <--- Actual DB execution
#   "cached": false,
#   "cost": 120.5
# }
```

**Identical query (CACHE HIT):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM test_products WHERE category = \"Electronics\""
  }'

# Response:
# {
#   "trace_id": "def-456...",
#   "latency_ms": 2.1,       <--- Returned from Redis cache
#   "cached": true,
#   "cost": 120.5
# }
```

### Test 2: Cache Invalidation on Write

**Execute INSERT:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "INSERT INTO test_products (name, price, category) VALUES (\"Keyboard\", 79.99, \"Electronics\")"
  }'

# Cache for test_products table is now INVALIDATED
```

**Query again (CACHE MISS - forced re-execute):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM test_products WHERE category = \"Electronics\""
  }'

# Response:
# {
#   "latency_ms": 48.7,      <--- Re-executed (data changed)
#   "cached": false,
#   "rows_count": 3          <--- Now includes "Keyboard"
# }
```

### Test 3: Cost Estimation

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM test_products",
    "dry_run": false
  }'

# Response includes:
# {
#   "cost": 120.5,           <--- From EXPLAIN plan
#   "latency_ms": 42.1       <--- Includes EXPLAIN overhead (~5ms)
# }
```

### Test 4: Budget Enforcement

Assuming user has daily budget of 50,000 cost units:

**View current usage:**

```bash
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "user_id": "testuser",
#   "daily_budget": 50000,
#   "current_usage": 0.0,
#   "remaining": 50000.0,
#   "resets_at": "2026-03-27T00:00:00Z"
# }
```

**Execute expensive query:**

```bash
# Assume full-table scan costs 45,000 units
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) FROM very_large_table"}'

# Response:
# {
#   "cost": 45000,
#   "latency_ms": 2345.6,
#   "cached": false
# }
```

**Try another query (exceeds budget):**

```bash
# Another 10,000 units would exceed 50,000 total
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) FROM another_table"}'

# Response: 429 Too Many Requests
# {
#   "detail": "Daily query budget exceeded. Remaining: 5000.0 cost units. Resets at midnight UTC."
# }
```

### Test 5: Auto-LIMIT Injection

**Query without LIMIT:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT name FROM test_products"}'

# Gateway receives: "SELECT name FROM test_products"
# Internally executes: "SELECT name FROM test_products LIMIT 1000"
# Response: max 1000 rows
```

**Query with explicit LIMIT:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT name FROM test_products LIMIT 5"}'

# Not modified (already has LIMIT)
# Response: max 5 rows
```

### Test 6: Database Routing

**Verify SELECT uses replica:**

```bash
# Add hostname logging to query router, then:
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "SELECT inet_server_addr()"}'

# Should return: postgres_replica IP (e.g., 172.20.0.3)
```

**INSERT always uses primary:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "INSERT INTO test_products (name, price, category) VALUES (\"Chair\", 199.99, \"Furniture\")"}'

# Written to primary, replicated to replica
```

---

## Phase 3 Manual Tests

### Test 1: Analysis Payload Presence

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 as phase3_test"}' | jq '.analysis'

# Expected keys:
# scan_type, execution_time_ms, rows_processed, total_cost,
# slow_query, index_suggestions, complexity
```

### Test 2: Complexity Scoring

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users u JOIN roles r ON u.role_id=r.id"}' \
  | jq '.analysis.complexity'

# Expected: score > 0, level = medium/high depending query
```

### Test 3: Cache Hit Still Returns Analysis

```bash
curl -s -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 42 as cache_phase3"}' > /dev/null

curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 42 as cache_phase3"}' \
  | jq '{cached, analysis}'

# Expected: cached=true and analysis still present
```

### Test 4: Slow Query Logging + Admin Endpoint

```bash
# Run intentionally heavy query (adjust table/query for your data size)
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users u JOIN users u2 ON u.id = u2.id"}' | jq '.analysis.slow_query'

# As admin:
curl -X GET "http://localhost:8000/api/v1/admin/slow-queries?limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.items[0]'
```

---

## Load Testing (Phase 1 + 2 + 3)

```bash
# Start Locust with 100 concurrent users, 10 spawn rate, 60s duration
make load-test

# Or manually:
cd tests/load
locust -f locustfile.py --headless -u 100 -r 10 -t 60s

# Metrics:
# - Requests/sec
# - Response time (mean, min, max)
# - Cache hit rate
# - Errors (rate limiting, budget exceeded, SQL injection blocks)
# - Analysis payload consistency under load
```

See [locustfile.py](tests/load/locustfile.py) for load test definition.

---

## Debugging Failed Tests

### 1. Check Service Health

```bash
# Verify all services are running
docker-compose ps

# Expected:
# gateway        Up (listening on :8000)
# postgres       Up (Healthy)
# redis          Up (Healthy)
```

### 2. Check Logs

```bash
# Gateway logs
docker-compose logs gateway

# Database logs
docker-compose logs postgres

# Redis logs (if available)
docker-compose logs redis
```

### 3. Connect to Database Directly

```bash
# Enter postgres shell
docker-compose exec postgres psql -U queryx -d queryx

# Check tables exist
\dt

# Sample data
SELECT * FROM users LIMIT 5;
```

### 4. Run Single Test with Debug Output

```bash
pytest tests/unit/test_auth.py::test_create_and_decode_jwt -v -s

# -v = verbose
# -s = show print statements
```

### 5. Check Redis Connection

```bash
# Enter redis container
docker-compose exec redis redis-cli

# Check keys
KEYS *

# Check cache hits
GET siqg:cache:abc123:user1:admin

# Exit
QUIT
```

---

## Test Coverage Goals

### Phase 1: Minimum 70%

- Auth: 85% (`hash_password`, `decode_jwt`, `get_current_user`)
- Validator: 75% (SQL injection patterns)
- Rate Limiter: 80% (tracking, lockout logic)
- RBAC: 70% (permission matrix)

### Phase 2: Minimum 70%

- Fingerprinter: 85% (normalization, hashing)
- Cache: 75% (check, write, invalidation)
- Cost Estimator: 70% (EXPLAIN parsing)
- Budget: 75% (daily tracking, reset logic)

### Phase 3: Minimum 70%

- Analyzer: 70% (EXPLAIN parsing + seq scan extraction)
- Complexity: 80% (score/level rules)
- Query route intelligence response: 70%

### Check Current Coverage

```bash
make test
# Then open: htmlcov/index.html
```

---

## Expected Test Results

All tests pass = ✅ Phase 1 + 2 + 3 Complete

```
tests/unit/test_auth.py::test_hash_api_key PASSED
tests/unit/test_auth.py::test_create_and_decode_jwt PASSED
tests/unit/test_auth.py::test_password_hashing PASSED
tests/unit/test_validator.py::test_sql_injection_blocked PASSED
tests/unit/test_validator.py::test_drop_table_blocked PASSED
tests/unit/test_rate_limiter.py::test_rate_limit_within_limit PASSED
tests/unit/test_rate_limiter.py::test_rate_limit_exceeded PASSED
tests/unit/test_rbac.py::test_admin_can_write PASSED
tests/unit/test_rbac.py::test_readonly_cannot_write PASSED
tests/unit/test_fingerprinter.py::test_query_fingerprint PASSED
tests/unit/test_fingerprinter.py::test_identical_fingerprints PASSED
tests/integration/test_full_pipeline.py::test_health_endpoint PASSED
tests/integration/test_full_pipeline.py::test_select_with_cache PASSED
tests/integration/test_full_pipeline.py::test_cache_invalidation PASSED
tests/integration/test_full_pipeline.py::test_budget_enforcement PASSED

====== 15 passed in 4.23s [coverage: 78%] ======
```

---

## One-Command Full Test Suite

```bash
#!/bin/bash
set -e

echo "🚀 Starting Phase 1 + 2 + 3 Test Suite..."

# 1. Bring up services
echo "📦 Starting Docker services..."
docker-compose up -d
sleep 15

# 2. Run unit tests
echo "✅ Running unit tests..."
make test

# 3. Run integration tests
echo "🔄 Running integration tests..."
pytest tests/integration/ -v

# 4. Optional: Load test (comment out if not needed)
# echo "⚡ Running load tests..."
# make load-test

# 5. Clean up
echo "🧹 Cleaning up..."
docker-compose down

echo "✨ Phase 1 + 2 + 3 Test Suite Complete!"
```

Save as `run_tests.sh` and execute:

```bash
chmod +x run_tests.sh
./run_tests.sh
```
