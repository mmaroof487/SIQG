# Phase 1, 2 & 3 Verification Guide

## Quick Start (3 minutes)

### Step 1: Start Services

```bash
docker-compose up -d
```

Verify all services are healthy:

```bash
docker-compose ps
```

Expected output:

```
CONTAINER ID   IMAGE              STATUS              NAMES
xxx            siqg-gateway       Up                  siqg-gateway-1
xxx            postgres:15        Up (Healthy)        siqg-postgres-1
xxx            postgres:15        Up                  siqg-postgres_replica-1
xxx            redis:7            Up (Healthy)        siqg-redis-1
```

---

### Step 2: Run Test Script

```bash
./test_features.sh
```

This will register a test user and run all Phase 1/2/3 tests automatically.

---

## Detailed Verification

### Phase 1: Security Layer

#### Test 1.1: SQL Injection Detection ✅

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","email":"u1@test.com","password":"pass1234"}' | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users WHERE id = 1 OR 1=1"}' | jq .
```

**Expected**: 400 Bad Request with `"Potential SQL injection detected"`

---

#### Test 1.2: Query Type Blocking ✅

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"DROP TABLE users"}' | jq .
```

**Expected**: 400 Bad Request with `"Potential SQL injection detected"` or similar blocking message

---

#### Test 1.3: Rate Limiting (60 req/min) ✅

```bash
# Make 65 rapid requests - request 61+ should fail
for i in {1..65}; do
  curl -s -X POST http://localhost:8000/api/v1/query/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query":"SELECT 1"}' > /dev/null 2>&1
done

# Also check individual request
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1"}' | jq '.detail'
```

**Expected after 60 requests**: 429 Too Many Requests with rate limit message

---

#### Test 1.4: Valid Query Works ✅

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS result"}' | jq .
```

**Expected**: 200 OK with valid response:

```json
{
	"trace_id": "abc-123...",
	"query_type": "SELECT",
	"rows": [{ "result": 1 }],
	"rows_count": 1,
	"latency_ms": 45.2,
	"cached": false,
	"slow": false,
	"cost": 120.5
}
```

✅ **Phase 1 Success Criteria**:

- SQL injection blocked
- DROP TABLE blocked
- Valid queries execute
- Rate limiting enforced

---

## Phase 2: Performance Layer

#### Test 2.1: Cache Hit Detection ✅

**First query (CACHE MISS)**:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS test"}' | jq '{latency_ms, cached, cost}'
```

**Expected output**:

```json
{
	"latency_ms": 45.2,
	"cached": false,
	"cost": 120.5
}
```

**Identical query again (CACHE HIT)**:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS test"}' | jq '{latency_ms, cached, cost}'
```

**Expected output**:

```json
{
	"latency_ms": 2.3,
	"cached": true,
	"cost": 120.5
}
```

✅ **Key indicator**: `latency_ms` should drop from ~45ms to ~2-5ms

---

#### Test 2.2: Cache Invalidation ✅

After the second query above, execute:

```bash
# Modify data (invalidates cache)
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"INSERT INTO test_cache VALUES (1, 1)"}' 2>/dev/null || true

# Query again - should be cache miss
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS test"}' | jq '{latency_ms, cached}'
```

**Expected output**:

```json
{
	"latency_ms": 48.3,
	"cached": false
}
```

✅ **Key indicator**: After write, cache is invalidated and `cached: false` on next query

---

#### Test 2.3: Budget Tracking ✅

```bash
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected output**:

```json
{
	"user_id": "user_id_here",
	"daily_budget": 50000,
	"current_usage": 241.0,
	"remaining": 49759.0,
	"resets_at": "2026-03-27T00:00:00Z"
}
```

✅ **Key indicators**:

- `current_usage` increases with each query
- `remaining` decreases accordingly
- `daily_budget` is 50000 (default)
- `resets_at` shows tomorrow at midnight UTC

---

#### Test 2.4: Cost Estimation ✅

Same as Test 2.1 - the `"cost"` field comes from EXPLAIN plan:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS test"}' | jq '.cost'
```

**Expected**: A number like `120.5` (from PostgreSQL EXPLAIN)

✅ **Key indicator**: Cost value should be reasonable (100-10000 for simple queries)

---

## Phase 3: Intelligence Layer

#### Test 3.1: Analysis Payload ✅

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS phase3"}' | jq '.analysis'
```

**Expected**: `analysis` contains `scan_type`, `execution_time_ms`, `rows_processed`, `total_cost`, `index_suggestions`, `complexity`

---

#### Test 3.2: Complexity Scoring ✅

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users u JOIN roles r ON u.role_id = r.id"}' \
  | jq '.analysis.complexity'
```

**Expected**: score > 0, level present, reasons list present

---

#### Test 3.3: Analysis on Cache Hit ✅

```bash
curl -s -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 42 as cache_phase3"}' > /dev/null

curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 42 as cache_phase3"}' | jq '{cached, analysis}'
```

**Expected**: `cached=true` and `analysis` still present

---

## Verification Using Logs

### Watch Real-Time Activity

```bash
# Terminal 1: Watch logs
docker-compose logs -f gateway | grep -E "(Cache|Cost|Budget|LIMIT|Fingerprint)"
```

### Example Log Output (Phase 2/3):

```
[trace-id] Cache MISS: abc123...
[trace-id] Cost estimate: 120.50 (warning: false)
[trace-id] Budget check passed for user1: 120.50 / 50000
[trace-id] Query executed in 45.2ms
[trace-id] Cache SET: siqg:cache:abc123:user1:readonly

