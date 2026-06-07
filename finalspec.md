Argus
Secure Intelligent Query Gateway
Final Product Specification — v1.0
This document defines the complete feature set of Argus — what the final product is, what every feature does, how each one works mechanically, and how all the pieces fit together into a single deployable system.

1. What Argus is
   Argus is a backend middleware gateway that sits between any client application and a PostgreSQL database. Instead of applications connecting to PostgreSQL directly, every query passes through Argus first. Argus inspects, secures, optimises, analyses, and logs every query before the database ever sees it — then returns the result to the client with full pipeline metadata attached.
   It is not a database. It is not an ORM. It is not a query builder. It is an intelligent proxy that makes database access safer, faster, and fully observable, while remaining completely transparent to the application sending the queries.
   Client Application → Argus Gateway → PostgreSQL
   Every query passes through four sequential middleware layers. A failure at any layer returns an immediate, descriptive error. Nothing reaches the database without passing all four layers.
   ● Layer 1 — Security: authentication, brute force, IP filter, rate limiting, injection detection, RBAC, honeypot
   ● Layer 2 — Performance: fingerprinting, caching, cost estimation, budget enforcement, LIMIT injection, R/W routing
   ● Layer 3 — Execution: circuit breaker, column encryption, retry logic, EXPLAIN ANALYZE, index recommendations, PII masking
   ● Layer 4 — Observability: trace IDs, audit logging, metrics counters, webhook alerts, heat map

2. Technical stack
   Component Technology Purpose
   API framework FastAPI — Python 3.11 Async gateway, auto Swagger docs, lifespan management
   Primary database PostgreSQL 15 Main data store, EXPLAIN ANALYZE, audit log
   Replica database PostgreSQL 15 (separate instance) All SELECT queries routed here to offload primary
   Cache + state store Redis 7 Query cache, sessions, metrics, circuit breaker state, rate limits, budgets
   Encryption cryptography — AES-256-GCM Column-level encryption with random nonce per operation
   Authentication python-jose + passlib/bcrypt JWT tokens (HS256) and SHA-256 hashed API keys
   Frontend React + Monaco Editor + Recharts SQL editor, results table, live dashboard, admin panel
   AI / LLM OpenAI gpt-4o-mini via httpx NL-to-SQL generation and query explanation
   Infrastructure Docker Compose — 5 services Single docker compose up --build starts the entire system
   Testing pytest + pytest-cov + Locust 134 unit + integration tests, load testing
   CI/CD GitHub Actions Full test suite on every push to main with coverage report
   SDK Python package + Typer CLI pip install argus-gateway, argus login / query / status commands

