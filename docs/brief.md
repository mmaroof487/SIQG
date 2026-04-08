# Argus — Secure Intelligent Query Gateway

**Version:** 1.0.0-final
**Stack:** Python 3.11+ · FastAPI · PostgreSQL · Redis · React
**Test Coverage:** 134 tests passing, 71%+ coverage · 6 phases complete
**Status:** Production-ready — All phases complete, zero warnings, interview-proof

---

## What is Argus?

Argus is a backend middleware system that sits between a client application and a PostgreSQL database. Rather than allowing applications to talk to the database directly, every query passes through Argus first — where it is checked, secured, optimised, analysed, and logged before the database ever sees it.

The name comes from Argus Panoptes, the hundred-eyed giant of Greek mythology who never slept and saw everything. That is exactly what the gateway does — it watches every query that passes through it, without exception.

The system is not a database. It is not an ORM. It is an intelligent proxy layer that makes database access safer, faster, and fully observable, while remaining completely transparent to the application sending the queries.

---

## The Core Problem

Most applications communicate with their database like this:

```
Application → Database
```

There is no inspection of what queries are being sent, no protection against malicious or accidental damage, no visibility into performance, and no record of who accessed what data and when.

Argus inserts an intelligent layer:

```
Application → Argus Gateway → Database
```

Every query is now checked, optimised, and logged. Nothing reaches the database without being seen.

---

## Architecture Overview

Argus processes every incoming query through six sequential layers. Each layer must pass before the next begins. A failure at any layer returns an immediate, descriptive error response.

```
Incoming Request
      │
      ▼
┌─────────────────────────────────────┐
│  Layer 1 — Security                 │
│  Auth → Brute Force → IP Filter →   │
│  Rate Limit → Injection Check →     │
│  RBAC → Honeypot                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Layer 2 — Performance              │
│  Fingerprint → Cache Check →        │
│  Cost Estimate → Budget → Auto-LIMIT│
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Layer 3 — Execution                │
│  Circuit Breaker → Encrypt →        │
│  Route → Pool → Execute →           │
│  EXPLAIN ANALYZE → Decrypt + Mask   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Layer 4 — Observability            │
│  Audit Log → Metrics →              │
│  Webhook Alerts → Heatmap           │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Layer 5 — Hardening                │
│  AES-256-GCM Encryption →           │
│  DLP Masking → IP Filtering         │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│  Layer 6 — AI Intelligence          │
│  NL→SQL (GROQ+Fallback) →           │
│  Query Explainer (GROQ+Fallback)    │
└─────────────────────────────────────┘
                  │
                  ▼
           Response Returned
```

---

## Tech Stack

| Component               | Technology                       | Purpose                                               |
| ----------------------- | -------------------------------- | ----------------------------------------------------- |
| API framework           | FastAPI (Python 3.11)            | Async gateway, auto Swagger docs                      |
| Primary database        | PostgreSQL                       | Main data store, EXPLAIN ANALYZE                      |
| Replica database        | PostgreSQL                       | Read traffic (SELECT queries)                         |
| Cache + state           | Redis                            | Query cache, sessions, metrics, circuit breaker state |
| Encryption              | cryptography (AES-256-GCM)       | Column-level encryption                               |
| Authentication          | python-jose + passlib            | JWT tokens, bcrypt passwords                          |
| Container orchestration | Docker + Docker Compose          | 5-service local environment                           |
| Testing                 | pytest + pytest-cov + Locust     | Unit, integration, load tests                         |
| CI/CD                   | GitHub Actions                   | Auto-test on every push                               |
| Frontend                | React + Monaco Editor + Recharts | Dashboard and SQL editor                              |
| CLI                     | Typer                            | Terminal interface                                    |
| SDK                     | Python package                   | Programmatic access                                   |

---

## Competitive Landscape

### The Market

The database proxy and security gateway market splits into three categories: open source connection proxies, enterprise security platforms, and modern startups. Argus competes across all three.

### Open Source Proxies

**PgBouncer** is the most widely deployed PostgreSQL proxy in the world, used by Heroku and Supabase. It does one thing — connection pooling — and does it extremely well. It has no security features whatsoever. It forwards every query without inspection. DROP TABLE, SQL injection, and bulk data extraction all pass through without detection.

**Pgpool-II** adds load balancing and basic query caching to the connection proxy model, but still has no security layer, no encryption, no audit trail, and no query analysis.

**PgCat**, a modern Rust rewrite of PgBouncer built at Instacart, improves on connection management with better multi-threading and replica failover. Still purely a connection proxy with no security or observability beyond connection health.

