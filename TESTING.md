# Argus Testing Guide

This guide explains how to test all 32 features of Argus across 6 tiers.

---

## Test Scripts Overview

| Script | Duration | Use Case | Output |
|--------|----------|----------|--------|
| **quick_test.sh** | 1-2 min | ✅ Verify system is up | Pass/fail summary (7 core features) |
| **test_user.sh** | 3-5 min | 📚 Learn all features | Detailed inputs/outputs for all 32 steps |
| **test_all_32_features.sh** | 5-10 min | 🚀 Full validation | Comprehensive test results with tallies |
| **demo_cli.sh** | 2 min | 🎬 Show walkthrough | CLI user journey (8 steps) |

---

## Prerequisites

Before running any test, ensure:

1. **Docker & Docker Compose installed**
   ```bash
   docker --version
   docker compose --version
   ```

2. **Services running**
   ```bash
   docker compose up --build
   # Wait 20-30 seconds for all services to initialize
   ```

3. **Basic tools available**
   - `bash` shell
   - `curl` command
   - `jq` JSON processor (usually pre-installed)

---

## Test #1: Quick Validation (Fastest)

**Use when:** You just need to verify the system got installed correctly

**Time:** 1-2 minutes

**Run:**
```bash
bash quick_test.sh
```

**What it tests:**
- Query execution
- SQL injection detection
- Query caching
- Budget tracking
- Live metrics
- AI NL→SQL
- Query explanation

**Expected output:**
```
Checking gateway...
✅ Gateway running

[1/7] Testing basic query execution...
✅ Query execution
[2/7] Testing SQL injection detection...
✅ Injection blocking
...
╔════════════════════════════════════════════════════════════╗
║ Quick Test Summary                                         ║
╚════════════════════════════════════════════════════════════╝
✅ Passed: 7/7
❌ Failed: 0/7
🎉 All systems operational!
```

---

## Test #2: Interactive User Demo (Learning)

**Use when:** You want to understand what each feature does with real input/output examples

**Time:** 3-5 minutes

**Run:**
```bash
bash test_user.sh
```

**What it shows:**

For every feature, you see:
- **Request:** The API call being made (e.g., POST endpoint, query parameters)
- **Response:** The actual JSON response from the server
- **Result:** Pass/fail with explanation

**Example output:**
```
▶ Step 1-5: Basic Query Execution & Trace ID
Request:
  POST /api/v1/query/execute
  Query: SELECT id, username FROM users LIMIT 2
Response:
  {
    "rows": [{"id": 1, "username": "alice"}, ...],
    "rows_count": 2,
    "trace_id": "a1b2c3d4-...",
    "latency_ms": 12.3,
    "cached": false
  }
✅ PASS │ Query executes with trace_id (a1b2...)

▶ Step 2-3: SQL Injection Detection & Blocking
Request:
  POST /api/v1/query/execute
  Query: SELECT * FROM users WHERE id = 1 OR 1=1
Response:
  {
    "detail": "Potential SQL injection detected: OR 1=1 pattern"
  }
✅ PASS │ SQL injection detected and blocked
...

╔════════════════════════════════════════════════════════════╗
║ TEST SUMMARY                                               ║
╚════════════════════════════════════════════════════════════╝
✅ Passed: 32
❌ Failed: 0
🎉 ALL TESTS PASSED!

All 32 Argus features verified:
  ✅ Tier 1 (Security: Steps 1-5)
  ✅ Tier 2 (Performance: Steps 6-10)
  ✅ Tier 3 (Execution: Steps 11-15)
  ✅ Tier 4 (Observability: Steps 16-19)
  ✅ Tier 5 (Hardening: Steps 20-24)
  ✅ Tier 6 (AI & Polish: Steps 25-32)
```

---

## Test #3: Comprehensive Automated Test (Most Thorough)

**Use when:** You need complete validation of all 32 features with detailed checks

**Time:** 5-10 minutes

**Run:**
```bash
bash test_all_32_features.sh
```

**What it tests:**

Validates all 32 integration steps grouped by tier:

**Tier 1: Security (Steps 1-5)**
- SENSITIVE_FIELDS constant centralization
- Sensitive column blocking (hashed_password, token, api_key)
- PII masking on NL→SQL path
- Pipeline order (decrypt → mask)
- Shell script verification

**Tier 2: Performance (Steps 6-10)**
- NL→SQL with pattern matching guardrails
- Query explanation quality
- Groq provider with mock fallback
- Dry-run mode verification
- Explainable error blocks

**Tier 3: Execution (Steps 11-15)**
- React app scaffold
- NL→SQL UI panel
- Results table with pagination & masking
- Live metrics dashboard
- Health status page

**Tier 4: Observability (Steps 16-19)**
- CI/CD badge (GitHub Actions)
- Load test results (P95 latency)
- README documentation
- CLI demo script

**Tier 5: Hardening (Steps 20-24)**
- Cache tag SSCAN cleanup
- Slow query advisor with merged recommendations
- Per-role rate limits (admin 500/min, readonly 60/min, guest 10/min)
- API key scoping (allowed_tables, allowed_query_types)
- Query whitelist mode

**Tier 6: Polish & Differentiation (Steps 25-32)**
- Time-based access rules with timezone support
- Query diff viewer (side-by-side + inline modes)
- Dry-run panel with pipeline checklist
- Index DDL suggestions with copy button
- Admin dashboard (7 tabs: audit log, slow queries, budget, IP rules, users, whitelist, compliance)
- HMAC request signing (X-Timestamp + X-Signature, timing-attack safe)
- Compliance report export (JSON/CSV formats)
- AI anomaly explanation (severity auto-detection, LLM-powered)