3. Layer 1 — Security features
   Every request hits this layer before anything else. A rejection here never reaches the database, the cache, or any other system. All security state is stored in Redis for sub-millisecond lookups.
   3.1 Authentication
   JWT token authentication
   Users log in with username and password. Argus verifies the bcrypt hash, issues a JWT signed with HS256. The token contains user_id, role, issued-at, and expiry. Every subsequent request must carry this token in the Authorization: Bearer header. On each request Argus decodes the JWT, checks the expiry claim, and extracts the role. An expired or invalid token returns 401 immediately — no database lookup required.
   API key authentication
   Users can generate API keys as an alternative to tokens. The raw key is shown once and never stored. Argus stores only the SHA-256 hash. On each request with X-API-Key header, Argus hashes the supplied key and checks Redis first (fast path), then the database. Keys can be scoped to specific allowed tables and allowed query types — a key restricted to SELECT on the users and orders tables cannot run INSERT or touch any other table.
   Brute force protection
   Failed login attempts are counted per IP + per username using a Redis INCR counter. The TTL is set only on the first increment — subsequent failures extend nothing, they just count. After 5 failures the account locks for 15 minutes and subsequent attempts return 423 (Locked) with the remaining TTL in the error message. A successful login clears the counter immediately.
   3.2 IP filtering
   Every request's IP address is checked against two Redis sets: a blocklist and an allowlist. The blocklist check happens first — blocked IPs return 403 immediately, before auth. If the allowlist is non-empty, only IPs on it are allowed through. Both lists are hot-configurable via the admin API — no gateway restart required. The honeypot system (below) automatically adds IPs to the blocklist.
   3.3 Rate limiting
   Requests are rate limited per authenticated user_id using a sliding window counter in Redis. The window key is keyed to the current 60-second bucket. The TTL is set to 2× the window to handle boundary cases correctly. Default limit is 60 requests per minute, configurable per role: admin gets 500/min, readonly gets 60/min, guest gets 10/min. Exceeding the limit returns 429.
   Anomaly detection
   Alongside rate limiting, Argus maintains a rolling baseline of the last 12 window counts per user. If the current window count exceeds 3× the rolling average, an anomaly flag is set in Redis for 5 minutes. The flag does not block the request — it marks the audit log entry and triggers a webhook alert. This catches unusual query spikes without false-positive lockouts.
   3.4 SQL injection detection
   Every query is checked against 12 regex patterns before execution: OR 1=1, UNION SELECT, SQL comment injection (--), stacked queries (;), block comments (/\* \*/), time-based blind injection (SLEEP, WAITFOR DELAY, BENCHMARK), schema enumeration (INFORMATION_SCHEMA), and MSSQL command execution (xp_cmdshell). Patterns are case-insensitive. A match returns 400 with a structured block_reasons array and a suggested_fix string telling the user exactly what to remove.
   3.5 Query type allowlist
   Only SELECT and INSERT are permitted by default. DROP, DELETE, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, EXEC, and EXECUTE are all blocked. The check uses the first keyword of the query after stripping whitespace — it is not a contains() check, which would be bypassable. A blocked query type returns 400 with the exact keyword that was rejected.
   3.6 Role-based access control
   Table access
   Each role has a list of permitted tables. Admin has no restrictions. Readonly can access users, orders, and products. Guest can only access products. A query referencing a table outside the role's allowed list returns 403 with the role name and the restricted table. This check is done before any database connection is opened.
   Column deny list
   Certain columns are stripped from all results for non-admin roles. hashed_password and internal_notes are stripped for readonly and guest. The stripping happens after execution on the result rows — Argus does not attempt to rewrite the SELECT clause, which would be fragile. If a query explicitly names a sensitive column (SELECT id, hashed_password FROM users), it is blocked at the validator level before execution.
   PII masking
   For readonly and guest roles, columns matching PII patterns are masked before the result is returned: SSN formatted as **\*-**-6789 (last 4 only), email as m**\*@domain.com (first character + domain), credit card as \*\***-\***\*-\*\***-3456 (last 4 only), phone as 12**\*\***90 (first 2 + last 2). Masking happens after decryption on a copy of the row — the original is never mutated. Admin role receives fully unmasked, decrypted values.
   3.7 Honeypot table detection
   A configurable list of fake table names (secret_keys, admin_passwords, etc.) is defined in the environment config. Any query referencing one of these tables — even in a comment or alias — triggers the honeypot. On a honeypot hit: the request is immediately rejected with a deliberately vague 403 (no information about why), the requesting IP is added to the Redis blocklist, and an async webhook alert fires to Discord or Slack with the user_id, IP, table name, trace_id, and timestamp. No real attacker should be querying secret_keys. Any query that does is treated as hostile.
   3.8 Sensitive field blocking
   Columns matching a configured sensitive field list (hashed_password, ssn, credit_card etc.) cannot be explicitly selected even by users who technically have table access. Attempting SELECT hashed_password FROM users returns 400 with a list of safe columns the user can access instead. This prevents a readonly user from ever seeing password hashes even if they know the column name.

