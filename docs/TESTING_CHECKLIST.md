# Phase 1, Phase 2 & Phase 3 Testing Checklist

Use this checklist to verify all Phase 1, 2 and 3 features are working correctly.

---

## Quick Links

- **Full Testing Guide**: [TESTING_PHASE1_PHASE2.md](TESTING_PHASE1_PHASE2.md)
- **Phase 1 Details**: [PHASE1_COMPLETION.md](PHASE1_COMPLETION.md)
- **Phase 2 Details**: [PHASE2_COMPLETION.md](PHASE2_COMPLETION.md)
- **Phase 3 Details**: [PHASE3_COMPLETION.md](PHASE3_COMPLETION.md)

---

## Setup Checklist

- [ ] Clone repo and navigate to project root
- [ ] Create `.env` file with required variables
- [ ] Run `docker-compose up -d` and verify all services show "Up" and "Healthy"
- [ ] Run `make test` successfully
- [ ] Check `docker-compose logs` for no error messages

---

## Phase 1: Security Layer ✅

### Authentication & JWT

- [ ] `POST /api/v1/auth/login` returns valid JWT token
- [ ] `decode_jwt()` correctly decodes token payload
- [ ] Invalid tokens return 401 Unauthorized
- [ ] Token expiry works (test with expired token)

### API Key Management

- [ ] API key hashing is consistent (same key → same hash)
- [ ] API key validation works (128-char SHA-256 hash)

### Brute Force Protection

- [ ] After 5 failed login attempts → 15-minute lockout
- [ ] Lockout returns 429 Too Many Requests
- [ ] Timer resets after 15 minutes
- [ ] Lockout applies per username (not IP)

### Rate Limiting (60 reqs/min)

- [ ] 60 requests/min allowed per authenticated user
- [ ] Request 61 → 429 Too Many Requests
- [ ] Rate limit resets after 1 minute
- [ ] Different users have separate limits

### IP Filtering

- [ ] Admin can add IPs to allow-list
- [ ] Admin can add IPs to block-list
- [ ] Blocked IPs → 403 Forbidden
- [ ] Non-listed IPs (when list exists) → 403 Forbidden

### SQL Injection Detection

- [ ] `SELECT * FROM users WHERE id = 1 OR 1=1` → 400 Bad Request
- [ ] `'; DROP TABLE users; --` → 400 Bad Request
- [ ] `UNION SELECT * FROM passwords` → 400 Bad Request
- [ ] Valid SELECT queries pass through

### Query Type Allowlist

- [ ] `SELECT * FROM users` → allowed ✅
- [ ] `INSERT INTO users (name) VALUES ('Bob')` → allowed ✅
- [ ] `DROP TABLE users` → 400 Bad Request
- [ ] `ALTER TABLE users ADD COLUMN` → 400 Bad Request
- [ ] `DELETE FROM users WHERE id = 1` → check if allowed in config

### RBAC (Role-Based Access Control)

- [ ] **Admin role**: Can SELECT, INSERT, UPDATE, DELETE
- [ ] **Readonly role**: Can SELECT only → 403 on INSERT
- [ ] **Guest role**: Limited SELECT only → 403 on most queries
- [ ] Column-level masking: sensitive columns hidden for Guest

---

## Phase 2: Performance Layer ✅

### Query Fingerprinting

- [ ] Same query twice generates same fingerprint
- [ ] `SELECT * FROM users WHERE id = 123`
- [ ] `SELECT * FROM users WHERE id = 456`
  - → Both have same fingerprint (values normalized)
- [ ] Different queries generate different fingerprints

### Redis Cache

- [ ] **First query**: `latency_ms=45, cached=false`
- [ ] **Same query 2x**: `latency_ms=2, cached=true` (2-5ms from Redis)
- [ ] Cache works with role-based permission filtering
- [ ] Cache TTL is 60 seconds (configurable)
- [ ] After TTL expires, cache miss on next query

### Cache Invalidation

- [ ] Execute: `SELECT * FROM products` → cached ✅
- [ ] Execute: `INSERT INTO products ...` → invalidates cache
- [ ] Next `SELECT * FROM products` → cache miss (must re-execute)
- [ ] Multi-table queries: invalidation works for all tables
- [ ] Unrelated table writes: don't invalidate unrelated cache

### Cost Estimation

- [ ] EXPLAIN runs before query execution
- [ ] Cost value returned in response (EXPLAIN "Total Cost")
- [ ] `latency_ms` includes EXPLAIN overhead (~5ms)
- [ ] High-cost queries trigger `cost_warning` flag
- [ ] Cost estimation doesn't execute the query

### Budget Enforcement (Daily Limit)

- [ ] Check `/api/v1/query/budget` shows daily_budget
- [ ] Execute multiple queries, `current_usage` increments
- [ ] When `current_usage + new_cost > daily_budget` → 429 error
- [ ] Budget resets at midnight UTC
- [ ] Budget key: `siqg:budget:{user_id}:{YYYY-MM-DD}`

### Auto-LIMIT Injection

- [ ] Query: `SELECT * FROM big_table`
  - → Modified to `SELECT * FROM big_table LIMIT 1000`
- [ ] Query: `SELECT * FROM big_table LIMIT 5`
  - → NOT modified (already has LIMIT)
- [ ] Default limit: 1000 rows (configurable)

### Database Routing

- [ ] SELECT queries routed to **replica** (read replica)
- [ ] INSERT/UPDATE/DELETE routed to **primary**
- [ ] Can verify with: `SELECT inet_server_addr()` → gives replica IP
- [ ] Write operations commit to primary only

---

## Phase 3: Intelligence Layer ✅

