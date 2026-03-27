# Argus — Implementation Correctness Checklist

Paste this into Opus when you want a full audit of your implementation.
For each item, show the relevant code and Opus will tell you if it's correct,
broken, or missing.

---

## HOW TO USE

Paste this entire file as your first message, then follow with:
"Here is my current codebase — audit it against this checklist."
Then paste or attach your code files one by one.

Opus should respond to each section with:

- PASS — implemented correctly
- FAIL — implemented but broken (explain why)
- MISSING — not implemented yet
- PARTIAL — implemented but incomplete (explain what's missing)

---

## LAYER 1: SECURITY

### 1.1 Authentication

- [x] JWT tokens are signed with HS256 or RS256, not "none" algorithm
- [x] JWT expiry (exp claim) is checked on every request — not just at login
- [x] Expired tokens return 401, not 200 or 500
- [x] API keys are stored as SHA-256 hashes in DB, never as plaintext
- [x] API key lookup hits Redis first (fast path), DB only on cache miss
- [ ] Rotated keys have a grace period (old key still works for N hours)
- [ ] HMAC signature verification uses secrets.compare_digest() — NOT == operator
      (== is vulnerable to timing attacks, compare_digest is constant-time)
- [ ] HMAC timestamps are checked — requests older than 5 minutes are rejected
- [x] Missing auth header returns 401, not 403 or 500

### 1.2 Brute Force Protection

- [x] Failed attempt counter is per IP + per username (not just IP alone)
- [x] Counter uses Redis INCR + EXPIRE — not a DB row (DB writes on every failed auth = too slow)
- [x] Lockout threshold is configurable via .env, not hardcoded
- [x] Locked account returns 423 (Locked), not 401 (Unauthorized) — different status codes
- [x] TTL is set on the FIRST increment, not reset on every increment
      (if you call EXPIRE on every INCR, the lockout window resets each attempt — wrong)
- [x] Successful login clears the failed attempt counter
- [x] Brute force check happens BEFORE password verification (fail fast)

### 1.3 IP Filter

- [x] IP blocklist is a Redis SET (SISMEMBER = O(1)), not a DB query on every request
- [x] Allowlist logic: if allowlist is empty, everyone is allowed (don't accidentally block all)
- [x] IP check is the FIRST thing after trace ID generation — before auth, before anything else
- [ ] Admin can add/remove IPs via API without restarting the server (hot config)
- [x] request.client.host is used for IP — not a user-supplied header like X-Forwarded-For
      (X-Forwarded-For can be spoofed — only use it if you're behind a trusted reverse proxy)

### 1.4 Rate Limiter

- [x] Window key includes the current time bucket: key = f"ratelimit:{user_id}:{now // 60}"
- [x] EXPIRE is set to 2x the window (not 1x) to handle edge cases at window boundaries
- [x] Rate limit is per authenticated user_id, not per IP (IPs can be shared/NATted)
- [x] Anomaly baseline uses rolling window of last N buckets, not a single average
- [x] Anomaly detection does NOT block — it flags and alerts only
      (false positive blocks = legitimate users locked out = bad)
- [x] Rate limit counter uses INCR (atomic) not GET + SET (race condition)

### 1.5 Query Validator

- [x] Regex patterns use re.IGNORECASE — SQL keywords are case-insensitive
- [x] Injection patterns check for: OR 1=1, --, ;--, UNION SELECT, SLEEP(), WAITFOR, /\*\*/
- [x] Allowed query types are checked by first keyword only — not contains()
      (contains("SELECT") would pass "DROP TABLE; SELECT 1" — wrong)
- [x] query.strip().split()[0].upper() is used to get first keyword safely
- [x] Empty query string is handled (split() on empty string crashes)
- [x] Validation happens on the ORIGINAL query before any modifications
- [x] Honeypot table check happens HERE, before any processing

### 1.6 RBAC

- [x] Role is extracted from JWT payload — never from request body or query params
- [x] Table access check is deny-by-default: unknown role = no access
- [x] Column strip happens AFTER execution on the result rows, not by modifying the query
      (modifying SELECT queries to remove columns is fragile — strip from results instead)
- [x] strip_denied_columns handles empty result set (empty list) without crashing
- [x] Role config is loaded from settings/DB — not hardcoded strings scattered in code

---

## LAYER 2: PERFORMANCE

### 2.1 Query Fingerprinting

- [x] Normalization replaces: integers, floats, string literals, IN list values
- [x] Normalization is case-insensitive and whitespace-normalized
- [x] Cache key includes role: same query by admin and readonly = different cache entries
      (admin gets unmasked data, readonly gets masked — they must NOT share cache)
- [x] Cache key includes table name for efficient invalidation pattern matching
- [x] Fingerprint is generated AFTER validation (don't fingerprint invalid queries)

### 2.2 Redis Cache

- [x] Cache GET happens before DB connection is opened (avoid opening pool connection on hit)
- [x] Cache SET uses SETEX (set + expire in one atomic command), not SET + EXPIRE separately
- [x] Cached result is JSON serialized — datetime objects need custom serializer
      (json.dumps(datetime.now()) crashes — use isoformat() or a custom default)
- [x] Cache key for SELECT only — INSERT/UPDATE/DELETE are never cached
- [x] Cache stores the FINAL result (after decryption + masking), not the raw DB rows
      (if you cache raw encrypted rows, every cache hit needs decryption = defeats the purpose)
- [x] Cache read is wrapped in try/except — Redis failure should not crash the query

### 2.3 Cache Invalidation

- [x] On INSERT/UPDATE/DELETE: table name is parsed from the query
- [x] SCAN + DEL uses a pipeline for efficiency (not one DEL per key)
- [x] SCAN uses COUNT hint (e.g. COUNT=100) to batch results
- [x] SCAN loop continues until cursor returns 0 (cursor != 0 means more keys remain)
- [ ] Invalidation is fire-and-forget (asyncio.create_task) — doesn't block the response
- [x] If no keys found for the table pattern, that's fine — no error

### 2.4 Auto-LIMIT

- [x] LIMIT check is case-insensitive (LIMIT, limit, Limit all match)
- [x] Auto-LIMIT only applies to SELECT queries — never to INSERT
- [ ] Original query and modified query are both stored for the diff viewer
- [x] Injected LIMIT value is configurable via .env (AUTO_LIMIT_DEFAULT)
- [x] If query already has LIMIT 5, don't inject LIMIT 1000 on top of it

### 2.5 Cost Estimator

- [x] Uses EXPLAIN (FORMAT JSON) — NOT EXPLAIN ANALYZE (ANALYZE actually runs the query)
- [x] JSON result is parsed: plan[0]["Plan"]["Total Cost"]
- [x] EXPLAIN failure is caught — don't block the query if EXPLAIN fails
- [ ] Cost threshold check is skipped for admin role
- [x] Cost is included in the response even if under threshold (for dashboard display)

### 2.6 Daily Budget

- [x] Budget key includes date: f"budget:{user_id}:{today}" in UTC, not local time
- [x] TTL is set to seconds until midnight UTC — not a fixed 86400 (that would be rolling, not daily)
- [x] INCRBYFLOAT is used (not INCR) since cost values are floats
- [x] Budget check happens AFTER cost estimation, BEFORE execution
- [x] Budget deduction happens AFTER successful execution — not before
      (deducting before execution means failed queries still consume budget — wrong)
- [ ] Admin role gets higher (or unlimited) budget — not same as readonly

---

## LAYER 3: EXECUTION

### 3.1 Circuit Breaker

- [x] State is stored in Redis — NOT in a Python global variable
      (global variable resets on every container restart — Redis persists)
- [x] State machine is correct:
      CLOSED → (N failures) → OPEN → (cooldown) → HALF_OPEN → (success) → CLOSED
      CLOSED → (N failures) → OPEN → (cooldown) → HALF_OPEN → (failure) → OPEN
- [x] In OPEN state: check timestamp before returning 503
      (don't return 503 forever — check if cooldown has elapsed)
- [x] In HALF_OPEN state: only ONE request is let through (not all requests)
- [x] Failure counter is reset to 0 when circuit closes (not just when it opens)
- [x] Circuit breaker fires a webhook alert when it opens
- [x] DB timeout errors count as circuit breaker failures
- [x] Circuit breaker check is BEFORE connection pool acquire
      (don't acquire a pool connection only to immediately return 503)

### 3.2 Column Encryption

- [x] AES-256-GCM is used — NOT AES-CBC (GCM is authenticated, CBC is not)
- [x] A new random nonce (12 bytes) is generated for EVERY encryption call
      (reusing a nonce with the same key completely breaks GCM security)
- [x] Nonce is prepended to ciphertext before base64 encoding: nonce + ct
- [x] Decryption extracts nonce as first 12 bytes: data[:12]
- [x] Encryption key is exactly 32 bytes — padded or truncated if wrong length
- [x] Encrypted values are stored in the DB — never the plaintext
- [x] encrypt_columns list is checked case-insensitively (column names vary)
- [x] decrypt_value() handles invalid/corrupted ciphertext gracefully (try/except)
- [x] Encryption happens BEFORE the query is executed (for INSERT)
- [x] Decryption happens AFTER results are fetched (for SELECT)

### 3.3 PII Masking

- [x] Masking happens AFTER decryption — mask the plaintext, not the ciphertext
- [x] Admin role receives fully decrypted, unmasked values
- [x] Mask patterns are correct:
      SSN: show last 4 only → **\*-**-6789
      Email: show first char + domain → m**\*@test.com
      Phone: show first 2 + last 2 → 98\*\*\***10
- [x] Masking is applied per-column per-row — not replacing the entire row value
- [x] None/null values are passed through without masking (don't mask None)
- [x] Masking happens on a COPY of the row dict — never mutate the original

### 3.4 R/W Routing

- [x] SELECT queries go to replica connection
- [x] INSERT, UPDATE go to primary connection
- [x] First keyword detection is reliable: query.strip().split()[0].upper()
- [x] WITH (CTE) queries that contain SELECT are routed to primary (they may modify data)
- [x] If replica is down, do NOT silently fall back to primary
      (silent fallback hides replica failures — log it and surface it)

### 3.5 Connection Pool

- [x] Pool is created ONCE at startup in lifespan — not per request
- [x] Pool is closed gracefully at shutdown
- [x] Pool acquire has a timeout — don't wait forever if pool is exhausted
- [x] Pool min/max sizes are configurable via .env
- [x] Primary and replica have SEPARATE pools (not the same pool)

### 3.6 Query Execution + Timeout

- [x] asyncio.wait_for() wraps the DB call with the timeout
- [x] TimeoutError is caught and returns 504 (Gateway Timeout), not 500
- [x] Timeout is configurable per role (admin gets longer timeout)
- [x] Retry only happens on TRANSIENT errors (connection reset, too many connections)
- [x] Retry does NOT happen on query errors (syntax error, constraint violation)
      (retrying a constraint violation 3 times just fails 3 times — wasteful)
- [x] Retry delays are: 100ms, 200ms, 400ms (exponential, not fixed)
- [x] After max retries, the failure is recorded for circuit breaker

### 3.7 EXPLAIN ANALYZE

- [x] EXPLAIN ANALYZE runs as a SEPARATE query AFTER the main query completes
- [x] FORMAT JSON is used: EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS)
- [x] Seq Scan nodes are found by recursively walking the plan tree
      (Seq Scan can be nested inside a Hash Join, Nested Loop, etc.)
- [x] execution_time_ms is extracted from "Actual Total Time" of the root node
- [x] EXPLAIN ANALYZE failure does NOT fail the main request (wrap in try/except)
- [x] EXPLAIN result is NOT included in the Redis cache (it's metadata, not result data)

### 3.8 Index Recommendations

- [x] Rule fires only when: Seq Scan AND the scanned column appears in WHERE clause
- [x] Generated DDL is syntactically correct: CREATE INDEX idx*{table}*{col} ON {table}({col});
- [x] Multiple suggestions are possible (multiple Seq Scans in one query)
- [x] Duplicate suggestions are deduplicated (don't suggest same index twice)
- [x] Suggestions are returned even on cache hits (re-run EXPLAIN or store with cache)

---

## LAYER 4: OBSERVABILITY

### 4.1 Trace IDs

- [ ] trace_id is generated as the VERY FIRST thing in every request handler
- [ ] trace_id is stored on request.state.trace_id for access in all middleware
- [ ] trace_id is included in EVERY log line from that request
- [ ] trace_id is returned in EVERY response (success AND error)
- [ ] trace_id is passed to audit log, slow query log, and webhook alerts

### 4.2 Audit Log

- [ ] Audit log table has NO UPDATE and NO DELETE permissions in application code
      (insert-only is enforced in code — not just convention)
- [ ] Every request is logged — including failed requests (auth failures, blocked queries)
- [ ] Audit log write is asyncio.create_task() — fire and forget, never blocks response
- [ ] Audit log includes: trace_id, user_id, role, fingerprint, query_type,
      latency_ms, status, cached, slow, anomaly_flag, error_message, created_at
- [ ] CSV export streams the response (StreamingResponse) — don't load all rows into memory

### 4.3 Metrics

- [ ] All metric INCR calls are fire-and-forget (create_task) — never block the response
- [ ] Latency samples list is capped (LTRIM to last 1000) — don't grow unbounded
- [ ] Percentile calculation sorts the samples array before indexing
      (unsorted array gives wrong percentiles)
- [ ] /metrics/live is NOT authenticated (Prometheus/dashboards need unauthenticated access)
      OR is separately authenticated — don't require user JWT for metrics
- [ ] Cache hit ratio handles division by zero (total = 0 case)
- [ ] Redis metric keys never expire — they're cumulative counters

### 4.4 Webhook Alerts

- [ ] Webhook POST uses httpx.AsyncClient — NOT requests (requests is sync, blocks event loop)
- [ ] Webhook call has a timeout (timeout=5) — don't hang forever on slow webhook
- [ ] Webhook failure is silently caught — NEVER raises an exception into the main flow
- [ ] Webhook is always fire-and-forget (asyncio.create_task)
- [ ] Webhook payload matches Discord/Slack embed format exactly
      (wrong payload format = silent failure — test with a real Discord webhook)

### 4.5 Health Check

- [ ] /health checks BOTH DB and Redis — not just one
- [ ] DB check uses a real query: SELECT 1 — not just checking if engine object exists
- [ ] Redis check uses PING — not just checking if client object exists
- [ ] /health returns 200 even if degraded (so load balancers don't kill the service)
      Use status: "degraded" in body — but still return HTTP 200
- [ ] /health is unauthenticated — monitoring systems can't provide JWT tokens

---

## CRITICAL CORRECTNESS ISSUES

## (things that look right but are subtly broken)

- [ ] NEVER use Python == to compare secrets, tokens, or hashes
      Use secrets.compare_digest() always — timing attack prevention

- [ ] NEVER store raw API keys or passwords in DB
      Store hash only. Return raw key once at creation. Never again.

- [ ] NEVER reuse AES-GCM nonces
      os.urandom(12) on EVERY encryption call. Never store/reuse a nonce.

- [ ] NEVER cache results before masking/decryption is applied
      Cache the final user-facing result, not the raw DB rows.

- [ ] NEVER let cache role bleed: admin and readonly must have separate cache keys
      Same query, different roles = different data = different cache entries.

- [ ] NEVER use GET + SET for Redis counters (race condition)
      Use INCR / INCRBYFLOAT (atomic operations only)

- [ ] NEVER call EXPIRE on every INCR for brute force counter
      Set TTL only on first INCR (when count becomes 1)
      Otherwise the lockout window resets on every failed attempt.

- [ ] NEVER let webhook/audit failures crash the main request
      Every fire-and-forget task must be wrapped in try/except internally.

- [ ] NEVER run EXPLAIN ANALYZE for cost estimation (pre-flight)
      EXPLAIN without ANALYZE for pre-flight (doesn't execute the query)
      EXPLAIN ANALYZE only POST-execution (actually runs the query)

- [ ] NEVER let circuit breaker state live in a Python global/module variable
      Must be in Redis — global state is lost on every container restart.

- [ ] NEVER blindly trust X-Forwarded-For for IP filtering
      Use request.client.host unless you're behind a verified trusted proxy.

- [ ] NEVER deduct query budget before execution completes
      Deduct AFTER successful execution only.

---

## FINAL INTEGRATION CHECKS

- [ ] All 4 middleware layers execute in the correct order for every request
- [ ] Error in any layer returns the correct HTTP status code (not always 500)
- [ ] trace_id is present in every single response — success and error
- [ ] Docker Compose: all 5 services start cleanly with docker compose up --build
- [ ] /health returns {"status": "ok", "db": "ok", "redis": "ok"} when everything is running
- [ ] /api/v1/docs loads and shows all endpoints (Swagger auto-docs working)
- [ ] A SELECT query executes end-to-end and returns result + analysis + pipeline_summary
- [ ] Same SELECT twice: second response shows cached=true and lower latency
- [ ] A DROP TABLE attempt returns 400
- [ ] An injection attempt returns 400
- [ ] A request with no auth header returns 401
- [ ] After 5 wrong passwords: 6th attempt returns 423
- [ ] Slow query (>200ms) appears in GET /api/v1/admin/slow-queries
- [ ] Honeypot table access returns 403 and fires webhook
- [ ] Stopping postgres container → subsequent requests return 503 (circuit open)
- [ ] Restarting postgres → after cooldown, circuit closes and requests succeed
- [ ] GitHub Actions CI runs and passes on push to main

---

## DEMO SEQUENCE CHECKLIST

## (practice this until it takes under 3 minutes)

- [ ] Step 1: Open /api/v1/docs — show self-documenting API
- [ ] Step 2: Login → get JWT token
- [ ] Step 3: Run SELECT → show full response with analysis, scan type, index suggestions
- [ ] Step 4: Run same SELECT again → show cached=true, latency drop
- [ ] Step 5: Try DROP TABLE → show 400 with clear error message
- [ ] Step 6: Try SQL injection → show 400 with injection detected message
- [ ] Step 7: Run a slow query → show Discord/Slack ping within 2 seconds
- [ ] Step 8: Type English question → NL→SQL → show generated SQL + result
- [ ] Step 9: Open React dashboard → show live metrics updating
- [ ] Step 10: docker stop postgres → show instant 503 → docker start postgres →
      wait 30s → show circuit half-open → show recovery

---

_Run this checklist against your code before every demo rehearsal and before
submitting to any placement. A clean pass here = a confident interview._