4. Layer 2 — Performance features
   4.1 Query fingerprinting
   Before checking the cache, Argus normalises the query: all integer literals are replaced with ?, all string literals with ?, whitespace is collapsed, and the result is uppercased. SELECT _ FROM users WHERE id = 42 becomes SELECT _ FROM USERS WHERE ID = ?. The SHA-256 hash of this fingerprint, combined with the user's role, forms the cache key. This means identical queries with different literal values share the same cache entry.
   4.2 Redis query caching
   Cache keys take the form argus:cache:{fingerprint}:{role}. Role is included because admin and readonly users receive different data (different masking applied) and must never share a cache entry. The cache stores the final result — after decryption and masking — not the raw database rows. A cache hit returns the stored result immediately without opening any database connection. Cache TTL defaults to 60 seconds, configurable per query via a cache_ttl request parameter.
   Multi-table cache invalidation
   When an INSERT or UPDATE executes, Argus parses the table name from the query and invalidates all cache entries tagged to that table using a Redis tag set (SSCAN on argus:cache_tags:{table}). Only entries touching the modified table are evicted. Entries for unrelated tables remain cached. After DEL-ing a cache key, the corresponding entry is removed from the tag set with SREM to prevent unbounded growth.
   4.3 Automatic LIMIT injection
   Any SELECT query without a LIMIT clause has LIMIT 1000 appended before execution. The check is case-insensitive. The original query and the modified query are both returned in query_diff.original and query_diff.would_execute so the user can see exactly what Argus changed. This prevents accidental full-table scans from fetching millions of rows. The limit value is configurable via AUTO_LIMIT_DEFAULT in the environment.
   4.4 Pre-flight cost estimation
   Before executing any query, Argus runs EXPLAIN (FORMAT JSON) — not EXPLAIN ANALYZE, which would actually execute the query — and extracts the Total Cost from the plan root node. If the estimated cost exceeds the configured block threshold (default 10,000 cost units), the query is rejected with a 403 explaining the cost and suggesting how to add filters to reduce it. Admin role is exempt from this block. The cost is returned in every response for dashboard display even when under the threshold.
   4.5 Daily query budget
   Each user has a daily cost budget stored as a Redis counter (INCRBYFLOAT key with TTL set to seconds until midnight UTC). Before execution, Argus checks whether the current usage plus the estimated cost would exceed the daily limit. If yes, the query is rejected with a 429 showing the current usage, the limit, and the reset time. Budget is deducted only after a successful execution — failed or cached queries do not consume budget. Admin role receives a 10× budget multiplier.
   4.6 Read/write routing
   SELECT queries are routed to the PostgreSQL replica connection pool. INSERT, UPDATE, DELETE, and WITH (CTE) queries go to the primary connection pool. The routing decision is made by inspecting the first keyword after stripping whitespace. Primary and replica maintain separate asyncpg connection pools (min 5, max 20 connections each, configurable). A pool acquire timeout prevents indefinite waiting if the pool is exhausted.

5. Layer 3 — Execution features
   5.1 Circuit breaker
   The circuit breaker state (closed / open / half-open) is stored in Redis — not in a Python variable, so it survives container restarts. When 5 consecutive database failures occur, the circuit opens. While open, every request returns 503 instantly without attempting any database connection. After 30 seconds (configurable), one probe request is allowed through. If it succeeds, the circuit closes and all traffic resumes. If it fails, the cooldown resets and the circuit stays open. A webhook alert fires whenever the circuit transitions to open.
   5.2 Column encryption
   Columns configured in ENCRYPT*COLUMNS (default: ssn, credit_card) are encrypted before INSERT and decrypted after SELECT. The algorithm is AES-256-GCM with a new random 12-byte nonce generated for every encryption operation — reusing a nonce would break GCM security. The nonce is prepended to the ciphertext and the combined value is base64-encoded for storage. Decryption extracts the first 12 bytes as the nonce. A failed decryption returns the raw stored value rather than crashing. The encryption key is a 32-byte value from the environment — never committed to source control.
   5.3 Retry with exponential backoff
   Transient database errors — connection reset, too many connections, server closed the connection, timeout — trigger automatic retry. Non-transient errors (syntax errors, constraint violations) are raised immediately without retry. Retry delays are exponential: 100ms, 200ms, 400ms. After three failed attempts the request fails with 503. The retry logic wraps all direct database fetch calls. After max retries are exhausted, the failure is recorded for the circuit breaker.
   5.4 EXPLAIN ANALYZE — post-execution
   After a query executes successfully, Argus runs EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS) as a separate query and walks the returned plan tree recursively to extract: the root node scan type, actual execution time, rows processed, and all nested plan nodes. Sequential Scan nodes are specifically identified for index recommendations. EXPLAIN ANALYZE failures are caught silently — the main query result is returned even if plan analysis fails.
   5.5 Index recommendations
   For every Sequential Scan node found in the EXPLAIN ANALYZE output, Argus extracts column names from the query's WHERE clause using regex. If a scanned table column appears in the WHERE clause, Argus generates a ready-to-run CREATE INDEX statement: CREATE INDEX idx*{table}\_{column} ON {table}({column});. Multiple suggestions per query are possible. Duplicate suggestions are deduplicated. Index suggestions are returned even on cache hits because they are stored alongside the cached result.
   5.6 Query complexity scoring
   Every query receives a numeric complexity score: each JOIN adds 2, each subquery adds 3, SELECT \* adds 1, missing WHERE clause adds 2. Score 0–2 is low, 3–6 is medium, 7+ is high. The level and reasons are returned in every response. High complexity queries do not block, but the score is used by the slow query advisor to combine execution evidence with static analysis into a single recommendation.