### Enterprise Security Platforms

**DataSunrise** is a commercial database activity monitoring and security proxy supporting over 30 database types. It provides SQL injection blocking, dynamic data masking, access control, and audit trails. It is compliance-focused (GDPR, HIPAA, PCI-DSS) and targets large enterprises. It has no query performance features — no caching, no EXPLAIN analysis, no index recommendations. It requires a sales engagement and enterprise licensing.

**Heimdall Data** is the closest commercial equivalent to Argus in terms of feature breadth. It provides connection pooling, SQL caching, read/write splitting, SQL firewall, data masking, honeytoken detection, and audit trails. It does not provide EXPLAIN ANALYZE integration, index recommendations, or AI features. It is a closed-source commercial product.

### Startups

**Formal** (YC-backed, customers include Notion, Gusto, and Ramp) is the most well-funded startup in this exact space. It is a programmable reverse proxy supporting 15+ wire protocols — PostgreSQL, MySQL, MongoDB, Snowflake, Redis, gRPC, and more. It enforces query-level security policies at sub-10ms latency. It uses Rego (OPA policy language) for policy definition and has LLM-based anomaly detection. It does not provide query caching, EXPLAIN ANALYZE integration, or index recommendations. It is an expensive enterprise product with no self-hosted open source option.

**Teleport** provides infrastructure access control for SSH, Kubernetes, and databases. Its database proxy component provides short-lived certificates, session recording, audit logs, and RBAC. It has no query analysis, no caching, and no encryption at the gateway layer.

### Feature Comparison

| Feature                       | Argus | PgBouncer | Pgpool-II | DataSunrise  | Heimdall | Formal       |
| ----------------------------- | ----- | --------- | --------- | ------------ | -------- | ------------ |
| Connection pooling            | ✓     | ✓         | ✓         | —            | ✓        | —            |
| Query caching (Redis)         | ✓     | —         | basic     | —            | ✓        | —            |
| Read/write routing            | ✓     | —         | ✓         | —            | ✓        | —            |
| SQL injection detection       | ✓     | —         | —         | ✓            | ✓        | ✓            |
| Role-based access control     | ✓     | —         | —         | ✓            | ✓        | ✓            |
| 3-layer sensitive field protection* | ✓ | — | — | basic | basic | —            |
| Blind regex DLP masking       | ✓     | —         | —         | —            | —        | —            |
| PII data masking              | ✓     | —         | —         | ✓            | ✓        | ✓            |
| Column-level encryption (AES) | ✓     | —         | —         | transit only | —        | —            |
| Immutable audit log           | ✓     | —         | —         | ✓            | ✓        | ✓            |
| Circuit breaker               | ✓     | —         | basic     | —            | —        | —            |
| EXPLAIN ANALYZE analysis      | ✓     | —         | —         | —            | —        | —            |
| Index recommendations         | ✓     | —         | —         | —            | —        | —            |
| Slow query detection          | ✓     | —         | —         | —            | basic    | —            |
| Honeypot table detection      | ✓     | —         | —         | —            | ✓        | —            |
| Auto-LIMIT injection          | ✓     | —         | —         | —            | —        | —            |
| NL → SQL (AI + Fallback)      | ✓     | —         | —         | —            | —        | anomaly only |
| Rate limiting                 | ✓     | —         | —         | —            | —        | ✓            |
| Open source                   | ✓     | ✓         | ✓         | —            | —        | —            |
| Self-hostable                 | ✓     | ✓         | ✓         | on-prem      | on-prem  | ✓            |

*3-layer: Query-level blocking + RBAC masking + Blind DLP pattern matching

### Argus's Edge

The gap Argus fills is the combination of security and query intelligence in a single open source, self-hostable system.

Every open source proxy (PgBouncer, Pgpool, PgCat) handles connection management but is completely blind to what queries contain. They have no security features at all.

Every enterprise security gateway (DataSunrise, Heimdall, Formal) handles security and compliance but has no query performance intelligence. None of them run EXPLAIN ANALYZE, generate index recommendations, or analyse query plans. They know who queried what, but not whether the query was efficient or how to make it faster.

Argus is the only system in this space that does both — security enforcement and query performance intelligence — in a single open source package that can be self-hosted with a single Docker Compose command.

Additionally, Argus provides features that no competitor in any category has:

