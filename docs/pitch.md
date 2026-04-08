# Argus: Secure Intelligent Query Gateway

I built a system called **Argus**, a middleware layer that sits between applications and databases to provide security, intelligence, and control.

## The Problem

Most applications send queries directly to databases with almost no control:

- **SQL Injection:** Attackers craft malicious queries that succeed
- **Performance Issues:** Expensive queries crash the database without warning
- **Zero Visibility:** No audit trail of who accessed what data or why
- **Data Leaks:** Sensitive fields (passwords, tokens) returned in results
- **Unreliability:** No retry logic, timeout handling, or graceful degradation

## The Solution: 6-Layer Pipeline

Argus intercepts every query and processes it through 6 production-grade layers:

### Layer 1: Security

- SQL injection detection (blocks 13+ injection patterns: OR 1=1, UNION SELECT, --, /\*, xp_cmdshell, etc.)
- Dangerous query blocking (DROP, DELETE, TRUNCATE, ALTER)
- **Sensitive field protection (3-layer defense-in-depth):**
  - Layer 1: Query-level blocking for explicit sensitive field references (SELECT hashed_password → 403)
  - Layer 2: RBAC masking removes denied columns from `SELECT *` post-execution
  - Layer 3: Blind DLP regex scans all string values for PII patterns (emails, SSNs, credit cards)
  - Centralized constant: `SENSITIVE_FIELDS = {hashed_password, password, token, api_key, secret, internal_notes}`
- Rate limiting (60 requests/minute per user, sliding window with anomaly detection)
- RBAC masking (columns stripped based on user role: Admin/Readonly/Guest)
- IP filtering, brute force detection (5 failed logins = 423 Locked status), honeypot tables
- Authentication: JWT (HS256) + API Keys (SHA-256 hashed)

### Layer 2: Performance

- Query fingerprinting + intelligent caching (6-10x speedup, role-separated)
- Cost estimation before execution (EXPLAIN without running)
- Budget enforcement per user (daily limits, admin bypass)
- **Auto-LIMIT injection** (NL→SQL generates unbounded SELECT → Argus injects LIMIT 1000 automatically)
- Read/write routing (SELECTs to replica, writes to primary)

### Layer 3: Execution

- Circuit breaker (auto-fail if database errors spike)
- Exponential backoff retry logic (100ms → 200ms → 400ms)
- Timeout protection (10-second limit per query)
- Connection pool management from asyncpg

### Layer 4: Observability

- Audit logging (every query logged with trace IDs)
- Live metrics (cache hit ratio, latency percentiles, errors)
- Query heatmap (most accessed tables)
- Slow query detection (alerts on >200ms queries)
- Webhook notifications for critical events

### Layer 5: Security Hardening

- AES-256-GCM encryption for sensitive columns
- Post-execution field masking
- Blind regex DLP (detects PII/emails regardless of column)
- IP-level access control

### Layer 6: AI Intelligence (with Production-Hardened Fallback)

**Why resilient architecture matters:**
In demo environments, you need queries to ALWAYS work, never fail. Single-provider LLM architectures risk API timeouts, rate limiting, or network issues causing demo failure and looking bad in front of executives.

Argus uses **Groq + Mock Fallback** dual-provider architecture:

```
User: "Top 5 users by spending"
    ↓
[Try: Groq LLM (primary, sophisticated)]
    ├─ Works within 1 second? → Return SQL ✅
    └─ Groq timeout/error/rate-limited? ↓
           ↓
    [Auto-fallback: Mock (pattern-based, instant)]
    └─ Match "top 5" pattern → Instantly return SQL ✅
```

**Provider Details:**

- **Groq (Llama 3.1 8B):** <1 second response, sophisticated SQL generation, free tier with no practical rate limits
- **Mock:** Pattern-based regex matcher for 95% of common questions (handles "top N", "how many", "average", etc.), never fails
- **Behavior:** ANY failure from Groq (timeout, HTTP error, invalid response) triggers automatic fallback

This means:

- ✅ Demos never fail due to LLM
- ✅ 95% of user questions work instantly via Mock
- ✅ Complex questions still get Groq quality when available
- ✅ Zero retry logic needed (automatic seamless fallback)

**Additional Features:**

- LIMIT injection: Post-generation, auto-appends `LIMIT 1000` if missing
- Semantic guardrails: Pattern matching for "top N" → `LIMIT N`, "count" → `GROUP BY`, etc.
- Query Explainer: Converts complex SQL to plain English explanations
- Dry-Run Mode: Test queries before execution (safety checks, cost estimation, complexity scoring)
- All AI-generated queries validated through same 6-layer pipeline as manual queries (untrusted by design)

## Production Hardening

Beyond features, I focused on reliability:

- **Zero Async Errors:** All coroutines properly awaited (tested against Python 3.14)
- **Zero Deprecations:** Uses latest Pydantic v2, bcrypt-only passlib
- **134+ Unit Tests:** Security, performance, execution, AI, all tested
- **71%+ Coverage:** Focused on critical paths
- **Docker Deployment:** PostgreSQL primary + replica, Redis, gateway in containers
- **Graceful Degradation:** Failures in monitoring don't cascade to user queries

## Beyond REST APIs

Users interact via:

1. **HTTP APIs:** Standard REST endpoints for queries, metrics, health
2. **Python SDK:** `from argus import Gateway; g.nl_to_sql("show top 5 users")`
3. **CLI Tool:** `argus query "SELECT * FROM users LIMIT 10"`
4. **Programmatic:** Full Python interface for automation

## Real Performance Results

From end-to-end testing:

```
Security Layer:
  ✓ SQL injection blocked
  ✓ Rate limiting enforced (57 allowed, 8 blocked per minute)

Performance Layer:
  ✓ Cache speedup: 8-10x (2ms cached vs 18ms fresh)
  ✓ Caching metrics: Accurate tracking of hits/misses

AI Intelligence:
  ✓ "Top 5 users" → LIMIT 5 (pattern matched, guaranteed accuracy)
  ✓ "How many users?" → COUNT(*) (pattern matched, instant)
  ✓ Explain: Generates specific, natural language explanations
  ✓ Fallback: GROQ fails → Mock takes over (seamless)

Security:
  ✓ Sensitive fields blocked at query level (defense-in-depth)
  ✓ RBAC masking verified (hashed_password stripped)
  ✓ All tests passing (100% suite)
```

## Standing Out Against Competitors

Most query proxies focus on performance or security—Argus combines:

- **Resilient AI:** GROQ + MOCK fallback means zero demo failures
- **Defense-in-Depth:** Sensitive fields blocked at 3 levels (query, RBAC, post-execution)
- **True Intelligence:** Pattern matching + LLM = accurate semantic SQL
- **Production Hardened:** 134+ tests, zero deprecations, async-correct

The key insight: A gateway isn't just about blocking queries—it's about enabling safe, intelligent, auditable database access at scale.

## The Vision

In a world where LLMs generate SQL, where databases have zero visibility into usage patterns, and where one bad query can down production—**Argus provides the control layer.** It's not about replacing engineers, but empowering them and the business with visibility, safety, and intelligence over database access.