6. Layer 4 — Observability features
   6.1 Trace IDs
   A UUID4 trace ID is generated as the very first operation in every request handler, before any middleware runs. It is stored on request.state.trace_id and included in every log line, every audit log entry, every slow query record, every webhook alert, and every response body — including error responses. Every failure in the system is traceable to its originating request.
   6.2 Immutable audit log
   Every request — including blocked ones, cached ones, and failed ones — is written to the audit_logs table. The write happens asynchronously via asyncio.create_task so it never adds latency to the response. The application code never calls UPDATE or DELETE on this table. Fields logged: trace_id, user_id, role, query fingerprint, query type, latency_ms, status (success / blocked / cached / error), cached flag, slow flag, anomaly flag, error message. The audit log can be exported to CSV via a streaming response that does not load all rows into memory.
   6.3 Redis metrics counters
   Cumulative counters are maintained in Redis for: requests_total, cache_hits, cache_misses, rate_limit_hits, slow_queries, errors. All increment calls are fire-and-forget. Latency samples are stored in a Redis list capped at 1000 entries via LTRIM. The /api/v1/metrics/live endpoint sorts the sample list and returns P50, P95, and P99 percentiles, plus cache hit ratio with division-by-zero protection. This endpoint is unauthenticated so dashboards can poll it freely.
   6.4 Webhook alerts
   When notable events occur, Argus fires an async HTTP POST to a configured Discord or Slack webhook URL. Events that trigger alerts: slow query detected, anomaly flag raised, honeypot table accessed, rate limit breached, circuit breaker opened. The payload uses Discord embed format with colour-coded event types (orange for slow query, red for anomaly, dark red for honeypot, red-orange for circuit open). Webhook failures are silently caught — an alert failure never crashes the main request flow.
   6.5 Table access heat map
   Every successful query increments a Redis ZINCRBY counter for the queried table in a sorted set. The /api/v1/admin/heatmap endpoint returns tables ranked by query count using ZREVRANGE. The frontend dashboard displays this as a bar chart showing hottest tables at the top. Useful for identifying which tables are under the most load and prioritising index creation.
   6.6 Health and status endpoints
   GET /health pings both PostgreSQL (SELECT 1) and Redis (PING) and returns a status for each plus an overall ok or degraded status. It always returns HTTP 200 so load balancers do not kill the service on degraded status. GET /api/v1/status returns a richer view including Redis connection status. Both endpoints are unauthenticated.

7. AI features
   7.1 Natural language to SQL
   POST /api/v1/ai/nl-to-sql accepts a plain English question and an optional schema_hint (e.g. 'table users(id, name, email)'). The LLM is instructed to return only a SQL query — no markdown, no explanation, no backticks. If the LLM returns an ERROR: prefix, the endpoint returns a structured error without executing anything. If valid SQL is returned, it is passed through the full Argus pipeline — all four layers — via run_pipeline(), not a separate database connection. RBAC masking applies to NL→SQL results exactly as it does to regular queries. If the generated SQL lacks a LIMIT clause, one is injected before execution.
   7.2 Query explanation
   POST /api/v1/ai/explain accepts any SQL query and returns a 2–4 sentence plain English explanation written for a non-technical reader. The LLM is instructed to describe what data is being retrieved or modified and what filters are applied, without using SQL terminology. This is accessible from the Monaco editor (select any query, click Explain) and from the AI chat panel (explain button on each result).
   7.3 AI anomaly explanation
   POST /api/v1/ai/explain-anomaly accepts a structured anomaly payload (type, baseline, detected value, user_id, table, timestamp) and returns a plain English narrative: what happened, how unusual it was, and what it might indicate. This is shown in the security center notification panel alongside the raw anomaly flag from the audit log.
   7.4 Dry-run mode
   Any query can be submitted with dry_run: true in the request body. Argus runs all security checks, validation, RBAC, fingerprinting, and cost estimation but does not execute the query against the database, does not write to cache, and does not write to the audit log. The response includes pipeline_checks (each check shows pass or fail), query_diff showing what Argus would have executed, cost_estimate, and complexity. Used by non-technical users to validate a query before running it.