### EXPLAIN ANALYZE Metadata

- [ ] Response includes `analysis.scan_type`
- [ ] Response includes `analysis.execution_time_ms`
- [ ] Response includes `analysis.rows_processed`
- [ ] Response includes `analysis.total_cost`
- [ ] EXPLAIN failure does not fail primary request

### Index Recommendations

- [ ] `analysis.index_suggestions` is present (array)
- [ ] Suggestions include `table`, `column`, `reason`, `ddl`
- [ ] Duplicate suggestions are deduplicated
- [ ] Suggestions still available on cache hits

### Complexity Scoring

- [ ] `analysis.complexity.score` is returned
- [ ] `analysis.complexity.level` is one of `low/medium/high`
- [ ] `analysis.complexity.reasons` is populated for complex queries

### Slow Query Logging

- [ ] Slow queries set `analysis.slow_query=true` when threshold exceeded
- [ ] Slow query records are persisted
- [ ] Admin endpoint `GET /api/v1/admin/slow-queries` returns recent records

---

## Manual Testing: Curl Commands

### Get a Token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"pass123"}' | jq -r '.access_token')

echo $TOKEN  # Should print a JWT token
```

### Test SQL Injection Block

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT * FROM users WHERE id = 1 OR 1=1"}'

# Expected: 400 Bad Request
```

### Test Cache (Phase 2)

```bash
# First query (cache miss)
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT * FROM users LIMIT 10"}' | jq '.latency_ms, .cached'
# Output: 45.2, false

# Identical query (cache hit)
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"SELECT * FROM users LIMIT 10"}' | jq '.latency_ms, .cached'
# Output: 2.1, true
```

### Test Budget

```bash
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN" | jq'.daily_budget, .current_usage, .remaining'
```

---

## Automated Testing

### Run All Tests

```bash
make test
```

### Expected Output

```
tests/unit/test_auth.py::test_hash_api_key PASSED
tests/unit/test_auth.py::test_create_and_decode_jwt PASSED
tests/unit/test_validator.py::test_sql_injection_blocked PASSED
tests/unit/test_rate_limiter.py::test_rate_limit_exceeded PASSED
tests/unit/test_rbac.py::test_readonly_cannot_write PASSED
tests/unit/test_fingerprinter.py::test_identical_fingerprints PASSED
tests/integration/test_full_pipeline.py::test_cache_hit PASSED

====== 7 passed in 3.45s [coverage: 74%] ======
```

---

## Load Testing

Test Phase 2 caching under load:

```bash
make load-test
```

Expected:

- Cache hit rate: 40-60% (repeated queries)
- Response time (cached): 2-10ms
- Response time (uncached): 50-200ms
- No errors or timeouts

---

## Debugging Commands

### Check Services

```bash
docker-compose ps
docker-compose logs gateway     # Gateway logs
docker-compose logs postgres    # Database logs
```

### Check Database

```bash
docker-compose exec postgres psql -U queryx -d queryx

# In psql:
\dt                             # List tables
SELECT * FROM users LIMIT 5;    # Check data
SELECT * FROM audit_log LIMIT 5; # Check audit log
```

### Check Redis Cache

```bash
docker-compose exec redis redis-cli

# In redis-cli:
KEYS siqg:cache:*               # List cached queries
GET siqg:cache:abc123:user1:admin # Get specific cache entry
KEYS siqg:budget:*              # Check budget tracking
QUIT
```

---

## Success Criteria

✅ **Phase 1 PASS**:

- All 5 random authentication tests pass
- SQL injection blocked (5 patterns tested)
- Rate limiting enforced
- RBAC permissions working
- Query type allowlist enforced

✅ **Phase 2 PASS**:

- Cache hits return in <10ms
- Cache invalidation works (write triggers purge)
- Cost estimation shows reasonable values
- Budget enforcement blocks over-budget queries
- Auto-LIMIT prevents unbounded queries

✅ **Overall**:

- Unit test coverage ≥ 70%
- Integration tests all pass
- No errors in logs
- Load test completes without errors

---

## Testing Timeline

| Step              | Command                     | Expected Time |
| ----------------- | --------------------------- | ------------- |
| Spin up services  | `docker-compose up -d`      | 15s           |
| Unit tests        | `make test`                 | 5-10s         |
| Integration tests | `pytest tests/integration/` | 10-15s        |
| Manual curl test  | 5-10 API calls              | 2-3s          |
| Load test         | 100 users, 60s              | 60s           |
| **Total**         |                             | ~2-3 min      |

---

## Common Issues & Fixes

| Issue                       | Cause                      | Fix                                    |
| --------------------------- | -------------------------- | -------------------------------------- |
| `postgres not healthy`      | DB startup slow            | Wait 20s instead of 15s                |
| `Connection refused :5432`  | DB container not running   | `docker-compose up -d`                 |
| `Redis timeout`             | Redis not running          | Check `docker-compose ps`              |
| `JWT decode error`          | Secret key mismatch        | Verify `SECRET_KEY` in `.env`          |
| `SQL injection not blocked` | Regex pattern not matching | Check `security/validator.py` patterns |
| `Cache returns stale data`  | TTL not working            | Verify Redis TTL commands              |

---

## Checkpoint: Ready for Phase 4?

Before starting Phase 4, verify:

- [ ] All Phase 1 security tests pass
- [ ] All Phase 2 performance tests pass
- [ ] All Phase 3 intelligence tests pass
- [ ] Test coverage ≥ 70%
- [ ] No errors in application logs
- [ ] Cache hit rate >30% in load test
- [ ] Budget enforcement working correctly

If all checkboxes ✅, proceed to Phase 4!
