# Argus — Secure Intelligent Query Gateway

> A 6-layer database middleware in Python/FastAPI that sits between clients and PostgreSQL.
> Every query passes through security, performance, execution, observability, security hardening, and AI intelligence layers.

![Phase 6: AI + Polish](https://img.shields.io/badge/Phase-6%20Complete-gold)
![Tests](https://img.shields.io/badge/Tests-134%20Passing-brightgreen)
![Coverage](https://img.shields.io/badge/Coverage-71%25-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Async](https://img.shields.io/badge/Async-%E2%9C%93%20Correct-green)
![Deprecations](https://img.shields.io/badge/Deprecations-Zero-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- Python 3.11+ (tested on 3.14.2)
- Make (optional, for convenience commands)

### Code Quality

✅ **Production-Ready**

- Zero async/await warnings (all coroutines properly awaited)
- Zero deprecation warnings (Pydantic v2+, bcrypt-only passlib)
- 134 unit + integration tests passing (6 phases)
- 71%+ code coverage (focused on critical paths: security, execution, caching)
- Exponential backoff retry mechanism for resilience
- Fire-and-forget audit logging (zero query impact)
- Python SDK (programmatic access)
- CLI tool (argus command)
- AI endpoints (NL→SQL, Query Explainer)

### Start the Gateway (1 command)

```bash
docker compose up --build
```

This starts:

- **Gateway** at `http://localhost:8000` (FastAPI + lifespan)
- **Postgres Primary** at `localhost:5432` (write DB)
- **Postgres Replica** at `localhost:5433` (read DB)
- **Redis** at `localhost:6379` (cache + sessions)

### First Query (3 steps)

**Step 1: Register a user**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"Test@1234"}'
```

Response:

```json
{
	"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
	"token_type": "bearer",
	"role": "readonly"
}
```

**Step 2: Run a SELECT query**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 AS result"}'
```

Response:

```json
{
	"trace_id": "a1b2c3d4-...",
	"query_type": "SELECT",
	"rows": [{ "result": 1 }],
	"rows_count": 1,
	"latency_ms": 2.5,
	"cached": false,
	"slow": false
}
```

**Step 3: Try a DROP query (should be blocked)**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query":"DROP TABLE users"}'
```

Response:

```json
{
	"detail": "DROP queries are not allowed"
}
```

Status: **400 Bad Request** ✓

---

## Architecture — 5-Layer Pipeline

```
Incoming Request
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: SECURITY                                       │
│ - JWT/API Key auth                                      │
│ - Brute force protection (Redis, 5 attempts lockout)    │
│ - IP allow/blocklist (Redis sets)                       │
│ - Rate limiting (rolling window, anomaly detection)     │
│ - Query validation (SQL injection, type blocklist)      │
│ - RBAC (role → table/column access)                     │
│ - Honeypot detection (Phase 5) 🔒                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ LAYER 2: PERFORMANCE                                    │
│ - Query fingerprinting (normalize → SHA-256)            │
│ - Redis cache with table-tagged invalidation            │
│ - Auto-LIMIT injection (prevent unbounded SELECT)       │
│ - Pre-flight EXPLAIN cost estimation                    │
│ - Daily query budget per user (Redis counter)           │
│ - Column encryption (Phase 5) 🔐                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ LAYER 3: EXECUTION                                      │
│ - Circuit breaker (3-state, Redis persistence) (Phase 5)│
│ - Read/write routing (SELECT → replica, write → primary)│
│ - Connection pooling (asyncpg, min=5, max=20)           │
│ - Retry logic + exponential backoff (Phase 5) 🔄        │
│ - EXPLAIN ANALYZE parsing (JSON format)                 │
│ - Index recommendation engine (rule-based)              │
│ - Column decryption (Phase 5) 🔓                        │
│ - Role-based PII masking (Phase 5) 👤                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ LAYER 4: OBSERVABILITY                                  │
│ - Immutable audit log (append-only, Postgres)           │
│ - Distributed trace IDs (UUID per request)              │
│ - Structured JSON logging                               │
│ - Redis metrics counters (served via /api/v1/metrics)   │
│ - Slow query detection (>200ms flagged)                 │
│ - Table access heat map                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ LAYER 5: SECURITY HARDENING (Phase 5) 🛡️               │
│ - Fire-and-forget audit logging (asyncio.create_task)   │
│ - AES-256-GCM column encryption management              │
│ - Circuit breaker persistence & recovery                │
│ - Honeypot & intrusion detection                        │
│ - Automatic IP blocking on suspicious activity          │
│ - Webhook alerting for security events                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ LAYER 6: AI + INTELLIGENCE (Phase 6) 🤖                │
│ - Natural Language → SQL conversion (OpenAI/GPT-4o-mini)│
│ - Query explanation (plain English via LLM)             │
│ - Dry-run mode (validate + cost est., no execution)     │
│ - Python SDK (standalone package, pip install-able)     │
│ - CLI tool (argus command - login, query, status, etc)  │
│ - Full pipeline integration for AI outputs              │
│ - Comprehensive test suite (22 AI/SDK tests)            │
└────────────────────┬────────────────────────────────────┘
                     │
                Response Returned
```

---

## Phase 1: Foundation (Complete)

### What Works

- ✅ JWT login + registration
- ✅ API key auth (with rotation placeholder)
- ✅ Brute force protection (423 Locked after 5 failures)
- ✅ IP allow/blocklist (Redis sets, configurable)
- ✅ Rate limiter (rolling window + anomaly detection)
- ✅ SQL injection detection (regex patterns)
- ✅ Query type blocker (SELECT + INSERT only by default)
- ✅ RBAC (Admin / Readonly / Guest roles)
- ✅ Column-level access control (role → allowed columns)
- ✅ PII masking (SSN → **\*-**-6789, etc.)
- ✅ Query fingerprinting (normalize → SHA-256)
- ✅ Redis cache with table-tagged invalidation
- ✅ Auto-LIMIT injection (prevents unbounded SELECT)
- ✅ Circuit breaker (3-state: closed/open/half-open)
- ✅ R/W routing (SELECT → replica, INSERT → primary)
- ✅ EXPLAIN ANALYZE parser (JSON output)
- ✅ Audit logging (append-only in Postgres)
- ✅ Trace IDs (UUID per request)
- ✅ Health check (DB + Redis ping)

### Testing

**Unit tests** (no DB required):

```bash
make test-unit
```

**Integration tests** (requires Docker):

```bash
make test-integration
```

**All tests with coverage**:

```bash
make test
```

---

## API Reference

### Auth Endpoints

**POST /api/v1/auth/register**

```json
{
	"username": "alice",
	"email": "alice@example.com",
	"password": "Test@1234" // 8+ chars
}
```

Returns: `{access_token, token_type, role}`

**POST /api/v1/auth/login**

```json
{
	"username": "alice",
	"password": "Test@1234"
}
```

Returns: `{access_token, token_type, role}`

### Query Endpoints

**POST /api/v1/query/execute**

```json
{
	"query": "SELECT * FROM users",
	"dry_run": false // Optional: validate without executing
}
```

Returns: `{trace_id, query_type, rows, rows_count, latency_ms, cached, slow}`

**GET /health**
Returns: `{status, service}`

**GET /api/v1/status**
Returns: `{status, redis}`

### Admin Endpoints

**POST /api/v1/admin/ip-rules** (requires admin role)

```json
{
	"ip_address": "192.168.1.100",
	"rule_type": "allow" // or "block"
}
```

**DELETE /api/v1/admin/ip-rules/{ip_address}**

**GET /api/v1/admin/metrics/live**
Returns: `{request_count, error_count, cache_hits, slow_queries}`

**GET /api/v1/admin/audit/export**
Returns: Streaming CSV of structural audit logs

**GET /api/v1/admin/heatmap**
Returns: Array of table access frequencies `[{"table": "name", "score": count}]`

**GET /api/v1/admin/slow-queries**
Returns: Recent slow queries with EXPLAIN ANALYZE data

---

## Configuration

All settings are loaded from `.env` (see `.env.example`):

| Variable                      | Default                     | Purpose                                 |
| ----------------------------- | --------------------------- | --------------------------------------- |
| `SECRET_KEY`                  | —                           | JWT signing key (change in production!) |
| `DB_PRIMARY_URL`              | postgres:5432               | Write database                          |
| `DB_REPLICA_URL`              | postgres_replica:5433       | Read database                           |
| `REDIS_URL`                   | redis:6379                  | Cache & sessions                        |
| `BRUTE_FORCE_MAX_ATTEMPTS`    | 5                           | Failed attempts before lockout          |
| `BRUTE_FORCE_LOCKOUT_MINUTES` | 15                          | Lockout duration                        |
| `RATE_LIMIT_PER_MINUTE`       | 60                          | Requests per user per minute            |
| `ENCRYPTION_KEY`              | —                           | AES-256-GCM key (32 chars)              |
| `ENCRYPT_COLUMNS`             | ssn,credit_card             | Columns to encrypt                      |
| `HONEYPOT_TABLES`             | secret_keys,admin_passwords | Tables that trigger alerts              |
| `AUTO_LIMIT_DEFAULT`          | 1000                        | Auto-LIMIT on unbounded SELECT          |
| `COST_THRESHOLD_WARN`         | 1000                        | EXPLAIN cost warning                    |
| `COST_THRESHOLD_BLOCK`        | 10000                       | EXPLAIN cost hard limit (admin exempt)  |
| `SLOW_QUERY_THRESHOLD_MS`     | 200                         | Latency threshold to flag as slow       |
| `DAILY_BUDGET_DEFAULT`        | 50000                       | Daily cost budget per user              |
| `CIRCUIT_FAILURE_THRESHOLD`   | 5                           | DB failures before circuit opens        |
| `CIRCUIT_COOLDOWN_SECONDS`    | 30                          | Cooldown before HALF_OPEN probe         |

---

## Development

### Add a test user

```bash
make shell-gateway
python
>>> from middleware.security.auth import hash_password
>>> from models import User
>>> from utils.db import PrimarySession
>>> import asyncio
>>> async def create_user():
...     async with PrimarySession() as session:
...         user = User(username="admin", email="admin@example.com", hashed_password=hash_password("Admin@123"), role="admin")
...         session.add(user)
...         await session.commit()
>>> asyncio.run(create_user())
```

### Run tests locally

```bash
cd gateway
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/ -v --cov=. --cov-report=html
```

### View logs

```bash
make logs
```

### Restart gateway

```bash
make restart
```

### Shell into database

```bash
make shell-db
```

---

## Project Structure

```
argus/
├── gateway/
│   ├── main.py                 # FastAPI app + lifespan
│   ├── config.py               # Settings (pydantic)
│   ├── requirements.txt         # Python dependencies
│   │
│   ├── middleware/
│   │   ├── security/           # Layer 1: auth, brute_force, validator, rbac, ip_filter, rate_limiter
│   │   ├── performance/        # Layer 2: fingerprinter, cache, auto_limit, cost_estimator, budget
│   │   ├── execution/          # Layer 3: circuit_breaker, executor, analyzer
│   │   └── observability/      # Layer 4: audit, metrics
│   │
│   ├── routers/
│   │   └── v1/                 # API v1 (auth, query, admin)
│   │
│   ├── models/                 # SQLAlchemy models (user, audit_log, sla_snapshot)
│   ├── utils/                  # Helpers (db, logger, redis)
│   │
│   └── migrations/             # Alembic (for schema evolution)
│
├── frontend/                    # Backend-first system, frontend optional
├── sdk/                         # Python SDK & CLI tool
├── tests/
│   ├── unit/                   # No DB required
│   ├── integration/            # Full pipeline (requires Docker)
│   └── load/                   # Locust load tests (placeholder)
│
├── docker-compose.yml          # 4 core services: gateway, postgres, postgres_replica, redis (frontend optional)
├── .env.example                # Environment template
├── .env                        # Local dev config
├── Makefile                    # Development shortcuts
└── README.md                   # This file
```

---

## Phase 2: Performance (Complete)

- ✅ Complete performance layer (cost estimation, caching optimization)
- ✅ Speed benchmarks (measure cache hit ratio improvement)
- ✅ Add slow query logging to dedicated table
- ✅ Implement query budget enforcement
- ✅ Pre-flight cost blocking (configurable per role)

## Phase 3: Intelligence (Complete)

- ✅ Index recommendation engine (smart rules from EXPLAIN)
- ✅ Query complexity scorer (JOINs, subqueries, wildcards)
- ✅ Slow query detection with alerting
- ✅ Query diff viewer (original vs executed via auto-LIMIT)
- ✅ Pre-flight EXPLAIN cost estimation display

## Phase 4: Observability (Complete)

- ✅ Trace IDs & JSON structured logging
- ✅ Immutable audit log (fire-and-forget async insertion)
- ✅ Real-time metrics via Redis (P50/P99 latencies, cache hit ratio)
- ✅ Table access heatmap (Redis ZSETs)
- ✅ Webhook alerting system (Honeypot, Slow Query, Circuit Breaker)
- ✅ Admin endpoints (streaming CSV audit export, live dashboard metrics)

## Phase 5: Security Hardening (Complete)

- ✅ AES-256-GCM column encryption & decryption
- ✅ Role-based PII masking (admin sees plaintext, readonly sees \*\*\* masks)
- ✅ Circuit breaker (Closed → Open → Half-Open, Redis-persisted state)
- ✅ Honeypot detection & intrusion alerting
- ✅ Automatic IP blocking on suspicious activity
- ✅ Exponential backoff retry logic (3 attempts, 1s/2s/4s)
- ✅ Production-hardened async/await patterns
- ✅ Zero deprecation warnings (Pydantic v2+, bcrypt-only passlib)

## Phase 6: AI + Polish (Complete)

- ✅ NL→SQL endpoint (`/api/v1/ai/nl-to-sql`) — Convert natural language → SQL
- ✅ Query explainer endpoint (`/api/v1/ai/explain`) — Plain English descriptions
- ✅ Dry-run mode enhancement — Validate + cost estimate without execution
- ✅ Python SDK (`sdk/argus/client.py`) — Programmatic gateway access
- ✅ CLI tool (`argus` command) — Command-line interface for scripts
- ✅ Unit tests for AI + SDK (30+ new tests)
- ✅ Load test with AI endpoints (Locust integration)
- ✅ GitHub Actions CI verified & passing
- ✅ Full documentation ([PHASE6_COMPLETION.md](docs/PHASE6_COMPLETION.md))

## Troubleshooting

### Gateway won't start: "Cannot connect to Postgres"

Check docker status:

```bash
docker compose ps
```

If postgres is "unhealthy", wait 10s and retry.

### "Rate limit exceeded" immediately

By default, limit is 60 requests/minute per user. Check `.env` `RATE_LIMIT_PER_MINUTE`.

### "Circuit breaker OPEN"

Gateway detected 5+ consecutive DB errors. Wait 30s (check `.env` `CIRCUIT_COOLDOWN_SECONDS`). Server is in HALF_OPEN state, testing recovery with 1 probe request.

### Tests fail: "Cannot find module 'main'"

Ensure you're running from the `gateway/` directory:

```bash
cd gateway
python -m pytest tests/
```

---

## Interview Talking Points

1. **4-layer pipeline**: Every query passes through security, performance, execution, observability — no layer can be skipped.

2. **Redis at every layer**: Brute force counters, rate limit buckets, circuit breaker state, cache, metrics — all in Redis for fast lookups.

3. **Fast-fail security**: IP check before auth, injection detection before execution. Fail as early as possible.

4. **True Caching**: Query fingerprinting + table-tagged invalidation means cache is always correct. True 100% database bypass (caching analysis metadata inline).

5. **Observability built-in**: Trace IDs, audit logs, metrics served via REST API. No external Prometheus/Grafana tools.

6. **Circuit breaker**: When DB fails, gateway fails fast (503) instead of hanging. HALF_OPEN state tests recovery. Production-ready resilience pattern.

7. **Blind DLP Data Masking**: Different roles see different data. Readonly sees masked SSNs/Emails. Blind Regex Data Loss Prevention prevents attackers from stealing data using SQL `AS` aliases.

8. **EXPLAIN ANALYZE**: Post-execution plan analysis → index recommendations. Rule-based engine suggests CREATE INDEX DDL.

---