8. Frontend — six pages
   8.1 Query workspace
   The primary working surface. Monaco Editor (the same engine as VS Code) for SQL editing with full syntax highlighting, line numbers, undo/redo, and SQL keyword autocomplete from the schema browser. Ctrl+Enter executes, Ctrl+Shift+F formats.
   The toolbar contains: Execute button, Dry-run button, Save button (saves to personal query library), and a role switcher dropdown (Admin / Readonly / Guest). Switching roles re-runs the current query and re-renders results — masking changes are visible immediately without re-logging in.
   The results panel shows a paginated table with column sorting. Masked values display a lock indicator. A 'cached' badge with latency comparison appears on cache hits. Export buttons for CSV and JSON.
   The analysis panel (collapsible sidebar) shows: scan type with colour coding (Seq Scan in amber, Index Scan in green), execution time, rows processed, cost, complexity score with reasons, budget usage bar, index suggestions each with one-click DDL copy, and the query diff viewer showing original vs executed with injected changes highlighted.
   When a query is blocked, a block explainer card replaces the error toast: the violated rule in plain English, the specific pattern matched, and a suggested fix. No raw JSON error messages for non-technical users.
   8.2 AI assistant
   A persistent chat panel. The user types plain English. Argus generates SQL, executes it through the full pipeline, and returns the result alongside an auto-generated plain English explanation in a single chat message. Follow-up questions refine the previous query — conversation context is maintained. Each result has an Explain button that appends a deeper explanation to the chat thread.
   The schema browser panel shows all tables and columns from information_schema with inferred relationships (user_id columns link to users.id). Clicking a table name inserts a SELECT template into the Monaco editor.
   8.3 Live dashboard
   Recharts line charts for request rate and P50/P95/P99 latency, all polling /metrics/live every 5 seconds. A cache hit ratio gauge. A table access heat map bar chart showing hottest tables. Per-user budget burn progress bars with colour change at 80% and 95%. System health indicators (green/amber/red dots) for DB primary, DB replica, Redis, and circuit breaker state with countdown on cooldown.
   Any query result can be pinned to the dashboard as a live tile with a configurable refresh interval. Pinned queries run through the full pipeline on each refresh — RBAC masking applies to live tiles.
   8.4 Admin panel
   Audit log table with full filtering (user, status, date range, table, anomaly flag, slow flag). Click any trace_id to expand the full query and pipeline result. CSV export streams the entire log. Slow query list sorted by execution time with one-click DDL application for index suggestions. User management: create, deactivate, change role, generate/revoke API keys. IP rules management: add/remove blocklist and allowlist entries. Compliance report export: select period and format, generates a structured summary of PII access, blocked queries, injection attempts, and anomalies.
   8.5 Security center
   In-app notification feed showing the last 20 security events: honeypot hits, anomaly flags, rate limit breaches, circuit breaker state changes. Each event links to the full audit log entry. Dedicated honeypot activity view with IP auto-ban status and manual unban option. Time-based access rule editor: configure per-role allowed hours and weekdays with timezone support. RBAC visualiser: shows what each role can and cannot see, with live preview.
   8.6 Account page
   API key management: generate new keys with labels and scope restrictions, view active keys with last-used timestamps, revoke with one click. Personal budget: daily usage bar chart over 7 days, top 5 most expensive personal queries. Query history: personal audit log filterable by date, status, and table — click any row to reload into the Monaco editor. Saved query library: personal named queries with tags, searchable, shareable to team library.

9. Python SDK and CLI
   9.1 Python SDK
   pip install argus-gateway installs the Gateway class. Supports JWT token auth and API key auth. Methods: login(username, password), query(sql, encrypt_columns=[], dry_run=False), explain(sql), nl_to_sql(question, schema_hint=''), status(), metrics(). All methods are synchronous wrappers using httpx.Client. Raise_for_status() on all responses — errors surface as Python exceptions with the full error detail.
   9.2 CLI
   The argus command provides a terminal interface: argus login <url> <username> <password> saves the token to ~/.argus_token. argus query '<sql>' executes and pretty-prints the result. argus status shows health of all components. argus explain '<sql>' returns the plain English explanation. All commands read from ~/.argus_token — no token flag required after login.