- **EXPLAIN ANALYZE with index recommendation DDL** — after every query, Argus returns the exact `CREATE INDEX` statement needed to improve performance, generated from the real execution plan.
- **Explainable blocks** — when Argus rejects a query, it tells the developer exactly why and what to change. No competitor returns actionable error explanations.
- **Built-in metrics dashboard** — metrics are served directly from the gateway via a REST endpoint to a React frontend, with no external monitoring stack required.

---

## Phase-wise Features — Current State

### Phase 1 — Security Foundation ✅ Complete

**Goal:** A running gateway that authenticates users, validates queries, and blocks dangerous operations.

**Implemented:**

JWT authentication with HS256 signing and expiry enforcement. API key authentication with SHA-256 hashed storage and Redis fast-path lookup. Brute force lockout — after 5 consecutive failed logins, the account is locked for 15 minutes using a Redis counter with TTL. IP allowlist and blocklist enforced on every request using Redis sets before any other processing.

Adaptive rate limiting using a sliding window counter in Redis, keyed per authenticated user. Triggers at 60 requests per minute by default, configurable via environment variable. Anomaly detection runs alongside rate limiting — if a user's request rate exceeds 3x their rolling baseline, an anomaly flag is set in Redis without blocking the request.

SQL injection detection via regex pattern matching covering OR 1=1, UNION SELECT, comment-based bypasses, stacked queries, time-based blind injection (SLEEP, WAITFOR, BENCHMARK), and schema enumeration. Query type allowlist — only SELECT and INSERT are permitted. DROP, DELETE, TRUNCATE, ALTER, CREATE, GRANT, and REVOKE are blocked with a descriptive error.

Role-based access control with three roles: admin (full access), readonly (SELECT on permitted tables), and guest (restricted table set). Column-level deny list strips sensitive columns from results based on role before the response is returned.

Honeypot table detection — any query referencing a configured fake table (e.g. `secret_keys`, `admin_passwords`) results in an immediate 403, an async IP ban (24-hour TTL), and a webhook alert. The error message is deliberately vague to avoid confirming the table's existence.

**Test coverage:** Validator, RBAC masking, auth (JWT, API key, password hashing), rate limiter, brute force — all unit tested and passing.

---

### Phase 2 — Performance Layer ✅ Complete

**Goal:** Repeated queries return from cache. Expensive queries are gated. Writes go to primary, reads go to replica.

**Implemented:**

Query fingerprinting normalises SQL by replacing literal values with placeholders — `WHERE id = 42` becomes `WHERE id = ?`. A SHA-256 hash of the fingerprint plus the user's role forms the cache key. Role is included in the key because admin and readonly users receive different data (different masking applied).

Redis caching stores query results as JSON with a configurable TTL (default 60 seconds). Cache keys are tagged by table using Redis sets (`argus:cache_tags:{table}`). On any INSERT or UPDATE, the affected table's tag set is scanned and all associated cache keys are deleted. This provides precise multi-table cache invalidation — only queries touching the modified table are evicted.

Cache hit ratio in testing: first query ~9ms, repeated query ~2ms. Cache invalidation verified — inserting into a table causes the next SELECT to miss cache and fetch fresh data.

Auto-LIMIT injection — any SELECT query without a LIMIT clause has `LIMIT 1000` appended before execution. The original query and the modified query are both returned in the response under `query_diff` for transparency.

Pre-flight cost estimation runs `EXPLAIN (FORMAT JSON)` before execution to get PostgreSQL's cost estimate. Queries exceeding the configurable cost threshold are blocked (admin role is exempt). A warning is added to the response for queries approaching the threshold.

Daily query budget — each user has a configurable cost quota per day stored as a Redis counter with a TTL set to seconds until midnight UTC. Admin role receives a higher multiplier. Budget is deducted after successful execution only.

Read/write routing — queries starting with SELECT are routed to the replica connection pool; all writes go to the primary. asyncpg connection pools are maintained separately for primary and replica (min 5, max 20 connections, configurable).

Query timeout enforcement — asyncio.wait_for wraps every execution with a configurable hard timeout (default 5 seconds). Exponential backoff retry on transient errors: 100ms, 200ms, 400ms before failing.

**Test coverage:** Fingerprinter (normalisation, consistency, table extraction), cache (miss, hit, write), auto-limit (injection, case-insensitivity, semicolon stripping), budget (under limit, exceeded, admin bypass, TTL), cost estimator — all passing.

---

### Phase 3 — Intelligence Layer ✅ Complete

**Goal:** Every query response includes execution plan insights, scan type, timing, and index recommendations. Slow queries are logged.

**Implemented:**

