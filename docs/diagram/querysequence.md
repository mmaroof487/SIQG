# Request Sequence Diagram — Query Execution (All Phases)

## Overview

Detailed step-by-step sequence for a single query request going through the entire gateway pipeline (cache miss path). Shows both the gateway-internal logic and the Redis/PostgreSQL calls.

**Scope:** Standard query with no cache hit, no dry-run, no external connection. AI endpoint sequence shown separately below.

---

## Standard Query Execution (Cache Miss)

```mermaid
sequenceDiagram
    participant C as Client (Browser / SDK)
    participant G as Argus Gateway
    participant R as Redis
    participant PGr as PostgreSQL Replica
    participant PGw as PostgreSQL Primary
    participant LLM as Groq / Mock LLM

    C->>G: POST /api/v1/query/execute\n{sql, connection_id?, dry_run?}\nAuthorization: Bearer <token>

    Note over G: Auth Layer
    G->>G: Generate trace_id (UUID)
    G->>G: Decode JWT → user_id, role, exp
    G->>G: Check is_active (user.is_active)
    G->>R: GET apikey:{hash} (if API key auth)
    R-->>G: user_data {role, allowed_tables, ...}
    G->>R: SISMEMBER argus:ip:blocklist {client_ip}
    R-->>G: 0 (not blocked)

    Note over G: Security Layer
    G->>G: Honeypot table detection
    G->>R: INCR argus:ratelimit:{user_id}:{bucket}
    R-->>G: count=3 (under limit)
    G->>G: SQL injection regex (13+ patterns)
    G->>G: Sensitive column check (hashed_password, etc)
    G->>G: Query type allowlist (DROP blocked)
    G->>G: Time-based RBAC (allowed_hours check)
    G->>G: API key scope check (allowed_tables)

    Note over G: Performance Layer
    G->>G: Fingerprint: normalize + SHA-256
    G->>R: GET argus:cache:{conn_scope}:{fingerprint}:{role}
    R-->>G: nil (cache miss)
    G->>G: Auto-inject LIMIT 1000 (if no LIMIT)
    G->>PGr: EXPLAIN (FORMAT JSON) SELECT...
    PGr-->>G: cost=42.5
    G->>R: INCRBYFLOAT argus:budget:{user_id}:{date} 42.5
    R-->>G: 1042.5 (under daily limit)

    Note over G: Execution Layer
    G->>R: GET argus:circuit:replica
    R-->>G: state=closed
    G->>G: Pre-decrypt encrypted input columns
    G->>PGr: SELECT ... LIMIT 1000
    PGr-->>G: rows=[{...}] (18.5ms)
    G->>PGr: EXPLAIN (ANALYZE, FORMAT JSON) SELECT...
    PGr-->>G: scan=Index Scan on users_pkey, rows=5
    G->>G: Decrypt result columns (AES-256-GCM)
    G->>G: RBAC masking: strip deny-list cols, redact PII

    Note over G: Observability Layer
    G->>R: SETEX argus:cache:{conn_scope}:{fp}:{role} 60 {rows}
    G->>R: SADD argus:cache_tags:{conn_scope}:users {cache_key}
    R-->>G: ok
    G->>PGw: INSERT INTO audit_logs (...) (async, fire-and-forget)
    G->>R: INCR argus:metrics:requests_total
    G->>R: LPUSH argus:metrics:latency_samples 18.5
    G->>R: ZINCRBY argus:heatmap users 1

    Note over G: Slow Query Check
    G->>G: latency 18.5ms < 200ms threshold → skip webhook

    G-->>C: 200 OK\n{trace_id, rows, cached:false,\nlatency_ms:18.5, analysis:{index_recommendation}}
```

---

## Cache Hit Path (Fast)

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Argus Gateway
    participant R as Redis

    C->>G: POST /api/v1/query/execute {same sql, same role}
    G->>G: Auth + Security + Rate limit checks
    G->>G: Fingerprint query
    G->>R: GET argus:cache:{conn_scope}:{fingerprint}:{role}
    R-->>G: {rows} (2.1ms cache hit)
    G->>G: RBAC masking applied to cached rows
    G->>PGw: INSERT INTO audit_logs (async)
    G->>R: INCR argus:metrics:cache_hits
    G-->>C: 200 OK {trace_id, rows, cached:true, latency_ms:2.1}
```

---

## AI Endpoint Sequence

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Argus Gateway
    participant R as Redis
    participant LLM as Groq API
    participant M as Mock LLM

    C->>G: POST /api/v1/ai/nl-to-sql\n{question: "show top 5 users"}\nAuthorization: Bearer <token>

    Note over G: Auth + AI Guards
    G->>G: JWT decode → user_id, role
    G->>R: INCR argus:ai_ratelimit:{user_id}:{bucket}
    R-->>G: count=3 (< 20 limit)
    G->>G: Topic check: "users" ∈ DB keywords ✅
    G->>G: Length check: 20 chars < 2000 ✅

    Note over G: LLM Call
    G->>LLM: POST /chat/completions\n{prompt, schema_hint}
    alt Groq succeeds
        LLM-->>G: "SELECT * FROM users ORDER BY created_at DESC LIMIT 5"
    else Groq fails / timeout
        G->>M: pattern_match("top 5 users")
        M-->>G: "SELECT id, username, created_at FROM users ORDER BY created_at DESC LIMIT 5"
    end

    G-->>C: 200 OK {generated_sql, provider, cached:false}
```

---

## Token Refresh Sequence

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Argus Gateway
    participant PG as PostgreSQL Primary

    C->>G: POST /api/v1/auth/refresh\nAuthorization: Bearer <expired_token>

    G->>G: Decode JWT without exp enforcement\n(verify_exp=False)
    G->>G: Check: now <= exp + 300s (5-min grace)?
    alt within grace window
        G->>PG: SELECT * FROM users WHERE id = {user_id}
        PG-->>G: user record
        G->>G: Check user.is_active
        G->>G: Extract role.value (re-reads from DB — may have changed)
        G->>G: create_jwt(user_id, role_value)
        G-->>C: 200 OK {access_token, role}
    else expired > 5 min ago
        G-->>C: 401 Token has expired. Please log in again.
    end
```

---

_Last Updated: June 2026_