[trace-id] Cache HIT: abc123...
[trace-id] ✅ Cache HIT - returning cached result (2.1ms)
[trace-id] analysis.scan_type: Seq Scan
[trace-id] analysis.complexity.level: medium
```

---

## Redis Verification

### Check Cache Keys

```bash
docker-compose exec redis redis-cli

# In redis-cli shell:
KEYS siqg:cache:*
# Shows all cached queries

GET siqg:cache:abc123:user1:readonly
# Shows the cached result

KEYS siqg:budget:*
# Shows budget tracking

GET siqg:budget:user1:2026-03-26
# Shows today's usage
```

---

## PostgreSQL Verification

### Check Audit Log

```bash
docker-compose exec postgres psql -U queryx -d queryx

# In psql shell:
SELECT trace_id, user_id, query_type, latency_ms, cached, slow
FROM audit_log
ORDER BY created_at DESC
LIMIT 10;
```

**Expected output**:

```
trace_id             | user_id | query_type | latency_ms | cached | slow
---------------------+---------+------------+------------+--------+-----
abc-123-def         | user1   | SELECT     | 2.1        | t      | f
def-456-ghi         | user1   | SELECT     | 45.2       | f      | f
ghi-789-jkl         | user1   | INSERT     | 15.3       | f      | f
```

---

## Success Checklist

### Phase 1 ✅

- [ ] SQL injection queries blocked (400)
- [ ] DROP TABLE blocked (400)
- [ ] Valid SELECT works (200)
- [ ] Rate limiting enforced after 60 requests
- [ ] Logs show security validations

### Phase 2 ✅

- [ ] First query: `cached: false`, latency ~45ms
- [ ] Same query 2x: `cached: true`, latency ~2-5ms
- [ ] Budget endpoint returns 200 OK
- [ ] Current usage increases with each query
- [ ] Cost field has reasonable values (100-1000)
- [ ] Redis has cache keys: `siqg:cache:*`
- [ ] PostgreSQL audit_log table has entries

### Phase 3 ✅

- [ ] Response includes `analysis` object
- [ ] `analysis.complexity.level` returned for SELECT
- [ ] `analysis.index_suggestions` present (array)
- [ ] Cache hits still return analysis

---

## Troubleshooting

| Issue                 | Solution                                                           |
| --------------------- | ------------------------------------------------------------------ |
| `Token: null`         | Run `/register` endpoint first                                     |
| `Budget endpoint 404` | Restart gateway: `docker-compose restart gateway`                  |
| `Cache always false`  | Check Redis connection: `docker-compose exec redis redis-cli ping` |
| `Latency very high`   | Normal on first run; should drop to 2-5ms on cache hit             |
| `No audit logs`       | Check if `audit_log` table exists: `\dt` in psql                   |

---

## One-Command Test Everything

```bash
#!/bin/bash
# Save as: test_all.sh

echo "🚀 Phase 1 + 2 + 3 Full Test"

# Start services
docker-compose up -d --remove-orphans
sleep 25

# Run automated test
./test_features.sh

# Show budget
echo ""
echo "📊 Budget Status:"
TOKEN=$(curl -s -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"testfinal","email":"test@final.com","password":"pass1234"}' | jq -r '.access_token')" | jq .)

# Show redis cache keys
echo ""
echo "💾 Redis Cache Keys:"
docker-compose exec -T redis redis-cli KEYS 'siqg:cache:*' | wc -l
echo "   cache entries in Redis"

# Show audit log
echo ""
echo "📝 Audit Log (last 5 entries):"
docker-compose exec -T postgres psql -U queryx -d queryx -c "SELECT trace_id, query_type, latency_ms, cached FROM audit_log ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo "   (Audit table may be empty on first run)"

echo ""
echo "✨ Test Complete!"
```

Run it:

```bash
chmod +x test_all.sh
./test_all.sh
```

---

## Expected Results Summary

| Phase | Feature        | Test Command       | Success Indicator                    |
| ----- | -------------- | ------------------ | ------------------------------------ |
| 1     | SQL Injection  | `OR 1=1` query     | 400 response                         |
| 1     | Query Blocking | `DROP TABLE`       | 400 response                         |
| 1     | Rate Limit     | 65 queries in loop | 429 on 61+                           |
| 2     | Cache Miss     | First SELECT query | `cached: false`                      |
| 2     | Cache Hit      | Same query 2x      | `cached: true`, latency 2-5ms        |
| 2     | Budget         | `/budget` endpoint | 200 with budget values               |
| 2     | Cost           | Any query          | `cost` field present                 |
| 3     | Analysis       | Any SELECT query   | `analysis` object with required keys |
| 3     | Complexity     | JOIN query         | `analysis.complexity.level` present  |

---

## Next Steps

Once Phase 1, 2 and 3 are verified:

- ✅ Commit changes to git
- ✅ Update README with test results
- ✅ Move to Phase 4 (alerts and observability expansion)

---

**Questions?** Check logs with:

```bash
docker-compose logs gateway | tail -50
```
