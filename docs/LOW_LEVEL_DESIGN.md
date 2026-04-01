# Argus (Secure Intelligent Query Gateway) - Low-Level Design Document

This document provides a detailed technical breakdown of every component inside the Secure Intelligent Query Gateway (Argus). It is intended for developers, maintainers, and security auditors who need to understand the exact mechanics of the system.

---

## 🏗 System Architecture

The project consists of an asynchronous Python FastAPl gateway sitting in front of a PostgreSQL database cluster (Primary for writes, Replica for reads) and a Redis instance (for caching, rate limiting, metrics, and circuit breaking).

The core flow involves a **5-Layer Pipeline** executed on every query request:

1. **Security Layer:** Identity, authorization, threat prevention, honeypot detection.
2. **Performance Layer:** Caching, limits, budgeting, cost analysis, encryption setup.
3. **Execution Layer:** Circuit breaker, retry logic, routing, decryption, masking.
4. **Observability Layer:** Metrics, audits (with exponential retry), anomaly detection.
5. **Security Hardening:** AES-256-GCM encryption, role-based masking, firewall rules.

---

## 1️⃣ Layer 1: Security

The security layer immediately terminates requests that violate security policies, preserving backend resources.

### 1.1 IP Filtering (`ip_filter.py`)

- **Mechanism:** Redis `SISMEMBER` check against `ip:allowlist` and `ip:blocklist`.
- **Logic:** Blocklist takes precedence. If an allowlist exists, the IP _must_ be in it.
- **Performance:** `O(1)` Redis lookup before any heavy processing.

### 1.2 Authentication & Brute Force Protection (`auth.py`, `brute_force.py`)

- **Authentication:** Uses JWT (HS256 signature) or static API Keys (SHA-256 hashed in DB).
- **Brute Force:** Tracks failed login attempts in Redis (`auth:failed:{ip}`). If attempts exceed the threshold (e.g., 5), a 423 Locked status is returned along with a temporary TTL lockout.

### 1.3 Rate Limiting (`rate_limiter.py`)

- **Mechanism:** Sliding window counter per-user using Redis (`INCR` with dynamic `EXPIRE`).
- **Anomaly Detection:** Maintains an Exponential Moving Average (EMA) baseline of request volume. If the current rate exceeds 3x the baseline, an anomaly flag is set on the `request.state`, triggering a webhook alert without blocking the user.

### 1.4 Query Validation (`validator.py`)

- **SQL Injection:** Uses regex matching for common injection payloads (e.g., `OR 1=1`, `UNION SELECT`, `--`).
- **Destructive Queries:** Extracts the first SQL keyword. Blocks `DROP`, `DELETE`, `TRUNCATE`, and `ALTER` operations to enforce a strict read/append-only paradigm where necessary.
- **Honeypot:** Checks the query string for access to monitored, deceptive tables. Triggers immediate security alerts if hit.

### 1.5 Role-Based Access Control (RBAC) & Blind DLP Masking (`rbac.py`)

- **Roles:** Hierarchical permissions (Admin, Readonly, Guest).
- **Masking:** Post-execution pipeline step. Applies explicit column-name masking, as well as an advanced **Blind Regex DLP scanner** over all returned string cells. This dynamically obscures PII (Emails, SSNs, Credit Cards) regardless of the column name, completely defeating SQL `AS` aliasing bypass attacks.

---

## 2️⃣ Layer 2: Performance

The performance layer minimizes database load through intelligent caching and preemptive cost analysis.

### 2.1 Query Fingerprinting (`fingerprinter.py`)

- **Normalization:** Strips comments, collapses whitespace, and replaces literal values (strings/numbers) with generic placeholders (`?`).
- **Hashing:** Generates a SHA-256 hash of the normalized string. This serves as the universal identifier for a query shape.
- **Table Extraction:** Uses regex to parse the AST of the query to identify all dependencies (tables in `FROM` and `JOIN` clauses).

### 2.2 Semantic Caching (`cache.py`)

- **Storage:** Results are stored in Redis as JSON-serialized lists using the key `argus:cache:{fingerprint}:{role}`. Role-separation prevents privilege escalation via cache hits. The `EXPLAIN` analysis metadata is serialized _inside_ the payload.
- **True Cache Bypass:** Cache hits hydrate the response (including index suggestions and performance metrics) 100% from Redis, completely skipping the database execution layer. This ensures the primary DB load drops to exactly zero.
- **Invalidation Strategy:** Table-tagged caching. Writes (INSERT/UPDATE/DELETE) trigger a fire-and-forget background task that uses Redis `SSCAN` to find and delete all cached queries associated with the affected tables.

### 2.3 Cost Estimation (`cost_estimator.py`)