**Expected output:**
```
════════════════════════════════════════════════════════════
             🧪 ARGUS ALL 32 FEATURES TEST SUITE
════════════════════════════════════════════════════════════

Testing comprehensive coverage of Tiers 1-6 (all integration steps)
Estimated runtime: 5-10 minutes

Checking gateway service...
✅ Gateway is running

════════════════════════════════════════════════════════════
SETUP: Test User & Tokens
════════════════════════════════════════════════════════════

✅ PASS - User registration/login successful

════════════════════════════════════════════════════════════
🔴 TIER 1: SECURITY (Steps 1-5)
════════════════════════════════════════════════════════════

✅ PASS - Basic query with trace_id
✅ PASS - SQL injection detection
✅ PASS - Sensitive field blocking
✅ PASS - RBAC masking
✅ PASS - Pipeline order verification
...
════════════════════════════════════════════════════════════
🎉 TEST RESULTS
════════════════════════════════════════════════════════════

✅ Passed: 32
❌ Failed: 0
Total Tests: 32
Success Rate: 100%

🎉 ALL TESTS PASSED!

All 32 Argus features verified:
  ✅ Tier 1 (Security: Steps 1-5)
  ✅ Tier 2 (Performance: Steps 6-10)
  ✅ Tier 3 (Execution: Steps 11-15)
  ✅ Tier 4 (Observability: Steps 16-19)
  ✅ Tier 5 (Hardening: Steps 20-24)
  ✅ Tier 6 (AI & Polish: Steps 25-32)
```

---

## Test #4: CLI Demo Walkthrough

**Use when:** You want to show a realistic user journey through the system

**Time:** 2 minutes

**Run:**
```bash
bash demo_cli.sh
```

**What it demonstrates:**

1. **User Registration** - Create a new account
2. **Login** - Authenticate and get token
3. **Token Refresh** - Extend session
4. **Execute Query** - Run SQL with security checks
5. **NL→SQL** - Ask in plain English, get SQL back
6. **Explain Query** - Get explanation of any SQL
7. **Dry-Run Mode** - Check cost before executing
8. **Health Check** - Verify all components running
9. **Live Metrics** - View performance statistics

**Perfect for:** Demos, presentations, interviews

---

## Manual Testing with curl

You can also test endpoints directly without scripts:

### Register a user
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username":"testuser",
    "email":"test@example.com",
    "password":"SecurePass123!"
  }'
```

### Get authentication token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username":"testuser",
    "password":"SecurePass123!"
  }' | jq -r '.access_token'
```

### Execute a query
```bash
TOKEN="your_token_here"

curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users LIMIT 5"}'
```

### Test SQL injection blocking
```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users WHERE id = 1 OR 1=1"}'
# Should return error: "SQL injection detected: OR 1=1 pattern"
```

### Try NL→SQL (natural language to SQL)
```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me users created in the last 7 days"}'
```

### Explain a query
```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT role, COUNT(*) FROM users GROUP BY role"}'
```

### Check budget
```bash
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN"
```

### View live metrics
```bash
curl -X GET http://localhost:8000/api/v1/metrics/live \
  -H "Authorization: Bearer $TOKEN"
```

### Check system health
```bash
curl http://localhost:8000/health
```

---

## Unit Tests

Run the pytest test suite:

```bash
# Inside Docker container
docker compose exec gateway python -m pytest tests/ -v

# Or locally (with Python venv)
cd gateway
python -m pytest tests/ -v
```

**Current status:**
- 134 tests total
- 71%+ code coverage
- All Tiers (1-6) included
- Fully automated in CI/CD

---

## Testing Checklist

- [ ] Start Docker: `docker compose up --build`
- [ ] Quick test: `bash quick_test.sh` (1-2 min)
- [ ] Interactive demo: `bash test_user.sh` (3-5 min)
- [ ] Comprehensive test: `bash test_all_32_features.sh` (5-10 min)
- [ ] Manual curl tests: Verify specific features
- [ ] Unit tests: `docker compose exec gateway pytest` (2-3 min)

---

## Troubleshooting

### Gateway won't start
```bash
# Check logs
docker compose logs gateway

# Rebuild from scratch
docker compose down -v
docker compose up --build
```

### Tests fail with connection error
```
❌ ERROR: Gateway is not running on port 8000
```
Solution: Make sure services are fully running before starting tests
```bash
docker compose logs  # Wait for "Application startup complete"
```

### jq not found
Install jq (for JSON parsing):
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Windows (in WSL2)
sudo apt-get install jq
```

### curl not found
curl is usually pre-installed, but if missing:
```bash
# macOS
brew install curl

# Ubuntu/Debian
sudo apt-get install curl
```

---

## Performance Benchmarks

From load testing (see `tests/load/locustfile.py`):

| Metric | Value |
|--------|-------|
| Requests per second | 74.1 req/s |
| P50 latency | 6.23 ms |
| P95 latency | 28.55 ms |
| P99 latency | 89.34 ms |
| Cache speedup (hit) | 8-10× faster |
| Success rate | 100% |

---

## Next Steps

After verification:
1. Review [docs/userguide.md](docs/userguide.md) for detailed feature walkthrough
2. Check [docs/TIER6_FEATURES_GUIDE.md](docs/TIER6_FEATURES_GUIDE.md) for advanced features
3. Explore [docs/diagram/](docs/diagram/) for architecture details
4. Read [integration_plan.md](docs/integration_plan.md) for implementation status
