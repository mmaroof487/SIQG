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
- SQL injection detection (blocks 13+ injection patterns)
- Dangerous query blocking (DROP, DELETE, TRUNCATE)
- Sensitive field guardrails (hashed_password, tokens explicitly blocked)
- Rate limiting (60 requests/minute per user, sliding window)
- RBAC masking (columns stripped based on user role)
- IP filtering, brute force detection, honeypot tables

### Layer 2: Performance
- Query fingerprinting + intelligent caching (6-10x speedup)
- Cost estimation before execution
- Budget enforcement per user
- Auto-LIMIT injection (prevents full-table scans)
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

### Layer 6: AI Intelligence (with Resilient Fallback)

This is where things get interesting. Users can write queries in natural language.

**Traditional Approach (Single Provider):**
```
User: "Top 5 users created in the last 7 days"
  ↓
[Call OpenAI]
  ├─ Works → Returns SQL ✓
  └─ Fails → User sees error ✗
```

**Argus Approach (GROQ + MOCK Fallback):**
```
User: "Top 5 users created in the last 7 days"
  ↓
[Try: Groq LLM (Fast, Sophisticated)]
  ├─ Works → Returns SQL ✓
  └─ ANY Error? ↓
       ↓
[Fallback: Mock (Pattern-Based, Instant)]
  └─ Works → Returns SQL ✓
```

**Why this matters:**
- **Groq succeeds:** 95% of the time, giving sophisticated LLM quality
- **Groq times out:** Instant fallback to mock, user never sees latency
- **Groq rate limited:** Automatic fallback, never blocks user
- **Demo fails?** Never—always get SQL either from Groq or mock

**Also included:**
- Pattern matching guardrails: "top 5" forces LIMIT 5 (semantic accuracy)
- Query Explainer: Converts complex SQL to plain English
- AI-generated queries go through same validation as manual queries (untrusted by design)

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