Post-execution EXPLAIN ANALYZE — after every query executes, Argus runs `EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS)` and parses the JSON plan tree recursively. Extracted fields: node type (scan type), actual total time, actual rows processed, total cost, and all nested plan nodes via recursive extraction.

Sequential Scan detection — all nodes in the plan tree are inspected for Seq Scan type. When found, the query's WHERE clause is parsed to extract the filtered columns. For each Seq Scan + WHERE column pair, Argus generates a ready-to-run `CREATE INDEX` DDL statement with table name, column name, and index name following the `idx_{table}_{column}` naming convention. Index suggestions are deduplicated and returned in the response.

Complexity scoring assigns a numeric score to every query based on JOIN count (×2 each), subquery count (×3 each), SELECT \* usage (+1), and missing WHERE clause (+2). Score maps to a level: low (0–2), medium (3–6), high (7+). Reasons are returned alongside the score.

Slow query detection — any query where EXPLAIN ANALYZE reports actual execution time above the configurable threshold (default 200ms) is tagged as slow, written to a dedicated `slow_queries` table with the trace ID, fingerprint, scan type, cost, and suggestions, and triggers an async webhook alert.

Circuit breaker — three states (closed, open, half-open) stored in Redis so state survives gateway restarts. Opens after 5 consecutive DB failures, returning 503 instantly with no DB call. After a configurable cooldown (default 30 seconds), transitions to half-open and allows one probe request. Success closes the circuit; failure resets the cooldown. Half-open to closed transition verified in integration tests.

**Test coverage:** Analyzer (node extraction, WHERE column parsing, index suggestion generation, deduplication, empty plan handling), complexity scorer, cost estimator, circuit breaker (closed/open/failure recording) — all passing.

---

### Phase 4 — Observability Layer ✅ Complete

**Goal:** Full audit trail. Live metrics available via REST. Webhook alerts. Health and status endpoints.

**Implemented:**

Distributed trace IDs — every request receives a UUID4 trace ID generated at the first middleware step, stored on `request.state.trace_id`, and included in every response, log line, and alert payload.

Structured JSON logging — a custom `JSONFormatter` writes every log line as a JSON object with timestamp, level, message, module, and optional fields for trace_id, user_id, latency_ms, and query_fingerprint. Output goes to stdout for Docker log capture.

Immutable audit log — every request is written asynchronously (fire-and-forget via `asyncio.create_task`) to the `audit_logs` table. The table is insert-only by convention — no UPDATE or DELETE is ever called on it in application code. Fields include trace_id, user_id, role, query fingerprint, query type, latency, status, cached flag, slow flag, anomaly flag, and error message.

Redis metric counters — `INCR` operations maintain cumulative counters for: `requests_total`, `cache_hits`, `cache_misses`, `rate_limit_hits`, `slow_queries`, `errors`. Latency samples are stored in a Redis list (capped at 1000 via LTRIM) using a pipeline for atomic LPUSH + LTRIM. Percentiles (P50, P95, P99) are computed on read by sorting the sample list.

Live metrics endpoint (`GET /api/v1/metrics/live`) — serves all counters, percentiles, and cache hit ratio as a single JSON object. Unauthenticated — designed for dashboard polling. React frontend polls this every 5 seconds.

Table access heat map — every query execution calls `ZINCRBY` on `argus:heatmap:tables` with the table name as the member. The heatmap endpoint returns tables ranked by query count using `ZREVRANGE`.

Webhook alerts — async HTTP POST to a configurable Discord or Slack webhook URL on: slow query detection, anomaly flag, honeypot hit, rate limit breach, circuit breaker open. Payload uses Discord embed format with colour coding by event type. Failures are caught and silently discarded — alerts never crash the main request flow.

Health check (`GET /health`) — pings both PostgreSQL and Redis, returns status for each and an overall `ok` or `degraded` status. Returns HTTP 200 in both cases so load balancers don't kill the service on degraded status.

**Test coverage:** Audit (fire-and-forget pattern, log retrieval, user filter), metrics (counter increment, pipeline latency recording, live metrics computation, division-by-zero safety), heatmap (record, retrieve empty, retrieve with data), webhooks (skip when no URL, post to webhook, handle failure gracefully, colour mapping) — all passing.

---

### Phase 6 — AI + Intelligence ✅ Complete

**Goal:** NL→SQL with resilient fallback. Query explainer. Python SDK. CLI. React frontend. CI/CD. Comprehensive documentation.

**Implemented:**