10. Deployment
    10.1 Starting the system
    git clone https://github.com/yourname/argus cd argus cp .env.example .env docker compose up --build
    Five Docker services start: the Argus gateway on port 8000, PostgreSQL primary on 5432, PostgreSQL replica on 5433, Redis on 6379, and the React frontend on 3001. All services have health checks. The gateway depends on PostgreSQL and Redis being healthy before starting.
    10.2 Available endpoints
    Endpoint Auth Purpose
    GET /health None DB + Redis ping, returns ok or degraded
    GET /api/v1/metrics/live None Live counters, latency percentiles, cache ratio
    POST /api/v1/auth/register None Register new user, returns JWT
    POST /api/v1/auth/login None Login, returns JWT token
    POST /api/v1/query/execute JWT / API Key Execute query through full 4-layer pipeline
    GET /api/v1/query/budget JWT / API Key Daily budget usage and remaining for current user
    POST /api/v1/ai/nl-to-sql JWT / API Key Natural language to SQL, executed through pipeline
    POST /api/v1/ai/explain JWT / API Key Plain English explanation of any SQL query
    GET /api/v1/admin/audit JWT (admin) Full audit log with filters
    GET /api/v1/admin/heatmap JWT (admin) Tables ranked by query count
    GET /api/v1/admin/slow-queries JWT (admin) Queries exceeding 200ms threshold with recommendations
    GET /api/v1/admin/compliance-report JWT (admin) GDPR/HIPAA evidence export in JSON or CSV
    GET /api/v1/docs None Auto-generated Swagger UI showing all endpoints

11. What makes Argus different from every competitor
    Every open source database proxy (PgBouncer, Pgpool-II, PgCat) handles connection management and nothing else. They have no security features. A SQL injection query or a DROP TABLE passes straight through.
    Every enterprise security gateway (DataSunrise, Heimdall Data) handles security and compliance but has no query performance intelligence. None of them run EXPLAIN ANALYZE, generate index DDL, or analyse query plans. They know who queried what but not whether the query was efficient.
    Formal (YC-backed, customers include Notion and Gusto) is the most direct competitor. It is a programmable security proxy with LLM anomaly detection. It has no query caching, no EXPLAIN integration, no index recommendations, and no open source self-hosted version.
    Argus is the only system that combines security enforcement and query performance intelligence in a single open source, self-hostable package deployable with one command.
    Unique features that no competitor has at any price:
    ● EXPLAIN ANALYZE with ready-to-run CREATE INDEX DDL generation from real execution plan data
    ● Explainable blocks — every rejected query returns the exact rule violated and what to fix, not a generic error
    ● Role-level cache scoping — admin and readonly users get different cached results, preventing data bleed
    ● Zero external monitoring stack — metrics served directly from the gateway via a REST endpoint
    ● Time-based access rules — configurable per-role allowed hours and weekdays
    ● Full session observability — every request traceable from entry to response via a single trace ID

12. Test coverage
    Test file What it covers Count
    test_ai.py NL→SQL, explainer, LLM disabled, API error handling 6
    test_analyzer.py Plan node extraction, WHERE column parsing, index suggestion generation 10
    test_audit.py Fire-and-forget pattern, log retrieval, user filter 3
    test_auth.py API key hashing, JWT create/decode, password hashing 3
    test_auto_limit.py Injection, case-insensitive check, semicolon stripping 7
    test_budget.py Under limit, exceeded, admin bypass, TTL, INCRBYFLOAT 6
    test_cache.py Miss, hit, write 3
    test_circuit_breaker.py Closed, open, failure recording 3
    test_complexity.py Low/medium/high scenarios 3
    test_cost_estimator.py Returns cost, non-SELECT, failure handling 3
    test_encryption.py Roundtrip, random nonce, graceful invalid input 3
    test_encryptor.py String encryption, query matching, row decryption 5
    test_executor.py First keyword detection, R/W routing 10
    test_fingerprinter.py Normalisation, consistency, table extraction 7
    test_heatmap.py Record access, empty, with data 3
    test_metrics.py Counter increment, pipeline latency, live metrics, division by zero 6
    test_rate_limiter.py Within limit, exceeded, anomaly flag, TTL on first increment 4
    test_rbac.py Column masking rules, PII masking patterns 14
    test_sdk_client.py Init, login, query, explain, NL→SQL, status, metrics 13
    test_validator.py Injection patterns, query types, clean query 8
    test_webhooks.py Skip when no URL, post to webhook, failure handling, colours 4
    test_full_pipeline.py Health, status, auth, injection, SQL blocking, metrics, admin auth 7

