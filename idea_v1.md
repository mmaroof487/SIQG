# Secure Intelligent Query Gateway (SIQG)

> A production-grade middleware system that sits between clients and a database — securing, analyzing, optimizing, and monitoring every query before execution.

[![CI Passing](https://img.shields.io/badge/CI-passing-brightgreen)](.) [![Coverage](https://img.shields.io/badge/coverage-75%25-green)](.) [![Python](https://img.shields.io/badge/python-3.11-blue)](.) [![Docker](https://img.shields.io/badge/docker-compose-blue)](.) [![License](https://img.shields.io/badge/license-MIT-lightgrey)](.)

---

## Table of Contents

1. [What is SIQG?](#what-is-siqg)
2. [Why SIQG?](#why-siqg)
3. [System Architecture](#system-architecture)
4. [Request Lifecycle](#request-lifecycle)
5. [Component Deep Dive](#component-deep-dive)
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
- **Monitors** everything with a live observability dashboard

Think of it like a security checkpoint, traffic controller, and analytics engine — all in one, for your database.

---

## Why SIQG?

| Problem                    | Without SIQG                         | With SIQG                              |
| -------------------------- | ------------------------------------ | -------------------------------------- |
| SQL Injection              | Relies on ORM / developer discipline | Caught at gateway level, every time    |
| Sensitive data exposure    | Role-based at app level only         | Column-level masking + encryption      |
| Slow queries               | Found in production by users         | Detected before they become incidents  |
| No query visibility        | Logs scattered across services       | Centralized audit trail with trace IDs |
| Repeated expensive queries | Hit DB every time                    | Redis cache with smart invalidation    |
| Runaway queries            | `SELECT *` on 10M rows crashes DB    | Auto-LIMIT injection + cost gating     |
| DB failures cascade        | Entire app hangs                     | Circuit breaker cuts off fast          |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│                                                                     │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│   │  Web UI      │   │  Python SDK  │   │  CLI Tool (siqg)     │  │
│   │  (React)     │   │  (PyPI)      │   │  Click / Typer       │  │
│   └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘  │
└──────────┼────────────────── ┼──────────────────────┼──────────────┘
           │                   │                       │
           └───────────────────┼───────────────────────┘
                               │  HTTP / gRPC
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        GATEWAY CORE (FastAPI)                       │
│                                                                     │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │  Auth   │→ │  Rate    │→ │  Query    │→ │   Encryption     │   │
│  │  Layer  │  │  Limiter │  │  Validator│  │   Engine (AES)   │   │
│  └─────────┘  └──────────┘  └───────────┘  └──────────────────┘   │
│                                                                     │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │  Cache  │→ │  Query   │→ │  Circuit  │→ │   Router         │   │
│  │  Layer  │  │  Analyzer│  │  Breaker  │  │   (R/W Split)    │   │
│  └─────────┘  └──────────┘  └───────────┘  └──────────────────┘   │
│                                                                     │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │  Audit  │  │  Tracer  │  │  Metrics  │  │   Alert Engine   │   │
│  │  Logger │  │  (UUID)  │  │  Exporter │  │   (Webhooks)     │   │
│  └─────────┘  └──────────┘  └───────────┘  └──────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  PostgreSQL  │  │    Redis     │  │ Elasticsearch│
  │  (Primary)   │  │  (Cache +    │  │  (Audit Logs)│
  │  (Replica)   │  │   Sessions)  │  │              │
  └──────────────┘  └──────────────┘  └──────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY STACK                            │
│                                                                     │
│   ┌───────────────┐      ┌────────────────┐    ┌───────────────┐   │
│   │  Prometheus   │ ───→ │    Grafana     │    │    Kibana     │   │
│   │  (Metrics)    │      │  (Dashboards)  │    │  (Log Search) │   │
│   └───────────────┘      └────────────────┘    └───────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Docker Compose Service Map

```
┌─────────────────────────────────────────────────────┐
│                  docker-compose.yml                  │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │ gateway  │   │ postgres │   │    redis     │    │
│  │ :8000    │   │ :5432    │   │    :6379     │    │
│  └──────────┘   └──────────┘   └──────────────┘    │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │prometheus│   │ grafana  │   │elasticsearch │    │
│  │ :9090    │   │ :3000    │   │    :9200     │    │
│  └──────────┘   └──────────┘   └──────────────┘    │
│                                                     │
│  ┌──────────┐   ┌──────────┐                        │
│  │  kibana  │   │ frontend │                        │
│  │ :5601    │   │ :3001    │                        │
│  └──────────┘   └──────────┘                        │
└─────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

Every query that enters SIQG travels through a fixed pipeline. No step can be skipped.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         QUERY LIFECYCLE                                  │
└──────────────────────────────────────────────────────────────────────────┘

  Incoming Request
       │
       ▼
┌─────────────┐
│  Generate   │  trace_id = uuid4()   ← Every request gets a unique ID
│  Trace ID   │  Attached to all logs, metrics, DB calls
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│    Auth     │ FAIL │  401 Unauthorized                    │
│   Layer     │─────▶│  Logged with trace_id                │
│  JWT / Key  │      └──────────────────────────────────────┘
└──────┬──────┘
       │ PASS
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│    Brute    │ FAIL │  423 Locked — too many failed auths  │
│   Force     │─────▶│  Redis TTL counter exceeded          │
│   Check     │      └──────────────────────────────────────┘
└──────┬──────┘
       │ PASS
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│ IP Allow /  │ FAIL │  403 Forbidden — IP blocked          │
│ Blocklist   │─────▶│  Check before any DB interaction     │
└──────┬──────┘
       │ PASS
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│   Adaptive  │ FAIL │  429 Too Many Requests               │
│    Rate     │─────▶│  Anomaly flag if pattern unusual     │
│   Limiter   │      │  Webhook alert fired                 │
└──────┬──────┘      └──────────────────────────────────────┘
       │ PASS
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│    Query    │ FAIL │  400 Bad Request                     │
│  Validator  │─────▶│  DROP/DELETE/TRUNCATE blocked        │
│  + Parser   │      │  SQL injection pattern flagged       │
└──────┬──────┘      └──────────────────────────────────────┘
       │ PASS
       ▼
┌─────────────┐
│  Complexity │ HIGH │  Either reject or queue async
│   Scorer   │─────▶│  Cost threshold configurable
└──────┬──────┘
       │ ACCEPTABLE
       ▼
┌─────────────┐
│  Auto-LIMIT │       Inject LIMIT 1000 if no LIMIT clause
│  Injection  │       Show diff in query diff viewer
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│   RBAC +    │ FAIL │  403 Forbidden                       │
│  Column     │─────▶│  Table or column not allowed         │
│   Check     │      │  for this role                       │
└──────┬──────┘
       │ PASS
       ▼
┌─────────────┐
│ Fingerprint │       Normalize: WHERE id=1 → WHERE id=?
│  + Hash     │       Used for cache key + analytics
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│    Cache    │  HIT │  Return cached result instantly      │
│    Check    │─────▶│  Log cache hit, update metrics       │
│   (Redis)   │      └──────────────────────────────────────┘
└──────┬──────┘
       │ MISS
       ▼
┌─────────────┐      ┌──────────────────────────────────────┐
│   Circuit   │ OPEN │  503 DB Unavailable                  │
│   Breaker   │─────▶│  Fast fail — no hanging requests     │
└──────┬──────┘      └──────────────────────────────────────┘
       │ CLOSED
       ▼
┌─────────────┐
│  Pre-flight │       EXPLAIN (no ANALYZE) → cost estimate
│  Cost Check │       Block if over budget threshold
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Encryption │       Encrypt specified columns before INSERT
│   Engine    │       (AES-256, envelope key model)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Router    │       SELECT → Replica DB
│  (R/W Split)│       INSERT/UPDATE → Primary DB
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Connection │       Reuse pre-opened connection from pool
│    Pool     │       Max N connections, queued if exhausted
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Execute   │       Query runs on PostgreSQL
│   + Timeout │       Hard timeout enforced (default 5s)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  EXPLAIN    │       Run EXPLAIN ANALYZE on completed query
│   ANALYZE   │       Extract: cost, scan type, rows, timing
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Decryption │       Decrypt encrypted fields for SELECT
│   + Masking │       Mask PII based on role (SSN → ***-6789)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Cache    │       Store result in Redis with TTL
│    Write    │       Keyed by query fingerprint hash
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Audit    │       Immutable log entry with full context
│     Log     │       trace_id, user, query, latency, result
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Metrics   │       Prometheus counters incremented
│   + Alerts  │       Webhook fired if slow / anomalous
└──────┬──────┘
       │
       ▼
   Response
   Returned
```

---

## Component Deep Dive

### 1. Auth Layer

```
┌────────────────────────────────────────────────────┐
│                   AUTH LAYER                       │
│                                                    │
│  Request                                           │
│     │                                              │
│     ├── Has "Authorization: Bearer <token>"?       │
│     │        │ YES                                 │
│     │        ▼                                     │
│     │   Decode JWT → Extract user_id, role, exp    │
│     │   Check exp → Reject if expired              │
│     │                                              │
│     ├── Has "X-API-Key: <key>"?                    │
│     │        │ YES                                 │
│     │        ▼                                     │
│     │   Lookup key in Redis (fast) / DB (fallback) │
│     │   Check revocation status                    │
│     │   Check key rotation grace period            │
│     │                                              │
│     └── Has HMAC Signature Header?                 │
│              │ YES                                 │
│              ▼                                     │
│         Verify HMAC-SHA256(body + timestamp)       │
│         Reject if timestamp > 5 min old (replay)   │
└────────────────────────────────────────────────────┘
```

### 2. Circuit Breaker

```
                      ┌─────────────┐
                      │   CLOSED    │ ← Normal operation
                      │ (Requests   │   All requests pass through
                      │  pass thru) │
                      └──────┬──────┘
                             │
                    N consecutive failures
                             │
                             ▼
                      ┌─────────────┐
                      │    OPEN     │ ← DB is struggling
                      │ (Fast fail) │   All requests rejected instantly
                      │   503       │   No DB hammering
                      └──────┬──────┘
                             │
                      Cooldown period
                      (e.g. 30 seconds)
                             │
                             ▼
                      ┌─────────────┐
                      │  HALF-OPEN  │ ← Testing recovery
                      │ (1 test req)│   One probe request allowed
                      └──────┬──────┘
                             │
                  ┌──────────┴──────────┐
                  │ SUCCESS             │ FAILURE
                  ▼                     ▼
             CLOSED again          Back to OPEN
             Normal ops            Cooldown resets
```

### 3. Cache Invalidation Strategy

```
┌────────────────────────────────────────────────────────────┐
│                 CACHE INVALIDATION MODEL                   │
│                                                            │
│  On SELECT:                                                │
│    cache_key = hash(fingerprint + user_role)               │
│    Redis GET(cache_key) → HIT: return, MISS: query DB      │
│    On MISS: store result with TTL (default: 60s)           │
│                                                            │
│  On INSERT / UPDATE / DELETE:                              │
│    Parse affected table from query AST                     │
│    Invalidate all cache keys tagged with that table        │
│    Redis: SCAN keys matching "table:{affected_table}:*"    │
│    Delete all matches → cache is clean                     │
│                                                            │
│  Cache Key Structure:                                      │
│    siqg:cache:{table_name}:{query_hash}:{role}            │
│                                                            │
│  Example:                                                  │
│    siqg:cache:users:a3f9b2c1:readonly                      │
│    siqg:cache:orders:d7e2a891:admin                        │
└────────────────────────────────────────────────────────────┘
```

### 4. Encryption Model (Envelope Encryption)

```
┌────────────────────────────────────────────────────────────┐
│               ENVELOPE ENCRYPTION MODEL                    │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MASTER KEY (stored in env / secret manager)        │  │
│  │  Never changes. Used only to encrypt/decrypt DEKs.  │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │ encrypts                       │
│                           ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DATA ENCRYPTION KEY (DEK) — one per column type    │  │
│  │  e.g. DEK_SSN, DEK_EMAIL, DEK_PHONE                 │  │
│  │  Stored encrypted in DB. Decrypted at runtime.      │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │ encrypts                       │
│                           ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ACTUAL DATA — AES-256-GCM                          │  │
│  │  ssn: "123-45-6789" → "X8#@!F92...base64..."        │  │
│  │  Stored encrypted in DB                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  If one column key (DEK) is compromised →               │  │
│  Only that column type is exposed, not all data         │  │
└────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer            | Technology                   | Why                                                   |
| ---------------- | ---------------------------- | ----------------------------------------------------- |
| API Framework    | FastAPI (Python)             | Async, auto Swagger docs, Pydantic validation         |
| Database         | PostgreSQL                   | EXPLAIN ANALYZE, full SQL feature set                 |
| Cache            | Redis                        | Fast key-value, TTL support, pub/sub for invalidation |
| Search / Logs    | Elasticsearch + Kibana       | Full-text log search, structured audit trail          |
| Metrics          | Prometheus                   | Time-series, scrape-based, Grafana compatible         |
| Dashboards       | Grafana                      | Live dashboards, alerting, Prometheus data source     |
| Containerisation | Docker + Docker Compose      | One-command setup, service isolation                  |
| Auth             | PyJWT + python-jose          | JWT encode/decode, HMAC signing                       |
| Encryption       | cryptography (AES-256-GCM)   | Industry standard, envelope key support               |
| Testing          | pytest + pytest-cov + Locust | Unit, integration, and load testing                   |
| CI/CD            | GitHub Actions               | Auto-test on every push                               |
| CLI              | Typer                        | Python-native CLI framework                           |
| Frontend         | React + Monaco Editor        | VS Code quality SQL editor in browser                 |
| ORM / Driver     | SQLAlchemy + asyncpg         | Async Postgres, multi-DB dialect support              |

---

## Feature Set

### Phase 1 — Core Security (Week 1–2)

- [x] JWT authentication
- [x] API key authentication with rotation
- [x] Role-based access control (Admin / Read-only / Guest)
- [x] SQL injection detection (regex + pattern matching)
- [x] Query type allowlist (SELECT + INSERT only)
- [x] Brute force protection (Redis-backed lockout)
- [x] IP allowlist / blocklist

### Phase 2 — Performance (Week 3–4)

- [x] Redis query caching with fingerprinting
- [x] Cache invalidation on write (table-tagged keys)
- [x] Query fingerprinting + normalization
- [x] Read/write routing (SELECT → replica, INSERT → primary)
- [x] Connection pooling (asyncpg pool)
- [x] Query timeout enforcement (configurable per role)
- [x] Auto-LIMIT injection on unbounded SELECT

### Phase 3 — Intelligence (Week 5–6)

- [x] EXPLAIN ANALYZE post-execution analysis
- [x] Pre-flight cost estimation (EXPLAIN without ANALYZE)
- [x] Slow query detection + dedicated log
- [x] Index recommendation engine (rule-based from EXPLAIN output)
- [x] Query plan regression detection (fingerprint → plan history)
- [x] Query complexity scoring (JOINs, subqueries, wildcards)
- [x] Daily query budget per user (BigQuery-style)

### Phase 4 — Observability (Week 7–8)

- [x] Distributed trace IDs on every request
- [x] Prometheus metrics exporter
- [x] Grafana dashboards (latency, cache ratio, error rate)
- [x] Structured JSON logging
- [x] Immutable audit log with CSV export
- [x] Webhook alerts (Slack / Discord on anomaly / slow query)
- [x] Table access heat map
- [x] SLA / uptime tracker (P50/P95/P99)
- [x] Health check endpoint + status page

### Phase 5 — Advanced Features (Week 9–10)

- [x] Circuit breaker (closed / open / half-open)
- [x] Exponential backoff retry on transient failures
- [x] Query anomaly detection (rolling average baseline)
- [x] Dead letter queue for failed async queries
- [x] Async query queue for expensive queries (job_id polling)
- [x] PII data masking in results (role-based)
- [x] Column-level access control
- [x] Honeypot table detection
- [x] Query diff viewer (original vs executed)
- [x] Data retention policy enforcement (GDPR)

### Phase 6 — AI + Polish (Week 11–12)

- [x] Natural language → SQL (LLM API)
- [x] AI query explainer (plain English explanation)
- [x] AI query fixer (auto-correct on syntax error)
- [x] Chat interface for DB exploration
- [x] Query result visualization (auto-chart numeric columns)
- [x] Monaco Editor with SQL autocomplete + schema hints
- [x] Saved query library with shareable links
- [x] Query history with search + filters
- [x] Dry-run / sandbox mode
- [x] API versioning (v1 / v2)
- [x] Swagger auto-docs at `/api/v1/docs`

---

## API Reference

### Core Endpoints

```
POST   /api/v1/query              Execute a query through the full pipeline
POST   /api/v1/query/batch        Execute multiple queries in one call
POST   /api/v1/query/dry-run      Validate without executing
GET    /api/v1/query/history      Paginated query history
POST   /api/v1/query/schedule     Schedule a recurring query (cron)
GET    /api/v1/query/result/{id}  Poll async query result
```

### Auth Endpoints

```
POST   /api/v1/auth/login         JWT login (username + password)
POST   /api/v1/auth/refresh       Refresh JWT token
POST   /api/v1/auth/logout        Revoke current session
GET    /api/v1/auth/sessions      List all active sessions
DELETE /api/v1/auth/sessions/{id} Revoke a specific session
POST   /api/v1/auth/keys          Generate new API key
DELETE /api/v1/auth/keys/{id}     Revoke API key
POST   /api/v1/auth/keys/{id}/rotate  Rotate key (grace period)
```

### Admin Endpoints

```
GET    /api/v1/admin/audit        Audit log (filterable, exportable)
GET    /api/v1/admin/analytics    Query analytics and patterns
GET    /api/v1/admin/users        User management
POST   /api/v1/admin/ip/block     Add IP to blocklist
POST   /api/v1/admin/policies     Update security policies (hot-reload)
GET    /api/v1/admin/schema       DB schema introspection
GET    /api/v1/admin/budget       Query budget usage per user
```

### Observability Endpoints

```
GET    /health                    Health check (DB, Redis, ES)
GET    /metrics                   Prometheus metrics scrape endpoint
GET    /api/v1/status             Public status page data (uptime, SLA)
GET    /api/v1/analytics/heatmap  Table access heat map data
```

### Example Request / Response

```json
POST /api/v1/query
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "query": "SELECT id, name, email, ssn FROM users WHERE id = 1",
  "encrypt_columns": [],
  "decrypt_columns": ["ssn"],
  "dry_run": false,
  "priority": "normal"
}
```

```json
HTTP 200 OK

{
  "trace_id": "a3f9b2c1-7e8d-4f2a-b1c3-d9e0f1a2b3c4",
  "status": "success",
  "cached": false,
  "latency_ms": 34,
  "result": [
    {
      "id": 1,
      "name": "Maroof",
      "email": "m@test.com",
      "ssn": "***-**-6789"
    }
  ],
  "query_analysis": {
    "scan_type": "Index Scan",
    "execution_time_ms": 2.3,
    "rows_processed": 1,
    "cost_estimate": 8.27,
    "plan_regression": false,
    "index_suggestions": []
  },
  "pipeline": {
    "auth": "pass",
    "rate_limit": "pass",
    "injection_check": "pass",
    "cache": "miss",
    "circuit_breaker": "closed",
    "timeout_remaining_ms": 4966
  }
}
```

---

## Implementation Plan

### Overview Timeline

```
Week 1  ──────── Auth + Basic Security
Week 2  ──────── Query Validation + RBAC
Week 3  ──────── Redis Cache + Fingerprinting
Week 4  ──────── Connection Pool + Routing
Week 5  ──────── EXPLAIN ANALYZE + Query Analysis
Week 6  ──────── Slow Query + Index Recommendations
Week 7  ──────── Prometheus + Grafana + Trace IDs
Week 8  ──────── Audit Logs + Webhooks + Alerts
Week 9  ──────── Circuit Breaker + Advanced Security
Week 10 ──────── Async Queue + Anomaly Detection
Week 11 ──────── AI Features (NL→SQL, Explainer)
Week 12 ──────── Frontend Polish + Testing + README
```

---

## Phase Breakdown

### Phase 1: Foundation (Week 1–2)

**Goal:** A working gateway that can authenticate users and safely execute basic queries.

**What to build:**

- FastAPI project skeleton with Docker Compose (Postgres + Redis)
- JWT login endpoint — issue token on valid credentials
- API key generation and validation
- Middleware chain skeleton (each layer is a function/class)
- Basic query allowlist (SELECT + INSERT only, reject everything else)
- SQL injection regex detection (block `'`, `--`, `OR 1=1`, etc.)
- RBAC: three roles (admin, readonly, guest) stored in DB
- Brute force protection: Redis counter per IP, lockout after 5 fails
- IP blocklist: check on every request, admin-managed

**Deliverable:** Can log in, get a token, send a SELECT query, have it validated and executed. Dangerous queries are rejected.

**Files to create:**

```
app/
  main.py              FastAPI app entry point
  config.py            Settings (env vars via pydantic-settings)
  middleware/
    auth.py            JWT + API key validation
    rate_limit.py      Adaptive rate limiter
    validator.py       Query parser + injection detector
    rbac.py            Role + table + column checks
  models/
    user.py            User + role DB models
    audit.py           Audit log DB model
  routers/
    auth.py            Login, logout, key management
    query.py           Main query execution router
```

---

### Phase 2: Performance Layer (Week 3–4)

**Goal:** Queries that have been run before return in under 5ms. Repeated work is eliminated.

**What to build:**

- Query fingerprinting: normalize `WHERE id=1` → `WHERE id=?`
- SHA-256 hash of fingerprint as cache key
- Redis GET before DB, Redis SET after DB
- Cache invalidation: on INSERT/UPDATE, delete all keys for affected table
- Read/write router: SELECT → replica connection, INSERT/UPDATE → primary
- asyncpg connection pool (min=5, max=20, configurable)
- Query timeout: asyncio timeout wrapper, configurable per role
- Auto-LIMIT injection: if SELECT has no LIMIT, inject `LIMIT 1000`

**Deliverable:** First query hits DB, all subsequent identical queries return from Redis. Load test shows 10x latency reduction for cached queries.

**Key implementation note on cache invalidation:**

```python
# On INSERT into "users" table:
# 1. Parse table name from query AST
# 2. Find all cache keys: SCAN "siqg:cache:users:*"
# 3. Delete them all: DEL key1 key2 key3...
# Result: next SELECT on users goes to DB fresh
```

---

### Phase 3: Intelligence Layer (Week 5–6)

**Goal:** The gateway understands query performance and can explain why a query is slow.

**What to build:**

- Post-execution `EXPLAIN ANALYZE` — run after every query, extract:
  - Scan type (Index Scan / Seq Scan / Bitmap Scan)
  - Actual execution time
  - Rows processed vs rows estimated
  - Total cost
- Pre-flight `EXPLAIN` (no ANALYZE) — cost estimate before execution
- Cost threshold gate: block queries over budget unless admin
- Slow query log: queries > 200ms get tagged, surfaced in dashboard
- Index recommendation engine:
  - If Seq Scan on a column in WHERE clause → suggest index
  - Generate exact `CREATE INDEX` DDL statement
- Query plan history: store plan per fingerprint, diff on each run
- Plan regression alert: if Index Scan → Seq Scan, fire alert
- Query complexity score: count JOINs + subqueries + `SELECT *` patterns

**Deliverable:** Run any query, see scan type, execution time, cost, and index suggestions in the response. Slow queries appear in a dedicated log.

---

### Phase 4: Observability Layer (Week 7–8)

**Goal:** Full visibility into everything that happens inside the gateway.

**What to build:**

- Trace ID (UUID4) generated at request entry, passed through all layers
- Prometheus metrics:
  - `siqg_requests_total` (counter, by status)
  - `siqg_query_latency_seconds` (histogram)
  - `siqg_cache_hits_total` / `siqg_cache_misses_total`
  - `siqg_rate_limit_hits_total`
  - `siqg_circuit_breaker_state` (gauge)
- Grafana dashboards:
  - Request rate + error rate
  - Latency P50 / P95 / P99
  - Cache hit ratio
  - Slow query count per hour
  - Circuit breaker state timeline
- Structured JSON logs: every log line has `trace_id`, `user_id`, `level`, `message`, `latency_ms`
- Elasticsearch index for logs, Kibana for search
- Immutable audit log in Postgres (insert-only table, no UPDATE/DELETE)
- CSV export endpoint for audit log
- Webhook alerts: POST to Discord/Slack on anomaly, slow query, rate limit breach
- `/health` endpoint: check DB, Redis, ES connectivity
- Table access heat map: query count per table, stored in Redis sorted set

**Deliverable:** Open Grafana, see live metrics. Open Kibana, search logs by trace_id. Get a Discord ping when a slow query fires.

---

### Phase 5: Advanced Security + Reliability (Week 9–10)

**Goal:** Production-grade failure handling and security depth.

**What to build:**

- Circuit breaker (3 states: closed / open / half-open)
  - Open after 5 consecutive DB failures
  - Half-open after 30s cooldown — send 1 test request
  - Close if test succeeds, re-open if it fails
- Exponential backoff retry (100ms → 200ms → 400ms, max 3 attempts)
- Async query queue:
  - High-cost queries go async
  - Return `{"job_id": "...", "status": "queued"}` immediately
  - Client polls `GET /api/v1/query/result/{job_id}`
  - Dead letter queue for failed jobs after max retries
- Query anomaly detection:
  - Track rolling 5-minute average queries/user in Redis
  - If current rate > 3x average → flag as anomalous, fire alert
- PII masking: mask SSN, email, phone in results based on role
- Column-level access control: role → allowed columns mapping in config
- Honeypot tables: admin defines fake tables, any query touching them → instant block + alert
- Data retention jobs: daily cron to enforce per-table retention policies
- Result size cap: truncate response if > 5MB, return warning header

**Deliverable:** Kill the DB container — gateway returns 503 instantly instead of hanging. Bring it back — half-open test succeeds, traffic resumes automatically.

---

### Phase 6: AI + Frontend Polish (Week 11–12)

**Goal:** AI-powered features and a demo-worthy frontend.

**What to build:**

- NL → SQL: send user's English query to LLM API, return SQL, run through pipeline
- AI query explainer: LLM explains any SQL in plain English, shown inline
- AI query fixer: on syntax error, send query + error to LLM, get corrected SQL
- AI security audit: admin triggers LLM analysis of last 7 days of queries
- Chat interface: conversational DB exploration, each message → SQL → result
- Monaco Editor integration (VS Code quality SQL editing in browser)
- SQL autocomplete using schema introspection data
- Query result visualization: auto-detect numeric columns, suggest chart
- Saved query library: name, save, one-click re-run
- Shareable query links: encode query state in URL
- Query history panel: last 50 queries, searchable, filterable
- Dry-run mode: full pipeline validation without DB execution
- API versioning: v1 (current), v2 (richer metadata)
- Python SDK: publish to PyPI, wrap all API endpoints
- CLI tool: `siqg query`, `siqg status`, `siqg logs`
- GitHub Actions CI: pytest on every push, coverage badge
- Load testing: Locust script, before/after cache comparison

**Deliverable:** Full working demo. Can type English, get SQL, run it, see chart, explain it with AI, all in 90 seconds.

---

## Project Structure

```
siqg/
├── docker-compose.yml
├── .env.example
├── README.md
├── Makefile                       # make dev, make test, make load-test
│
├── gateway/                       # Main FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   │
│   ├── middleware/                 # Pipeline layers (order matters)
│   │   ├── __init__.py
│   │   ├── tracer.py              # Trace ID generation
│   │   ├── auth.py                # JWT + API key + HMAC
│   │   ├── brute_force.py         # Failed auth counter
│   │   ├── ip_filter.py           # Allowlist / blocklist
│   │   ├── rate_limiter.py        # Adaptive rate limiting
│   │   ├── validator.py           # Injection + type check
│   │   ├── complexity.py          # Query complexity scorer
│   │   ├── rbac.py                # Role + column checks
│   │   ├── fingerprinter.py       # Query normalization + hash
│   │   ├── cache.py               # Redis get/set/invalidate
│   │   ├── circuit_breaker.py     # 3-state circuit breaker
│   │   ├── cost_estimator.py      # Pre-flight EXPLAIN
│   │   ├── encryptor.py           # AES-256 envelope encryption
│   │   ├── router.py              # R/W split routing
│   │   ├── pool.py                # Connection pool manager
│   │   └── timeout.py             # Query timeout enforcer
│   │
│   ├── analysis/
│   │   ├── explain.py             # EXPLAIN ANALYZE parser
│   │   ├── index_advisor.py       # Index recommendation engine
│   │   ├── plan_history.py        # Plan regression detection
│   │   ├── anomaly.py             # Rolling average anomaly detection
│   │   └── budget.py              # Daily query budget tracker
│   │
│   ├── ai/
│   │   ├── nl_to_sql.py           # Natural language → SQL
│   │   ├── explainer.py           # Query explanation
│   │   ├── fixer.py               # Syntax error auto-fix
│   │   └── audit_ai.py            # AI security audit
│   │
│   ├── routers/
│   │   ├── v1/
│   │   │   ├── query.py           # Core query endpoint
│   │   │   ├── auth.py            # Auth endpoints
│   │   │   ├── admin.py           # Admin endpoints
│   │   │   └── health.py          # Health + status
│   │   └── v2/
│   │       └── query.py           # v2 with richer response
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── user.py
│   │   ├── audit.py
│   │   ├── query_plan.py
│   │   ├── scheduled_query.py
│   │   └── retention_policy.py
│   │
│   ├── queue/
│   │   ├── async_queue.py         # Redis-backed async queue
│   │   ├── dead_letter.py         # DLQ for failed jobs
│   │   └── scheduler.py           # Cron-based scheduled queries
│   │
│   ├── metrics/
│   │   ├── prometheus.py          # Metric definitions
│   │   └── webhooks.py            # Alert webhook sender
│   │
│   └── utils/
│       ├── masking.py             # PII masking functions
│       ├── diff.py                # Query diff viewer
│       └── lineage.py             # Data lineage tracker
│
├── frontend/                      # React app
│   ├── Dockerfile
│   ├── src/
│   │   ├── components/
│   │   │   ├── QueryEditor.jsx    # Monaco Editor integration
│   │   │   ├── ResultsPanel.jsx   # Results + chart toggle
│   │   │   ├── AnalysisPanel.jsx  # EXPLAIN output + suggestions
│   │   │   ├── Dashboard.jsx      # Live metrics dashboard
│   │   │   ├── AuditLog.jsx       # Searchable audit trail
│   │   │   ├── SchemaExplorer.jsx # Table + column browser
│   │   │   ├── ChatInterface.jsx  # NL chat with DB
│   │   │   └── StatusPage.jsx     # Health + uptime
│   │   └── App.jsx
│   └── package.json
│
├── sdk/                           # Python SDK (PyPI publishable)
│   ├── siqg/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── cli.py                 # Typer CLI
│   ├── setup.py
│   └── README.md
│
├── tests/
│   ├── unit/
│   │   ├── test_validator.py
│   │   ├── test_encryption.py
│   │   ├── test_cache.py
│   │   ├── test_circuit_breaker.py
│   │   └── test_rate_limiter.py
│   ├── integration/
│   │   ├── test_query_pipeline.py  # Full pipeline with real DB
│   │   └── test_auth_flow.py
│   └── load/
│       └── locustfile.py           # Load testing scenarios
│
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/
│           ├── overview.json
│           ├── security.json
│           └── performance.json
│
└── .github/
    └── workflows/
        └── ci.yml                  # GitHub Actions CI pipeline
```

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourname/siqg.git
cd siqg

# Copy environment config
cp .env.example .env

# Start everything (8 services)
docker compose up --build

# Services available at:
# Gateway API:   http://localhost:8000
# Swagger Docs:  http://localhost:8000/api/v1/docs
# Frontend:      http://localhost:3001
# Grafana:       http://localhost:3000  (admin/admin)
# Kibana:        http://localhost:5601
# Prometheus:    http://localhost:9090
```

**First query in 30 seconds:**

```bash
# Get a token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Run a query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users LIMIT 5"}'
```

**CLI usage:**

```bash
pip install siqg-cli

siqg login --url http://localhost:8000
siqg query "SELECT COUNT(*) FROM orders"
siqg status
siqg logs --tail 20 --level slow
```

---

## Configuration

```env
# .env

# Gateway
SECRET_KEY=your-secret-key-here
JWT_EXPIRY_MINUTES=60
DRY_RUN_DEFAULT=false

# Database
DB_PRIMARY_URL=postgresql+asyncpg://user:pass@postgres:5432/siqg
DB_REPLICA_URL=postgresql+asyncpg://user:pass@postgres-replica:5432/siqg
DB_POOL_MIN=5
DB_POOL_MAX=20

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_DEFAULT_TTL=60
CACHE_MAX_SIZE_MB=5

# Security
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10
BRUTE_FORCE_MAX_ATTEMPTS=5
BRUTE_FORCE_LOCKOUT_MINUTES=15
IP_BLOCKLIST=[]
IP_ALLOWLIST=[]

# Query limits
QUERY_TIMEOUT_SECONDS=5
QUERY_RESULT_MAX_MB=5
AUTO_LIMIT_DEFAULT=1000
COST_THRESHOLD_WARN=1000
COST_THRESHOLD_BLOCK=10000
SLOW_QUERY_THRESHOLD_MS=200

# Circuit breaker
CIRCUIT_FAILURE_THRESHOLD=5
CIRCUIT_COOLDOWN_SECONDS=30

# Encryption
MASTER_KEY=your-master-key-32-chars-minimum
ENCRYPT_COLUMNS=ssn,credit_card,password_hint

# AI
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
AI_ENABLED=true

# Alerts
WEBHOOK_URL=https://hooks.slack.com/...
ALERT_SLOW_QUERY=true
ALERT_ANOMALY=true
ALERT_HONEYPOT=true

# Observability
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Interview Talking Points

### System Design Questions

**"Walk me through your architecture."**

> "SIQG is a middleware gateway between clients and PostgreSQL. Every query goes through a 15-step middleware chain — auth, rate limiting, injection detection, RBAC, fingerprinting, cache check, circuit breaker, cost estimation, encryption, routing to primary or replica, execution with timeout, post-execution EXPLAIN ANALYZE, decryption and masking, cache write, and finally audit logging. Each step is a composable module — adding a new security check is one file, no changes to the core pipeline."

**"How does your cache invalidation work?"**

> "Cache keys are structured as `siqg:cache:{table_name}:{query_hash}:{role}`. On any write — INSERT, UPDATE, DELETE — I parse the affected table from the query and scan Redis for all keys matching that table prefix, then delete them. It's table-level invalidation rather than exact-key, which means some over-invalidation but guarantees correctness. I log every invalidation event so I can measure the false invalidation rate."

**"What happens when your database goes down?"**

> "The circuit breaker opens after 5 consecutive failures. In open state, all requests get a 503 immediately — no hanging connections, no timeout waits, no DB hammering. After a 30-second cooldown, the breaker goes half-open and allows one probe request through. If it succeeds, the circuit closes and traffic resumes. If it fails, cooldown resets. This is the same pattern Netflix Hystrix uses."

**"How does your encryption work?"**

> "I use envelope encryption — same model as AWS KMS. There's a master key that never touches the DB. For each sensitive column type — SSN, email, credit card — I generate a separate data encryption key, or DEK. The DEK is encrypted with the master key and stored in the DB. At runtime, I decrypt the DEK with the master key, then use it to decrypt column values with AES-256-GCM. If one DEK is leaked, only that column type is exposed — not all encrypted data."

**"How do you handle slow queries?"**

> "Three layers. First, a pre-flight EXPLAIN without ANALYZE estimates cost before execution — high-cost queries are blocked or queued async. Second, I enforce a hard timeout on all queries — default 5 seconds, configurable per role. Third, post-execution EXPLAIN ANALYZE captures actual timing, and anything over 200ms is tagged as slow and surfaced in a dedicated dashboard panel. I also store query plans per fingerprint, so if a query switches from an Index Scan to a Seq Scan between runs, I detect that as a plan regression and fire an alert."

---

_Built by [Your Name] — 3rd year CS student. Open to backend, infra, and platform engineering roles._

_For demo, architecture walkthrough, or questions: [your@email.com]_
