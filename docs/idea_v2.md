# Secure Intelligent Query Gateway (SIQG)

> A backend middleware system that sits between clients and a database — securing, analyzing, optimizing, and monitoring every query before execution.

[![CI Passing](https://img.shields.io/badge/CI-passing-brightgreen)](.) [![Coverage](https://img.shields.io/badge/coverage-75%25-green)](.) [![Python](https://img.shields.io/badge/python-3.11-blue)](.) [![Docker](https://img.shields.io/badge/docker-compose-blue)](.) [![License](https://img.shields.io/badge/license-MIT-lightgrey)](.)

---

## Table of Contents

1. [What is SIQG?](#what-is-siqg)
2. [Why SIQG?](#why-siqg)
3. [System Architecture](#system-architecture)
4. [Request Lifecycle](#request-lifecycle)
5. [Pipeline Layers](#pipeline-layers)
6. [Tech Stack](#tech-stack)
7. [Feature Set](#feature-set)
8. [API Reference](#api-reference)
9. [Implementation Plan](#implementation-plan)
10. [Phase Breakdown](#phase-breakdown)
11. [Project Structure](#project-structure)
12. [Quick Start](#quick-start)
13. [Configuration](#configuration)
14. [Interview Talking Points](#interview-talking-points)

---

## What is SIQG?

Most applications talk to databases directly:

```
Client → Backend → Database
```

SIQG inserts an intelligent layer between them:

```
Client → SIQG Gateway → Database
```

This gateway is **not** a database. It is a **smart middleware** that:

- **Secures** every query before it touches the DB
- **Analyzes** query execution plans in real time
- **Optimizes** through intelligent caching
- **Monitors** with a built-in React dashboard (no external observability stack)

---

## Why SIQG?

| Problem                    | Without SIQG                         | With SIQG                                 |
| -------------------------- | ------------------------------------ | ----------------------------------------- |
| SQL Injection              | Relies on ORM / developer discipline | Caught at gateway level, every time       |
| Sensitive data exposure    | App-level only                       | Column-level AES encryption + PII masking |
| Slow queries               | Found in production by users         | Detected before they become incidents     |
| No query visibility        | Logs scattered                       | Centralized audit trail with trace IDs    |
| Repeated expensive queries | Hit DB every time                    | Redis cache with smart invalidation       |
| Runaway `SELECT *`         | Crashes DB on large tables           | Auto-LIMIT injection + cost gating        |
| DB failures cascade        | Entire app hangs                     | Circuit breaker cuts off fast             |

---

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│                                                                  │
│   ┌─────────────────┐   ┌──────────────┐   ┌────────────────┐  │
│   │   Web UI        │   │  Python SDK  │   │  CLI (siqg)    │  │
│   │   (React)       │   │  (PyPI)      │   │  Typer         │  │
│   └────────┬────────┘   └──────┬───────┘   └───────┬────────┘  │
└────────────┼────────────────── ┼───────────────────┼────────────┘
             └───────────────────┼───────────────────┘
                                 │  HTTP / REST
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    GATEWAY CORE (FastAPI)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SECURITY LAYER                                          │   │
│  │  Auth → Brute Force → IP Filter → Rate Limit →          │   │
│  │  Injection Check → RBAC → Column Access                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PERFORMANCE LAYER                                       │   │
│  │  Fingerprint → Cache Check → Auto-LIMIT →               │   │
│  │  Cost Estimator → Query Budget                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  EXECUTION LAYER                                         │   │
│  │  Circuit Breaker → Encrypt → Router → Pool →            │   │
│  │  Execute + Timeout → EXPLAIN ANALYZE → Decrypt + Mask   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  OBSERVABILITY LAYER                                     │   │
│  │  Cache Write → Audit Log → Metrics → Alert Webhooks     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────┐
          │                   │               │
          ▼                   ▼               ▼
  ┌──────────────┐   ┌──────────────┐  ┌───────────────┐
  │  PostgreSQL  │   │    Redis     │  │  React        │
  │  Primary     │   │  Cache +     │  │  Dashboard    │
  │  Replica     │   │  Sessions    │  │  (built-in)   │
  └──────────────┘   └──────────────┘  └───────────────┘
```

### Docker Compose Services

```
┌──────────────────────────────────────────────┐
│              docker-compose.yml              │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ gateway  │  │ postgres │  │   redis   │  │
│  │  :8000   │  │  :5432   │  │   :6379   │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│                                              │
│  ┌──────────┐  ┌──────────┐                 │
│  │ frontend │  │ postgres │                 │
│  │  :3001   │  │ -replica │                 │
│  └──────────┘  └──────────┘                 │
└──────────────────────────────────────────────┘
```

> No Prometheus, no Grafana, no ELK. Metrics are stored in Postgres/Redis and visualized via built-in React charts. Same data, zero DevOps overhead.

---

## Request Lifecycle

Every query travels through exactly four layers. Each layer is a group of middleware. No step is skipped.

```
  Incoming Request
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  LAYER 1 — SECURITY                                           │
│                                                               │
│  ┌─────────────┐  Generate trace_id = uuid4()                │
│  │  Trace ID   │  Attached to all logs from this point       │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  JWT or API Key validation                  │
│  │    Auth     │  FAIL → 401 Unauthorized                    │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Redis counter per IP                       │
│  │Brute Force  │  5 failures → 423 Locked (15 min TTL)       │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Check admin-managed allow/block list       │
│  │  IP Filter  │  FAIL → 403 Forbidden                       │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Rolling window counter per user in Redis   │
│  │ Rate Limit  │  FAIL → 429 Too Many Requests               │
│  │  + Anomaly  │  3x baseline → anomaly flag + webhook alert │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Block: DROP, DELETE, TRUNCATE, ALTER       │
│  │  Injection  │  Detect: OR 1=1, --, UNION SELECT, etc.     │
│  │  + Validator│  FAIL → 400 Bad Request                     │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Role → allowed tables → allowed columns    │
│  │    RBAC     │  Strip forbidden columns from SELECT *       │
│  │  + Columns  │  FAIL → 403 Forbidden                       │
│  └──────┬──────┘                                             │
└─────────┼─────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────────┐
│  LAYER 2 — PERFORMANCE                                        │
│                                                               │
│  ┌─────────────┐  WHERE id=1 → WHERE id=?                    │
│  │Fingerprint  │  SHA-256 hash → cache key                   │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Redis GET(cache_key)                       │
│  │    Cache    │  HIT  → return instantly, skip DB           │
│  │    Check    │  MISS → continue pipeline                   │
│  └──────┬──────┘                                             │
│         │ MISS                                               │
│  ┌─────────────┐  No LIMIT clause → inject LIMIT 1000        │
│  │ Auto-LIMIT  │  Show injected LIMIT in diff viewer         │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Run EXPLAIN (no ANALYZE) pre-execution     │
│  │    Cost     │  Warn if cost > threshold                   │
│  │  Estimator  │  Block if cost > hard limit (admin exempt)  │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Redis counter (cost units/day per user)    │
│  │   Budget    │  Resets midnight. Throttle if exceeded.     │
│  └──────┬──────┘                                             │
└─────────┼─────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────────┐
│  LAYER 3 — EXECUTION                                          │
│                                                               │
│  ┌─────────────┐  CLOSED: pass through                       │
│  │  Circuit    │  OPEN: 503 instantly (no DB hammering)      │
│  │  Breaker    │  HALF-OPEN: 1 probe request allowed         │
│  └──────┬──────┘                                             │
│         │ CLOSED                                             │
│  ┌─────────────┐  AES-256-GCM encrypt specified columns      │
│  │  Encrypt    │  Before INSERT — SSN, email, etc.           │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  SELECT → Replica                           │
│  │   Router    │  INSERT/UPDATE → Primary                    │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Reuse pre-opened connection (pool)         │
│  │    Pool     │  asyncpg pool: min=5, max=20                │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Query runs on PostgreSQL                   │
│  │  Execute +  │  Hard timeout enforced (default 5s)         │
│  │  Timeout    │  100ms → 200ms → 400ms retry on transient   │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Run EXPLAIN ANALYZE post-execution         │
│  │  EXPLAIN    │  Extract: scan type, cost, rows, time       │
│  │  ANALYZE    │  Seq Scan + WHERE column → suggest index    │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Decrypt columns for SELECT results         │
│  │ Decrypt +   │  Mask PII by role: SSN → ***-**-6789        │
│  │  Mask       │  email → m***@test.com                      │
│  └──────┬──────┘                                             │
└─────────┼─────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────────┐
│  LAYER 4 — OBSERVABILITY                                      │
│                                                               │
│  ┌─────────────┐  Store result in Redis with TTL             │
│  │ Cache Write │  Table-tagged key for invalidation          │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Insert-only Postgres table                 │
│  │  Audit Log  │  trace_id, user, query, latency, status     │
│  │             │  CSV export endpoint for compliance         │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  In-memory + Postgres counters              │
│  │   Metrics   │  Served to React dashboard via REST API     │
│  │   Update    │  No Prometheus — just /api/v1/metrics/live  │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌─────────────┐  Slow query? → POST to webhook (Slack/Discord)
│  │   Alerts    │  Anomaly? → webhook + flag in audit log     │
│  │  Webhooks   │  Honeypot hit? → immediate block + alert    │
│  └──────┬──────┘                                             │
└─────────┼─────────────────────────────────────────────────────┘
          │
      Response
      Returned
```

---

## Pipeline Layers

### Layer 1: Security

| Middleware   | What it does                                     | Failure response |
| ------------ | ------------------------------------------------ | ---------------- |
| Trace ID     | Generates UUID4, attaches to all downstream logs | —                |
| Auth         | Validates JWT or API key                         | 401              |
| Brute Force  | Redis counter, lockout after 5 fails             | 423              |
| IP Filter    | Allow/block list check                           | 403              |
| Rate Limiter | Rolling window + anomaly detection               | 429              |
| Validator    | Blocks dangerous query types, detects injection  | 400              |
| RBAC         | Table + column access per role                   | 403              |

### Layer 2: Performance

| Middleware     | What it does                                              |
| -------------- | --------------------------------------------------------- |
| Fingerprinter  | Normalizes query, generates SHA-256 hash                  |
| Cache Check    | Redis GET — hit returns immediately, miss continues       |
| Auto-LIMIT     | Injects `LIMIT 1000` if no LIMIT clause present           |
| Cost Estimator | Pre-flight `EXPLAIN` to estimate cost                     |
| Budget         | Daily cost quota per user, Redis counter + midnight reset |

### Layer 3: Execution

| Middleware        | What it does                                              |
| ----------------- | --------------------------------------------------------- |
| Circuit Breaker   | 3-state: closed / open / half-open                        |
| Encryptor         | AES-256-GCM encrypt specified columns before INSERT       |
| Router            | SELECT → replica, INSERT/UPDATE → primary                 |
| Connection Pool   | asyncpg pool, reuse pre-opened connections                |
| Execute + Timeout | Run query, enforce hard timeout, retry on transient error |
| EXPLAIN ANALYZE   | Post-execution plan analysis, index suggestions           |
| Decrypt + Mask    | Decrypt columns, mask PII by role                         |

### Layer 4: Observability

| Middleware     | What it does                                       |
| -------------- | -------------------------------------------------- |
| Cache Write    | Store result in Redis, table-tagged key            |
| Audit Log      | Insert-only log entry with full request context    |
| Metrics Update | Increment counters served to React dashboard       |
| Alert Webhooks | Fire POST to Slack/Discord on slow query / anomaly |

---

## Component Deep Dive

### Circuit Breaker States

```
              ┌──────────────────┐
              │     CLOSED       │  ← Normal. All requests pass.
              │  Counting fails  │
              └────────┬─────────┘
                       │
              5 consecutive failures
                       │
                       ▼
              ┌──────────────────┐
              │      OPEN        │  ← DB is down / struggling.
              │  Fast fail 503   │    All requests rejected instantly.
              │  No DB calls     │    No hanging. No hammering.
              └────────┬─────────┘
                       │
                 30s cooldown
                       │
                       ▼
              ┌──────────────────┐
              │   HALF-OPEN      │  ← Testing recovery.
              │  1 probe request │    One real request allowed through.
              └────────┬─────────┘
                       │
          ┌────────────┴────────────┐
       SUCCESS                  FAILURE
          │                         │
          ▼                         ▼
       CLOSED                     OPEN
    Resume normal               Reset cooldown
```

### Cache Invalidation

```
┌──────────────────────────────────────────────────────────┐
│                  CACHE KEY STRUCTURE                     │
│                                                          │
│  siqg:cache:{table_name}:{query_hash}:{role}            │
│                                                          │
│  Example:                                                │
│  siqg:cache:users:a3f9b2c1:readonly                      │
│  siqg:cache:orders:d7e2a891:admin                        │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                  ON SELECT (cache miss)                  │
│                                                          │
│  1. Fingerprint query → hash                             │
│  2. Redis GET → miss                                     │
│  3. Execute on DB                                        │
│  4. Redis SET with TTL (default 60s)                     │
│     Key tagged with table name                           │
│                                                          │
├──────────────────────────────────────────────────────────┤
│             ON INSERT / UPDATE / DELETE                  │
│                                                          │
│  1. Parse affected table from query                      │
│  2. SCAN Redis: keys matching siqg:cache:{table}:*       │
│  3. DELETE all matching keys                             │
│  4. Next SELECT on that table goes fresh to DB           │
│                                                          │
│  Result: correctness guaranteed. Some over-invalidation  │
│  is acceptable — simpler than exact-key tracking.        │
└──────────────────────────────────────────────────────────┘
```

### AES Column Encryption

```
┌──────────────────────────────────────────────────────────┐
│              AES-256-GCM COLUMN ENCRYPTION               │
│                                                          │
│  Config: ENCRYPT_COLUMNS = ["ssn", "credit_card"]        │
│                                                          │
│  On INSERT:                                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Raw value: "123-45-6789"                        │    │
│  │       │                                          │    │
│  │       ▼  AES-256-GCM + ENCRYPTION_KEY            │    │
│  │  Encrypted: "gAAAAABl9f2X..."  (stored in DB)    │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  On SELECT (admin role):                                 │
│  ┌──────────────────────────────────────────────────┐    │
│  │  DB value: "gAAAAABl9f2X..."                     │    │
│  │       │                                          │    │
│  │       ▼  Decrypt with ENCRYPTION_KEY             │    │
│  │  Returned: "123-45-6789"  (full value)           │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  On SELECT (readonly role):                              │
│  ┌──────────────────────────────────────────────────┐    │
│  │  DB value: "gAAAAABl9f2X..."                     │    │
│  │       │                                          │    │
│  │       ▼  Decrypt → then Mask                     │    │
│  │  Returned: "***-**-6789"  (masked)               │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  Key stored in env. Rotation: update key + re-encrypt    │
│  flagged columns in a background migration script.       │
└──────────────────────────────────────────────────────────┘
```

### Index Recommendation Engine

```
┌──────────────────────────────────────────────────────────┐
│           INDEX RECOMMENDATION (rule-based)              │
│                                                          │
│  Input: EXPLAIN ANALYZE output                           │
│                                                          │
│  Rule 1: Seq Scan detected?                              │
│    └─ AND column appears in WHERE clause?                │
│         └─ Suggest: CREATE INDEX idx_{table}_{col}       │
│                     ON {table}({col});                   │
│                                                          │
│  Rule 2: Rows estimated << Rows actual?                  │
│    └─ Statistics are stale                               │
│         └─ Suggest: ANALYZE {table};                     │
│                                                          │
│  Rule 3: Hash Join on large tables?                      │
│    └─ Suggest: increase work_mem or add composite index  │
│                                                          │
│  Output included in every query response:                │
│  {                                                       │
│    "index_suggestions": [                                │
│      {                                                   │
│        "reason": "Seq Scan on column used in WHERE",     │
│        "ddl": "CREATE INDEX idx_users_email              │
│                ON users(email);"                         │
│      }                                                   │
│    ]                                                     │
│  }                                                       │
└──────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer            | Technology                   | Why                                                    |
| ---------------- | ---------------------------- | ------------------------------------------------------ |
| API Framework    | FastAPI (Python)             | Async, auto Swagger docs, Pydantic validation          |
| Database         | PostgreSQL                   | EXPLAIN ANALYZE, full SQL feature set, replica support |
| Cache            | Redis                        | Fast key-value, TTL, pub/sub for invalidation          |
| Containerisation | Docker + Docker Compose      | One-command setup                                      |
| Auth             | PyJWT + python-jose          | JWT encode/decode, HMAC signing                        |
| Encryption       | cryptography (AES-256-GCM)   | Industry standard, well-documented                     |
| ORM / Driver     | SQLAlchemy + asyncpg         | Async Postgres, connection pooling                     |
| Frontend         | React + Recharts             | Built-in charts, no external dashboard tool needed     |
| SQL Editor       | Monaco Editor (CDN)          | VS Code quality, autocomplete support                  |
| Testing          | pytest + pytest-cov + Locust | Unit, integration, load testing                        |
| CI/CD            | GitHub Actions               | Auto-test on every push                                |
| CLI              | Typer                        | Python-native, clean DX                                |
| SDK              | Python package (PyPI)        | Wrap all endpoints, publishable                        |

> **No Prometheus. No Grafana. No Elasticsearch. No Kibana.**
> Metrics are computed in the backend and served via `/api/v1/metrics/live`. Charts are React + Recharts. This removes 4 services and hundreds of config lines with zero loss of core value.

---

## Feature Set

### Core (Must Have)

- JWT authentication + API key auth with rotation
- Brute force protection (Redis lockout)
- IP allow / blocklist (admin-managed)
- SQL injection detection (regex + pattern matching)
- Query type allowlist (SELECT + INSERT only by default)
- Role-based access control (Admin / Read-only / Guest)
- Column-level access control (role → allowed columns)
- PII data masking in results (role-based)
- AES-256-GCM column encryption
- Honeypot table detection + instant block + alert

### Performance

- Query fingerprinting + normalization
- Redis caching with table-tagged invalidation on write
- Auto-LIMIT injection (no unbounded SELECT)
- Pre-flight cost estimation (EXPLAIN without ANALYZE)
- Daily query budget per user (Redis counter, midnight reset)
- Read/write routing (SELECT → replica, INSERT → primary)
- asyncpg connection pooling
- Query timeout enforcement (configurable per role)
- Exponential backoff retry on transient failures

### Intelligence

- Post-execution EXPLAIN ANALYZE analysis
- Slow query detection + dedicated log (threshold: 200ms)
- Rule-based index recommendation engine
- Query complexity scoring (JOINs, wildcards, missing WHERE)
- Query diff viewer (original vs executed query)

### Observability (Built-in, No External Stack)

- Distributed trace IDs on every request
- Structured JSON logging
- Immutable audit log in Postgres (insert-only) + CSV export
- Metrics API (`/api/v1/metrics/live`) served to React charts
- Webhook alerts (Slack / Discord) for slow queries, anomalies, honeypot hits
- Table access heat map (Redis sorted set)
- Health check endpoint (`/health`) — DB + Redis status
- SLA tracker (P50 / P95 / P99 latency stored in Postgres)

### Circuit Breaker + Reliability

- 3-state circuit breaker (closed / open / half-open)
- Anomaly detection (rolling average baseline in Redis)

### AI Features (One, Done Well)

- Natural language → SQL (LLM API call, result runs through full pipeline)
- AI query explainer (plain English explanation of any SQL, shown inline)

### Developer Experience

- Swagger auto-docs at `/api/v1/docs` (FastAPI built-in)
- API versioning (`/api/v1/` and `/api/v2/`)
- Dry-run / sandbox mode (`dry_run=true` flag)
- Python SDK (PyPI publishable)
- CLI tool (`siqg query`, `siqg status`, `siqg logs`)
- GitHub Actions CI (pytest on every push, coverage badge)
- Load test suite (Locust, before/after cache comparison)
- HMAC request signing (replay attack prevention)

### Frontend (Focused, Not Overloaded)

- Monaco Editor (SQL editing with autocomplete)
- Query results panel
- Query analysis panel (EXPLAIN output, index suggestions, scan type)
- Live metrics dashboard (React + Recharts, polling `/api/v1/metrics/live`)
- Query history (last 50, searchable)
- Saved query library (one-click re-run)
- Schema browser (tables, columns, types from information_schema)
- Health / status page

---

## API Reference

### Core Endpoints

```
POST   /api/v1/query              Execute query through full pipeline
POST   /api/v1/query/batch        Execute multiple queries in one call
POST   /api/v1/query/dry-run      Full pipeline validation, no DB execution
GET    /api/v1/query/history      Paginated query history (searchable)
GET    /api/v1/query/saved        List saved queries
POST   /api/v1/query/saved        Save a query with a name
```

### Auth Endpoints

```
POST   /api/v1/auth/login         JWT login
POST   /api/v1/auth/refresh       Refresh JWT
POST   /api/v1/auth/logout        Revoke session
GET    /api/v1/auth/sessions      List active sessions
DELETE /api/v1/auth/sessions/{id} Revoke session
POST   /api/v1/auth/keys          Generate API key
DELETE /api/v1/auth/keys/{id}     Revoke API key
POST   /api/v1/auth/keys/{id}/rotate  Rotate key (24hr grace period)
```

### Admin Endpoints

```
GET    /api/v1/admin/audit        Audit log (filter by user, date, status)
GET    /api/v1/admin/audit/export CSV export
GET    /api/v1/admin/users        User list + role management
POST   /api/v1/admin/ip/block     Add to blocklist
POST   /api/v1/admin/ip/allow     Add to allowlist
GET    /api/v1/admin/schema       DB schema introspection
GET    /api/v1/admin/budget       Query budget usage per user
GET    /api/v1/admin/slow-queries Slow query log
GET    /api/v1/admin/heatmap      Table access heat map
```

### Observability Endpoints

```
GET    /health                    Health check (DB alive? Redis alive?)
GET    /api/v1/metrics/live       Live metrics for React dashboard
GET    /api/v1/status             SLA + uptime data (P50/P95/P99)
```

### AI Endpoints

```
POST   /api/v1/ai/nl-to-sql       Natural language → SQL
POST   /api/v1/ai/explain         Plain English explanation of SQL
```

### Example: Query Request + Response

```json
POST /api/v1/query
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "query": "SELECT id, name, email, ssn FROM users WHERE id = 1",
  "encrypt_columns": [],
  "decrypt_columns": ["ssn"],
  "dry_run": false
}
```

```json
HTTP 200 OK

{
  "trace_id": "a3f9b2c1-7e8d-4f2a-b1c3-d9e0f1a2b3c4",
  "status": "success",
  "cached": false,
  "cache_key": "siqg:cache:users:a3f9b2c1:readonly",
  "latency_ms": 34,
  "result": [
    {
      "id": 1,
      "name": "Maroof",
      "email": "m@test.com",
      "ssn": "***-**-6789"
    }
  ],
  "query_diff": {
    "original": "SELECT id, name, email, ssn FROM users WHERE id = 1",
    "executed": "SELECT id, name, email, ssn FROM users WHERE id = 1 LIMIT 1000"
  },
  "analysis": {
    "scan_type": "Index Scan",
    "execution_time_ms": 2.3,
    "rows_processed": 1,
    "cost_estimate": 8.27,
    "slow_query": false,
    "index_suggestions": []
  },
  "pipeline_summary": {
    "auth": "pass",
    "injection_check": "pass",
    "cache": "miss",
    "circuit_breaker": "closed",
    "auto_limit_injected": true,
    "cost_under_budget": true
  }
}
```

---

## Implementation Plan

### Timeline Overview

```
Week 1  ───── Project scaffold + Auth + Basic security
Week 2  ───── RBAC + Injection detection + Brute force + IP filter
Week 3  ───── Redis cache + Fingerprinting + Cache invalidation
Week 4  ───── Connection pool + Router + Timeout + Auto-LIMIT
Week 5  ───── EXPLAIN ANALYZE + Slow query log + Index suggestions
Week 6  ───── Circuit breaker + Cost estimator + Budget system
Week 7  ───── Audit log + Webhooks + Trace IDs + Metrics API
Week 8  ───── Encryption + PII masking + Honeypot + Anomaly detection
Week 9  ───── NL→SQL + AI Explainer + Dry-run + API versioning
Week 10 ───── Frontend (Monaco + Dashboard + Schema browser)
Week 11 ───── SDK + CLI + Tests + GitHub Actions CI
Week 12 ───── Load testing + README + Demo prep + Polish
```

---

## Phase Breakdown

### Phase 1: Foundation (Week 1–2)

**Goal:** A running gateway that authenticates users and safely validates + executes basic queries.

**What to build:**

```
1. FastAPI skeleton
   - main.py with lifespan (startup/shutdown)
   - Docker Compose: gateway + postgres + redis
   - config.py using pydantic-settings (reads .env)

2. Auth middleware
   - POST /api/v1/auth/login → issue JWT
   - Validate JWT on every protected route
   - API key generation + Redis lookup
   - HMAC signature verification header

3. Security middleware (in order)
   - Brute force: Redis INCR per IP, lockout after 5 with TTL
   - IP filter: check request.client.host against DB table
   - Rate limiter: sliding window counter in Redis per user_id
   - Query validator:
       - Parse first keyword: block DROP, DELETE, TRUNCATE, ALTER
       - Regex scan for: ' OR, --, ;--, UNION SELECT, 1=1
   - RBAC: user.role → allowed_tables config → allowed_columns config

4. Basic query execution
   - Pass validated query to asyncpg
   - Return raw result
   - Log every request (plain for now, structured logging in Phase 4)
```

**Deliverable:** `POST /api/v1/query` with a valid JWT executes a SELECT. A DROP TABLE returns 400. A wrong password after 5 tries locks the account.

---

### Phase 2: Performance Layer (Week 3–4)

**Goal:** Repeated queries never hit the database twice.

**What to build:**

```
1. Fingerprinter
   - sqlglot or regex to normalize literals: WHERE id=1 → WHERE id=?
   - SHA-256(fingerprint + role) → cache_key

2. Redis cache
   - Before execution: GET siqg:cache:{table}:{hash}:{role}
   - HIT: return immediately
   - MISS: continue, then SET with TTL after execution
   - Tag key with table name for invalidation

3. Cache invalidation
   - On INSERT/UPDATE/DELETE: parse table name from query
   - SCAN Redis for siqg:cache:{table}:*
   - DEL all matches

4. Auto-LIMIT injection
   - Regex check: does query contain LIMIT?
   - No → append LIMIT 1000 before execution
   - Store original + modified in query_diff field

5. Read/write router
   - Query starts with SELECT → use DB_REPLICA_URL connection
   - Everything else → use DB_PRIMARY_URL connection

6. asyncpg connection pool
   - min_size=5, max_size=20 (configurable)
   - Acquire on request, release after response

7. Query timeout
   - asyncio.wait_for(execute(), timeout=QUERY_TIMEOUT_SECONDS)
   - TimeoutError → 504 Gateway Timeout, logged as slow query
```

**Deliverable:** Run the same SELECT twice. Second response shows `"cached": true` and `latency_ms` drops from ~30ms to ~2ms. Load test with Locust shows clear before/after.

---

### Phase 3: Intelligence Layer (Week 5–6)

**Goal:** The gateway understands query performance and provides actionable insights.

**What to build:**

```
1. EXPLAIN ANALYZE (post-execution)
   - After every query: run EXPLAIN (ANALYZE, FORMAT JSON) on same query
   - Parse JSON output:
       - Scan type: "Seq Scan" or "Index Scan" etc.
       - Actual rows, actual time
       - Total cost
   - Include in every response under "analysis" key

2. Slow query detection
   - If execution_time_ms > SLOW_QUERY_THRESHOLD (default 200)
   - Insert into slow_queries table
   - Fire webhook alert
   - Surface in GET /api/v1/admin/slow-queries

3. Index recommendation (rule-based)
   - EXPLAIN output shows Seq Scan?
   - AND column appears in WHERE clause of original query?
   - → Generate: CREATE INDEX idx_{table}_{col} ON {table}({col});
   - Return in response under "index_suggestions"

4. Query complexity scorer
   - Count: JOINs (+2 each), subqueries (+3 each), SELECT * (+1), no WHERE (+2)
   - Total score → include in response
   - Log high-complexity queries separately

5. Pre-flight cost estimator
   - EXPLAIN (no ANALYZE) before execution
   - Extract "Total Cost" from plan
   - If cost > COST_THRESHOLD_WARN → add warning to response
   - If cost > COST_THRESHOLD_BLOCK → return 403 (admin exempt)

6. Daily query budget
   - Each user has a cost quota per day (configurable by role)
   - Redis key: budget:{user_id}:{date} with midnight TTL
   - INCRBY by query cost on each execution
   - If quota exceeded → throttle (slow down) or soft-block
   - GET /api/v1/admin/budget shows per-user usage
```

**Deliverable:** Run `SELECT * FROM orders` with no WHERE clause. Response shows Seq Scan, cost estimate, complexity score, and a suggestion to add a WHERE clause or index.

---

### Phase 4: Observability Layer (Week 7–8)

**Goal:** Full visibility into the gateway. No external stacks — everything built-in.

**What to build:**

```
1. Trace IDs
   - Generate uuid4() at request entry
   - Store in request.state.trace_id
   - Pass to every logger call, every DB query comment, every response

2. Structured JSON logging
   - Replace print() with Python logging + custom JSON formatter
   - Every log line: {"timestamp", "level", "trace_id", "user_id",
                      "message", "latency_ms", "query_fingerprint"}
   - Write to stdout (Docker captures it) + append to log file

3. Audit log (Postgres)
   - insert-only table: audit_logs
   - Columns: id, trace_id, user_id, role, query_fingerprint,
              query_type, latency_ms, status, cached, slow,
              anomaly_flag, created_at
   - No UPDATE or DELETE ever on this table
   - GET /api/v1/admin/audit with filters (user, date range, status)
   - GET /api/v1/admin/audit/export → CSV download

4. Metrics API (no Prometheus)
   - Counters stored in Redis (INCR on each event):
       siqg:metrics:requests_total
       siqg:metrics:cache_hits
       siqg:metrics:cache_misses
       siqg:metrics:rate_limit_hits
       siqg:metrics:slow_queries
       siqg:metrics:errors
   - Latency: LPUSH to Redis list, keep last 1000 values
   - GET /api/v1/metrics/live → compute P50/P95/P99, hit ratio, etc.
   - React dashboard polls this every 5 seconds

5. Webhook alerts
   - webhooks.py: async POST to WEBHOOK_URL
   - Trigger on: slow query, anomaly flag, honeypot hit, rate limit breach
   - Payload: {event_type, trace_id, user_id, message, timestamp}
   - Demo with Discord: free webhook URL, instant visible alert

6. Table heat map
   - Redis sorted set: ZINCRBY siqg:heatmap {table_name}
   - GET /api/v1/admin/heatmap → ZRANGE with scores
   - React renders as colour-coded table cards

7. Health check
   - GET /health
   - Check: asyncpg ping, Redis ping
   - Return: {status: ok/degraded, db: ok/error, redis: ok/error}

8. SLA tracker
   - Store P50/P95/P99 snapshots in Postgres every hour
   - GET /api/v1/status → 30-day uptime percentage + latency history
```

**Deliverable:** Open React dashboard. Run 10 queries. Watch request count, cache ratio, and latency update live. Run a slow query — get a Discord ping within 2 seconds.

---

### Phase 5: Security Hardening (Week 8–9)

**Goal:** Production-grade security depth.

**What to build:**

```
1. AES-256-GCM column encryption
   - Config: ENCRYPT_COLUMNS = ["ssn", "credit_card"]
   - On INSERT: detect column name → encrypt value before DB write
   - On SELECT: decrypt values → then apply masking by role
   - Key in env var ENCRYPTION_KEY (32 bytes minimum)
   - encryptor.py: encrypt(value, key) / decrypt(value, key)

2. PII masking (role-based)
   - After decryption, apply mask based on user role:
       SSN:    "123-45-6789"  → "***-**-6789"  (readonly)
       Email:  "m@test.com"   → "m***@test.com" (readonly)
       Phone:  "9876543210"   → "98*****210"    (readonly)
   - Admin role gets full decrypted value
   - Mask patterns configurable per column type

3. Honeypot tables
   - Admin defines fake table names: ["secret_keys", "admin_passwords"]
   - If any query references a honeypot table:
       - Immediately block (403)
       - Flag user in audit log
       - Fire webhook alert with user details
       - Optionally: auto-add user IP to blocklist

4. Anomaly detection
   - Per user: track query count in 5-minute rolling window (Redis)
   - Baseline: rolling average over last 12 windows
   - If current window > 3x baseline → anomaly flag
   - Add flag to audit log entry + fire webhook
   - Does not block — flags and alerts only (avoid false positives)

5. Circuit breaker
   - State stored in Redis (so it survives restarts)
   - closed: all requests pass
   - open: return 503 immediately, check timestamp for cooldown
   - half_open: allow 1 request, close on success / reopen on failure
   - Transitions logged with trace_id

6. Exponential backoff retry
   - On asyncpg.exceptions.TooManyConnectionsError or transient errors
   - Retry: 100ms → 200ms → 400ms (max 3 attempts)
   - If all fail: mark as circuit breaker failure hit
```

**Deliverable:** Stop the Postgres Docker container. First request gets 503 instantly. Bring Postgres back after 30s. Half-open probe succeeds. Traffic resumes. All logged with trace IDs.

---

### Phase 6: AI + Polish (Week 9–12)

**Goal:** One strong AI feature. Clean frontend. Deployable and demo-ready.

**What to build:**

```
1. NL → SQL (one LLM call, full pipeline integration)
   - POST /api/v1/ai/nl-to-sql
   - Body: {"question": "How many users signed up last week?"}
   - LLM system prompt includes: schema context, allowed tables for role
   - LLM returns SQL
   - SQL runs through FULL gateway pipeline (auth already done)
   - Returns same response format as regular /query
   - Demo: type English → see generated SQL → see results

2. AI Query Explainer
   - POST /api/v1/ai/explain
   - Body: {"query": "SELECT ..."}
   - LLM returns: plain English explanation of what the query does
   - Shown inline below query editor in frontend
   - 15 lines of code. Very high demo value.

3. Dry-run mode
   - Any query with dry_run: true in body
   - Runs full pipeline: auth, validation, RBAC, cost estimation
   - Does NOT execute on DB, does NOT write cache
   - Returns: what would have happened, pipeline_summary, cost estimate
   - Useful for policy testing without side effects

4. API versioning
   - /api/v1/ — current stable
   - /api/v2/ — richer response (includes full EXPLAIN JSON, lineage stub)
   - FastAPI APIRouter prefix makes this trivial

5. Frontend (focused scope)
   - Monaco Editor: SQL editing, autocomplete table/column names from schema
   - Query results panel: tabular display, column type badges
   - Analysis panel: scan type, cost, slow flag, index suggestions, diff viewer
   - Metrics dashboard: 4 Recharts — request rate, cache ratio, latency,
                         slow queries over time (polls /metrics/live)
   - Query history: last 50 queries, filter by status/date, re-run button
   - Saved queries: name + save, one-click load into editor
   - Schema browser: sidebar showing tables + columns + types
   - Status page: health indicators for DB + Redis, P95 latency badge

6. Python SDK (PyPI)
   - siqg/client.py: Gateway class wrapping all endpoints
   - Usage: gw = Gateway("http://...", api_key="..."); gw.query("SELECT 1")
   - setup.py + pyproject.toml → publishable to PyPI
   - README with quickstart

7. CLI (Typer)
   - siqg login --url http://localhost:8000
   - siqg query "SELECT COUNT(*) FROM users"
   - siqg status
   - siqg logs --tail 20 --slow

8. Testing
   - pytest unit tests: validator, encryptor, cache, circuit breaker, rate limiter
   - pytest integration tests: full pipeline with real Postgres + Redis
     (Docker Compose spun up by pytest fixture)
   - Locust load test: 100 users, random queries, show cache impact
   - Target: 70%+ coverage, coverage badge on README

9. GitHub Actions CI
   - On every push: pytest + coverage report
   - If tests pass: build Docker image
   - Badge in README

10. README (treat it like a product page)
    - One-line pitch
    - Architecture diagram (ASCII or Excalidraw export)
    - Feature table
    - Quick start (docker compose up in one command)
    - 4-5 screenshots of dashboard + query editor + analysis panel
    - Interview talking points (brief)
```

**Deliverable:** Type "how many orders were placed today" in chat. See the SQL it generated. See the EXPLAIN output. See the result. Show the Discord alert that fired because it was a slow query. All in under 90 seconds.

---

## Project Structure

```
siqg/
├── docker-compose.yml
├── .env.example
├── Makefile                        # make dev, make test, make load-test
├── README.md
│
├── gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app, lifespan events
│   ├── config.py                   # pydantic-settings, reads .env
│   │
│   ├── middleware/
│   │   ├── security/
│   │   │   ├── tracer.py           # Trace ID generation
│   │   │   ├── auth.py             # JWT + API key + HMAC
│   │   │   ├── brute_force.py      # Redis lockout counter
│   │   │   ├── ip_filter.py        # Allow / blocklist
│   │   │   ├── rate_limiter.py     # Sliding window + anomaly
│   │   │   ├── validator.py        # Injection + type check
│   │   │   └── rbac.py             # Role + column access
│   │   │
│   │   ├── performance/
│   │   │   ├── fingerprinter.py    # Normalize + hash
│   │   │   ├── cache.py            # Redis get/set/invalidate
│   │   │   ├── auto_limit.py       # Inject LIMIT if absent
│   │   │   ├── cost_estimator.py   # Pre-flight EXPLAIN
│   │   │   └── budget.py           # Daily cost quota
│   │   │
│   │   ├── execution/
│   │   │   ├── circuit_breaker.py  # 3-state breaker (Redis state)
│   │   │   ├── encryptor.py        # AES-256-GCM encrypt/decrypt
│   │   │   ├── masker.py           # PII masking by role
│   │   │   ├── router.py           # R/W split
│   │   │   ├── pool.py             # asyncpg pool manager
│   │   │   ├── executor.py         # Execute + timeout + retry
│   │   │   └── analyzer.py         # EXPLAIN ANALYZE + index advice
│   │   │
│   │   └── observability/
│   │       ├── audit.py            # Insert-only audit log writer
│   │       ├── metrics.py          # Redis counter updates
│   │       ├── webhooks.py         # Slack/Discord alert sender
│   │       └── heatmap.py          # Redis sorted set table tracker
│   │
│   ├── routers/
│   │   ├── v1/
│   │   │   ├── query.py            # POST /query, /batch, /dry-run
│   │   │   ├── auth.py             # Login, keys, sessions
│   │   │   ├── admin.py            # Audit, users, budget, heatmap
│   │   │   ├── metrics.py          # GET /metrics/live
│   │   │   ├── ai.py               # NL→SQL, explainer
│   │   │   └── health.py           # /health, /status
│   │   └── v2/
│   │       └── query.py            # Richer response schema
│   │
│   ├── models/                     # SQLAlchemy models
│   │   ├── user.py
│   │   ├── audit_log.py
│   │   ├── slow_query.py
│   │   └── sla_snapshot.py
│   │
│   └── utils/
│       ├── diff.py                 # Query diff (original vs executed)
│       └── honeypot.py             # Honeypot table checker
│
├── frontend/
│   ├── Dockerfile
│   └── src/
│       ├── components/
│       │   ├── QueryEditor.jsx     # Monaco Editor + run button
│       │   ├── ResultsPanel.jsx    # Table display
│       │   ├── AnalysisPanel.jsx   # Scan type, cost, suggestions, diff
│       │   ├── Dashboard.jsx       # 4 Recharts + live polling
│       │   ├── QueryHistory.jsx    # Last 50, filterable
│       │   ├── SavedQueries.jsx    # Saved + one-click load
│       │   ├── SchemaExplorer.jsx  # Tables + columns sidebar
│       │   └── StatusPage.jsx      # Health + SLA
│       └── App.jsx
│
├── sdk/
│   ├── siqg/
│   │   ├── __init__.py
│   │   ├── client.py               # Gateway class
│   │   └── cli.py                  # Typer CLI commands
│   ├── setup.py
│   └── README.md
│
├── tests/
│   ├── unit/
│   │   ├── test_validator.py
│   │   ├── test_encryptor.py
│   │   ├── test_cache.py
│   │   ├── test_circuit_breaker.py
│   │   └── test_rate_limiter.py
│   ├── integration/
│   │   ├── conftest.py             # Docker Compose fixture
│   │   ├── test_query_pipeline.py
│   │   └── test_auth_flow.py
│   └── load/
│       └── locustfile.py
│
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/yourname/siqg.git
cd siqg

# Config
cp .env.example .env

# Start (5 services: gateway, postgres, postgres-replica, redis, frontend)
docker compose up --build

# Available at:
# API:          http://localhost:8000
# Swagger docs: http://localhost:8000/api/v1/docs
# Frontend:     http://localhost:3001
```

**First query:**

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users LIMIT 5"}'
```

**CLI:**

```bash
pip install siqg-cli

siqg login --url http://localhost:8000
siqg query "SELECT COUNT(*) FROM orders"
siqg status
siqg logs --tail 20
```

---

## Configuration

```env
# .env.example

# App
SECRET_KEY=change-me-in-production
JWT_EXPIRY_MINUTES=60

# Database
DB_PRIMARY_URL=postgresql+asyncpg://siqg:siqg@postgres:5432/siqg
DB_REPLICA_URL=postgresql+asyncpg://siqg:siqg@postgres-replica:5432/siqg
DB_POOL_MIN=5
DB_POOL_MAX=20

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_DEFAULT_TTL=60

# Security
RATE_LIMIT_PER_MINUTE=60
BRUTE_FORCE_MAX_ATTEMPTS=5
BRUTE_FORCE_LOCKOUT_MINUTES=15
ENCRYPT_COLUMNS=ssn,credit_card
ENCRYPTION_KEY=your-32-char-minimum-key-here
HONEYPOT_TABLES=secret_keys,admin_passwords,_internal_tokens

# Query limits
QUERY_TIMEOUT_SECONDS=5
AUTO_LIMIT_DEFAULT=1000
COST_THRESHOLD_WARN=1000
COST_THRESHOLD_BLOCK=10000
SLOW_QUERY_THRESHOLD_MS=200
DAILY_BUDGET_DEFAULT=50000

# Circuit breaker
CIRCUIT_FAILURE_THRESHOLD=5
CIRCUIT_COOLDOWN_SECONDS=30

# AI
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
AI_ENABLED=true

# Alerts
WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## Interview Talking Points

**"Walk me through your architecture."**

> "SIQG is a middleware gateway between clients and PostgreSQL. Every request goes through four logical layers — security, performance, execution, and observability. Security covers auth, rate limiting, injection detection, and RBAC. Performance covers caching, fingerprinting, cost estimation, and auto-LIMIT injection. Execution covers the circuit breaker, encryption, routing, connection pooling, query execution, and EXPLAIN ANALYZE. Observability covers audit logging, metrics, and webhook alerts. Each layer is a group of composable middleware — adding a new check is one file, zero changes to the pipeline."

**"How does your cache invalidation work?"**

> "Cache keys are structured with the table name embedded — `siqg:cache:{table}:{query_hash}:{role}`. On any write operation — INSERT, UPDATE, DELETE — I parse the affected table from the query, then SCAN Redis for all keys that start with that table prefix and delete them. It's intentional over-invalidation — I trade a few extra DB calls for guaranteed correctness, and I log every invalidation so I can measure the false rate."

**"What happens when your database goes down?"**

> "The circuit breaker opens after 5 consecutive failures. In open state every request gets a 503 immediately — no waiting, no timeout, no hammering a dead DB. After 30 seconds it goes half-open and allows exactly one probe request through. If it succeeds the circuit closes and traffic resumes. If it fails the cooldown resets. The breaker state lives in Redis so it survives a gateway restart."

**"How does your encryption work?"**

> "I use AES-256-GCM — a symmetric authenticated cipher that also detects tampering. Sensitive column names are in config — SSN, credit card, whatever you define. On INSERT, I intercept those values, encrypt them before the query reaches the DB. On SELECT, I decrypt them, then apply role-based masking — an admin gets the full value, a read-only user gets SSN shown as `***-**-6789`. The encryption key lives in an environment variable, never in code or DB."

**"How do you handle slow queries?"**

> "Two layers. Before execution, I run EXPLAIN without ANALYZE to get a cost estimate — if it's too expensive, I block it or warn the user. After execution, I run EXPLAIN ANALYZE to capture actual timing and scan type. Anything over 200ms is tagged as slow, written to a slow query log, and fires a webhook to Slack or Discord. The EXPLAIN output also feeds a rule-based index recommendation engine — if I see a Seq Scan on a column that's in the WHERE clause, I generate the exact CREATE INDEX statement and return it in the response."

**"Why not use Prometheus and Grafana?"**

> "I made a deliberate scope decision. Prometheus plus Grafana plus an ELK stack is essentially a DevOps project inside my project — hundreds of lines of config, complex networking, and weeks of debugging that add zero value to the core system. Instead I store metrics as Redis counters and latency samples, serve them from `/api/v1/metrics/live`, and visualize them with Recharts in my React frontend. Same data, same charts, five services instead of nine, and I fully understand every line."

---

_Built by [Your Name] — CS undergrad. Open to backend and platform engineering roles._
_Demo, walkthrough, or questions: [your@email.com] | [github.com/yourname/siqg]_