- **Execution:** Runs `EXPLAIN (FORMAT JSON)` on the query. This calculates the PostgreSQL execution plan cost without actually running the query.
- **Thresholding:** If the estimated planner cost exceeds `cost_threshold_warn`, a warning is generated.

### 2.4 Auto-LIMIT Injection (`auto_limit.py`)

- **Mechanism:** Intercepts unbounded `SELECT` statements (queries lacking a `LIMIT` clause).
- **Injection:** Appends `LIMIT {settings.auto_limit_default}` to prevent accidental full-table scans from crashing the memory buffer.

### 2.5 Query Budgeting (`budget.py`)

- **Tracking:** Maintains a daily cost budget per user.
- **Deduction:** Uses an atomic Redis `INCRBYFLOAT` operation to deduct the actual query cost post-execution.
- **Bypass:** Admin users are entirely excluded from budget tracking.

---

## 3️⃣ Layer 3: Execution & Intelligence

The execution layer handles robust database communication and explains the context behind query performance.

### 3.1 Execution Engine & Routing (`executor.py`)

- **Selector:** Parses the initial SQL verb.
- **Routing:** Directs `SELECT` statements to the PostgreSQL Replica. Directs `INSERT`, `UPDATE`, `DELETE`, and complex `WITH` (CTE) queries to the PostgreSQL Primary.
- **Native SQL Safety:** Safely escapes SQLAlchemy bind parameters (`\:`) so that user queries containing native Postgres casting (e.g., `::uuid`) or JSON operators do not crash the downstream parsing engine.

### 3.2 Timeouts and Retries (`executor.py`)

- **Timeout Limit:** Enforced via Python `asyncio.wait_for` and PostgreSQL `SET statement_timeout`. Admin users get an extended timeout limit.
- **Exponential Backoff:** Transient network errors or timeouts trigger a 3-attempt retry loop with cascading delays (100ms → 200ms → 400ms).

### 3.3 Circuit Breaker (`circuit_breaker.py`)

- **State Machine:** Maintained in Redis.
  - _CLOSED:_ Normal operation.
  - _OPEN:_ Error threshold exceeded; all requests fast-fail with 503 Service Unavailable.
  - _HALF-OPEN:_ After a cooldown period, the next request acts as a single probe. If successful, closes the circuit. If it fails, re-opens it.

### 3.4 Intelligence: Query Analysis (`analyzer.py`)

- **Execution:** Runs `EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS)` in the background on queries that were executed successfully.
- **Index Recommendations:** Scans the execution nodes for `Seq Scan` (Sequential Scan). If a filter condition is present on the scan, generates a theoretical `CREATE INDEX` DDL statement.
- **Complexity Scoring (`complexity.py`):** Awards "points" for anti-patterns (e.g., `SELECT *`, multiple `JOIN`s, lacking `WHERE`), categorized into Low/Medium/High complexity.

---

## 4️⃣ Layer 4: Observability

The observability layer is fully asynchronous, preventing monitoring overhead from inflating response latencies.

### 4.1 Audit Logging (`audit.py`)

- **Immutability:** A background task (`asyncio.create_task`) writes execution details to the PostgreSQL `audit_logs` table.
- **Metadata:** Captures `trace_id`, `user_id`, `latency_ms`, cache status, anomalies, and the exact query shape. Uses SQLAlchemy ORM logic to prevent injection in the admin viewer.

### 4.2 Real-time Metrics (`metrics.py`)

- **Counters:** Stores cumulative tallies in Redis via `INCRBYFLOAT` for requests, errors, and cache hits/misses.
- **Latency Percentiles:** Pushes latency values into a capped Redis list (max 1000 items via `LPUSH` + `LTRIM`). Dynamically calculates p50, p95, and p99 metrics.

### 4.3 Table Heatmap (`heatmap.py`)

- **Mechanism:** Increments a Redis Sorted Set (`ZINCRBY`) whenever a table is parsed from a query.
- **Insight:** Allows administrators to pinpoint the most heavily utilized tables in real-time.

### 4.4 Webhook Alerting (`webhooks.py`)

- **Integration:** Pushes formatted JSON Embeds to internal communication channels (e.g., Discord/Slack) upon critical events.
- **Events Traced:** Slow queries, honeypot access, rate limit exhaustion, and anomaly detection.
- **Resiliency:** Fails silently to ensure that logging infrastructure downtime does not cause gateway downtime.

---

## 🗄 Data Models (`models/audit_log.py`)

- **AuditLog:** Central table for the entire gateway. Holds deep request traces.
- **SlowQuery:** Secondary materialized view for queries exceeding `slow_query_threshold_ms`. Includes planner data, parsed row counts, and the suggested index modifications.
- **SLASnapshot:** Hourly rollup of percentiles, uptime, and cache hit ratios for historical SLA auditing.