Total: 134 tests passing, 3 skipped (SDK file structure tests inside Docker), 0 failing

13. Placement readiness checklist
    Backend
    ● All 4 middleware layers execute in correct order for every request
    ● Every error returns the correct HTTP status code with a structured body
    ● trace_id present in every response including errors
    ● docker compose up --build starts all 5 services cleanly
    ● GET /health returns {status: ok, db: ok, redis: ok} when running
    ● GET /api/v1/docs loads Swagger with all endpoints documented
    ● SELECT executes end to end and returns result + full analysis object
    ● Same SELECT twice: second returns cached: true with lower latency
    ● DROP TABLE returns 400 with block_reasons and suggested_fix
    ● SQL injection returns 400 with structured error
    ● No auth header returns 401
    ● 5 wrong passwords: 6th attempt returns 423
    ● SELECT \* FROM users: hashed_password blocked for readonly role
    ● Email address masked as m\*\*\*@domain.com for readonly role
    ● Slow query (>200ms) appears in GET /api/v1/admin/slow-queries
    ● Honeypot table access returns 403, fires webhook, blocks IP
    ● Stopping postgres: subsequent requests return 503 (circuit open)
    ● Restarting postgres: after 30s cooldown, circuit closes and requests succeed
    ● NL-to-SQL generates valid SQL and executes it through full pipeline
    ● AI explain returns plain English explanation
    ● Dry-run returns pipeline_checks, cost, complexity — no rows
    ● GitHub Actions CI green on main branch
    Frontend
    ● Monaco editor loads with SQL syntax highlighting
    ● Results table shows data correctly with masked columns indicated
    ● Analysis panel shows scan type, cost, complexity, index suggestions
    ● Cache hit shows latency comparison vs first run
    ● Block explainer shows structured error with fix suggestion
    ● Role switcher re-runs query and shows masking difference immediately
    ● AI chat panel takes plain English and returns results
    ● Live dashboard charts update every 5 seconds
    ● Health status page shows green indicators for all services
    ● Admin panel shows audit log, slow queries, user management
    Testing and documentation
    ● pytest passes: 134 tests, 0 failures
    ● README has architecture diagram, feature table, and quick start
    ● README has 4 screenshots: Swagger, query response, cache hit, metrics
    ● Locust load test screenshot showing P95 latency for cached vs uncached
    ● SDK CLI demo: argus login, argus query, argus status all work

14. Demo sequence — under 3 minutes
    Practise this until the sequence is automatic. Each step should take 15–20 seconds.
    Step 1 Open /api/v1/docs — show the API is fully self-documenting. Every endpoint visible.
    Step 2 Login → get JWT token.
    Step 3 Run SELECT on users — show full response: trace_id, analysis, scan type, index suggestion with CREATE INDEX DDL.
    Step 4 Run same query again — show cached: true, latency drop from ~9ms to ~2ms.
    Step 5 Try DROP TABLE — show 400 with block_reasons: ['Query type not allowed: DROP'] and suggested_fix.
    Step 6 Try OR 1=1 injection — show 400 with injection detected, pattern identified.
    Step 7 Type English in the AI panel: 'show me users created this week' — watch SQL generate, execute, and results appear with masking.
    Step 8 Switch role to Readonly in the role switcher — same result, emails now masked as m\*\*\*@domain.com. Switch to Admin — masks disappear.
    Step 9 Open the live dashboard — show P50/P95/P99 charts updating, cache hit ratio, table heatmap.
    Step 10 docker stop postgres → instant 503 (circuit open) → docker start postgres → wait 30s → probe succeeds → circuit closes → requests resume.