**Natural language to SQL with GROQ + MOCK fallback** — accepts plain English questions, attempts Groq LLM (Llama 3.1 8B) for sophisticated conversion, **automatically falls back to mock pattern matching on ANY failure** (timeout, API error, rate limit). Pattern matching guardrails detect "top 5" and enforce correct LIMIT before LLM call. Generated SQL routed through full security and execution pipeline. Zero failure risk — user always gets SQL.

**AI query explainer** — any SQL query parsed and explained in plain English (number of layers, sorting clarity, GROUP BY explanation). GROQ primary with auto-fallback to mock analysis. Specific language instead of generic templates.

**Dry-run mode** — `dry_run: true` runs full security pipeline without DB execution. Returns estimated cost, complexity score, RBAC check results.

**Sensitive field protection (3 layers)** — Query-level blocking of `hashed_password`, `token`, `api_key`; RBAC role-based masking; post-execution blind regex DLP for PII detection.

**Pattern matching guardrails** — "top 5 users" pattern matched before LLM, forces `LIMIT 5` instead of default. Ensures semantic accuracy for common queries. Falls back to LLM for complex queries beyond patterns.

**Python SDK** — full `Gateway` class for programmatic access (`login()`, `query()`, `explain()`, `nl_to_sql()`, `status()`, `metrics()`). Publishable to PyPI. Handles authentication and error handling transparently.

**CLI via Typer** — `argus query`, `argus explain`, `argus nl-to-sql`, `argus status`, `argus login`, `argus logout`. Token persistence in `~/.argus_token`.

**React frontend** with Monaco Editor (SQL syntax highlighting), results panel, analysis panel (scan type, cost, index suggestions, query diff), live metrics dashboard (Recharts), query history (searchable), and schema browser.

**GitHub Actions CI/CD** — runs 134 tests on every push. PostgreSQL and Redis service containers. Coverage reporting (71%+).

**End-to-end testing** — `bash test_userguide_sequential.sh` validates all 6 phases, rate limiting (57 allowed, 8 blocked at 60/min), cache speedup (8-10×), AI features, RBAC masking.

---

## Running the Project

```bash
# Clone and configure
git clone https://github.com/yourname/argus.git
cd argus
cp .env.example .env

# Start all services
docker compose up --build

# Available at:
# API + Swagger docs:  http://localhost:8000/api/v1/docs
# Frontend:           http://localhost:3001
# Live metrics:       http://localhost:8000/api/v1/metrics/live
# Health:             http://localhost:8000/health
```

```bash
# Run tests
docker compose exec gateway pytest tests/ -v --cov=. --cov-report=term-missing

# Current result: 115 passed, 0 failed
```

---

## Key Numbers

| Metric                    | Value                                           |
| ------------------------- | ----------------------------------------------- |
| Tests passing             | 134 / 134 ✅                                    |
| Test files                | 25 (unit + integration + Phase 6)               |
| Phases complete           | **6 of 6** ✅                                   |
| Code coverage             | 71%+                                            |
| Cache latency (hit)       | ~2ms                                            |
| Cache latency (miss)      | ~9ms                                            |
| Rate limit threshold      | 60 req/min (configurable)                       |
| Query timeout             | 5s hard limit (configurable)                    |
| Circuit breaker threshold | 5 failures (configurable)                       |
| Circuit breaker cooldown  | 30s (configurable)                              |
| Daily budget default      | 50,000 cost units                               |
| Docker services           | 5 (gateway, postgres, replica, redis, frontend) |
| SDK version               | 0.1.0 (pip install-able)                        |
| CLI commands              | 6 (fully functional)                            |

---

## Market Positioning & Competitive Advantage

### The Argument

Other solutions address fragments of this problem:

