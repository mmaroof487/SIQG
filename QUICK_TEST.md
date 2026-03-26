# Phase 1 & 2 Quick Test Card

## 60-Second Test

```bash
# 1. Start services
docker-compose up -d && sleep 25

# 2. Register user & get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","email":"test@test.com","password":"pass1234"}' | jq -r '.access_token')

# 3. Test SQL Injection (BLOCKED)
curl -s -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT * WHERE 1=1"}' | jq '.detail'
# ✅ Should show: "Potential SQL injection detected"

# 4. Test Cache Miss → Hit
curl -s -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT 1"}' | jq '{latency_ms, cached}'
# First: latency_ms: 45.2, cached: false

curl -s -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT 1"}' | jq '{latency_ms, cached}'
# Second: latency_ms: 2.1, cached: true ✅

# 5. Check Budget
curl -s -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN" | jq '.remaining'
# ✅ Should show amount less than 50000
```

---

## What Each Test Shows

| Test          | Phase | What It Tests            | Success =              |
| ------------- | ----- | ------------------------ | ---------------------- |
| SQL Injection | 1     | Blocks dangerous queries | 400 response           |
| Query Type    | 1     | Blocks DROP/ALTER        | 400 response           |
| Cache Miss    | 2     | First query slow         | `cached: false`        |
| Cache Hit     | 2     | Second query fast        | `cached: true` + 2-5ms |
| Budget        | 2     | Daily cost tracking      | `remaining < 50000`    |

---

## Key Metrics to Watch

✅ **Phase 1 Success**:

- Attack queries → 400 Bad Request
- Valid queries → 200 OK
- Rate limit → 429 after 60 req/min

✅ **Phase 2 Success**:

- Cache hit latency: **2-5ms** (vs 45-150ms miss)
- Cost value: **100-1000** for simple queries
- Budget: **Decreases with each query**
- Cache HIT flag: **true on identical queries**

---

## Check Full Logs

```bash
# Watch Phase 2 activity in real-time
docker-compose logs -f gateway | grep -E "(Cache|Cost|Budget)"
```

Expected output:

```
[trace-id] Cache MISS: abc123...
[trace-id] Cost estimate: 120.50
[trace-id] Budget check passed: 120.50 / 50000
[trace-id] Cache SET with 60s TTL

[trace-id] Cache HIT: abc123...  ← Second identical query
```

---

## Verify in Redis

```bash
docker-compose exec redis redis-cli
```

Then:

```redis
KEYS siqg:cache:*
# ✅ Should list cached query keys

GET siqg:budget:test:2026-03-26
# ✅ Should show cost units used today (e.g., "241.0")

QUIT
```

---

## Verify in PostgreSQL

```bash
docker-compose exec postgres psql -U queryx -d queryx
```

Then:

```sql
SELECT trace_id, query_type, latency_ms, cached
FROM audit_log
ORDER BY created_at DESC LIMIT 5;

-- ✅ Should show execution history with cache status
```

---

## Expected Output Example

```json
{
	"trace_id": "a1b2c3d4-e5f6-4789-0abc-def123456789",
	"query_type": "SELECT",
	"rows": [{ "1": 1 }],
	"rows_count": 1,
	"latency_ms": 2.1,
	"cached": true,
	"slow": false,
	"cost": 120.5,
	"recommended_index": null
}
```

**Key checks**:

- ✅ `cached: true` on 2nd identical query
- ✅ `latency_ms: 2.1` (down from ~45ms)
- ✅ `cost: 120.5` (from EXPLAIN)
- ✅ `trace_id` in audit log

---

## Stop Everything

```bash
docker-compose down -v
```

---

## Full Documentation

- [VERIFICATION_GUIDE.md](VERIFICATION_GUIDE.md) — Detailed tests
- [TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) — Checkbox format
- [TESTING_PHASE1_PHASE2.md](docs/TESTING_PHASE1_PHASE2.md) — Comprehensive guide
- [PHASE2_IMPLEMENTATION.md](docs/PHASE2_IMPLEMENTATION.md) — Architecture details