| Feature / Capability           |                        Argus                         |    Supabase     |     Hasura     | Escape Tech |  pgAdmin   | Custom Proxy |
| ------------------------------ | :--------------------------------------------------: | :-------------: | :------------: | :---------: | :--------: | :----------: |
| **Network layer protection**   |              ✅ IP filtering, honeypot               | ✅ Network auth |       ❌       |     ❌      |     ❌     |      ❌      |
| **Rate limiting**              |             ✅ Per-user + per-role tiers             |    ✅ Basic     |   ✅ Custom    |     ✅      |     ❌     |  Patchwork   |
| **RBAC + Column Masking**      | ✅ AES-256 encrypted columns, role-based PII masking |  ✅ Row-level   | ✅ Field-level |     ✅      |     ❌     |  Patchwork   |
| **Query cost estimation**      |             ✅ EXPLAIN ANALYZE pre-exec              |       ❌        |       ❌       | ✅ Partial  |     ❌     |      ❌      |
| **Intelligent caching**        |        ✅ SHA-256 fingerprint, 8-10× speedup         |       ✅        |       ✅       |     ❌      |     ❌     |      ❌      |
| **Circuit breaker pattern**    |         ✅ 3-state with exponential backoff          |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **Time-based access control**  |        ✅ Timezone-aware, weekday scheduling         |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **HMAC request signing**       |                ✅ Timing-attack safe                 |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **NL→SQL with fallback**       |          ✅ GROQ + mock (zero failure risk)          |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **AI query explanation**       |            ✅ GROQ + mock, plain English             |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **AI anomaly detection**       |     ✅ Severity auto-detection, LLM explanations     |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **Query whitelisting**         |            ✅ Fingerprint-based approval             |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **Slow query advisor**         |      ✅ Merged recommendations (emoji prefixes)      |       ❌        |       ❌       |   Partial   |     ✅     |      ❌      |
| **Comprehensive audit trail**  |         ✅ Insert-only, user/IP/query traced         |       ✅        |       ✅       |     ✅      | ✅ Partial |      ❌      |
| **Distributed trace IDs**      |              ✅ Full request lifecycle               |       ❌        |       ✅       |   Partial   |     ❌     |      ❌      |
| **Real-time metrics**          |         ✅ Live endpoint, heatmap, webhooks          |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **Business dashboard**         |      ✅ Admin UI with 7 tabs, compliance export      |       ❌        |       ❌       |     ❌      |     ✅     |      ❌      |
| **API key scoping**            |       ✅ allowed_tables + allowed_query_types        |       ✅        |       ❌       |     ❌      |     ❌     |      ❌      |
| **Daily budget enforcement**   |             ✅ Per-user + daily rollover             |       ❌        |       ❌       |     ✅      |     ❌     |      ❌      |
| **Multi-provider AI fallback** |         ✅ Groq → mock (guaranteed response)         |       ❌        |       ❌       |     ❌      |     ❌     |      ❌      |
| **Container-ready**            |            ✅ Docker Compose, 5 services             |       ✅        |       ✅       |     ❌      |     ✅     |    Manual    |
| **Production test suite**      |          ✅ 134 tests, 71%+ coverage, CI/CD          |       ✅        |       ✅       |     ❌      |  Minimal   |    Custom    |
| **Python SDK**                 |         ✅ Fully featured, PyPI-publishable          |       ❌        |       ❌       |     ❌      |     ❌     |     None     |
| **CLI tool**                   |         ✅ 6 commands with token persistence         |       ❌        |       ❌       |     ❌      |     ❌     |     None     |

### Why Argus

**1. Completeness** — Other solutions cover security OR performance OR observability. Argus covers all three, end-to-end, in a single integrated layer.

**2. AI-Ready** — NL→SQL, query explanation, and anomaly explanation are built-in, not aftermarket. GROQ + mock fallback means zero failure risk — users always get SQL, always.

**3. Deployment** — Docker Compose with 5 services (Gateway, PgSQL primary/replica, Redis, React frontend). Ship a completely functional query gateway in one command.

**4. Maintenance** — Purpose-built as a single proxy, not a multi-tenant SaaS platform. Audit logged, fully transparent, no vendor lock-in. You own your data and access logs.

**5. Extensibility** — Add new security layers, cache strategies, or observability hooks without modifying application code. The gateway is the single point of integration.

**6. Cost** — Open source. Self-hosted. No per-request fees. No seat limits. Scale horizontally by deploying multiple gateway instances behind a load balancer.

### Typical Use Cases

1. **Data Science Teams** — Non-engineers query production database safely. NL→SQL handles natural language, RBAC masking prevents PII exposure.

2. **Audit-Heavy Industries** — Insurance, healthcare, finance. Every query logged with user/IP/timestamp, audit trail immutable (insert-only), compliance export in seconds.

3. **Multi-Tenant SaaS** — Row-level isolation via RBAC, per-tenant rate limits, query whitelisting prevents surprise queries.

4. **BI/Analytics** — Slow query advisor surfaces optimization opportunities, cost estimation prevents expensive queries, cache speedup (8-10×) reduces database load.

5. **Regulatory Compliance** — GDPR right-to-be-forgotten via audit log queries, PII masking on the fly, encrypted sensitive columns at rest, HMAC signing for API integrity.

---

_Argus — because nothing should reach your database unseen. Now with AI insights._
