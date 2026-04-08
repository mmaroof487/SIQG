# Request Pipeline — Complete Query Flow (All 32 Steps)

## Overview

Complete flow of a query request through ALL security, performance, execution, observability, hardening, and AI layers (Tiers 1-6, Steps 1-32).

**Scope:** This diagram shows the complete pipeline for `/api/v1/query/execute` endpoint including all new Tier 6 polish features.

**Related:** AI endpoints (`/api/v1/ai/nl-to-sql`, `/api/v1/ai/explain`, `/api/v1/ai/explain-anomaly`) have parallel pipelines — see [systemarchitecture.md](systemarchitecture.md) for integrated architecture.

---

## Complete Request Pipeline (11+ Stages)

```mermaid
flowchart TD
    A([Incoming Request]) --> B[Generate trace_id]

    %% Authentication Layer
    B --> C{JWT or API Key Valid?}
    C -->|invalid| C1([401 Unauthorized])
    C -->|valid| D[Validate API key scope<br/>allowed_tables/allowed_query_types]
    D --> D1{Scope allows<br/>this table?}
    D1 -->|no| D2([403 Forbidden - Scope])

    %% Security Layer - IP & Honeypot
    D1 -->|yes| E{IP in blocklist?}
    E -->|yes| E1([403 Forbidden - Blocked IP])
    E -->|no| F{Honeypot intrusion<br/>detected?}
    F -->|yes| F1([403 Forbidden + IP Ban 24h])

    %% Performance - Rate Limiting
    F -->|no| G{Rate limited?<br/>per-role tier}
    G -->|yes| G1([429 Too Many Requests])

    %% Security - Query Validation
    G -->|no| H{SQL Injection<br/>detected?}
    H -->|yes| H1([400 Injection Blocked])
    H -->|no| I{Sensitive column<br/>access?}
    I -->|yes| I1([403 Access Denied])
    I -->|no| J{Query type allowed?<br/>SELECT/INSERT only}
    J -->|no| J1([400 Type Not Allowed])

    %% Security - Time-Based RBAC
    J -->|yes| K{Time-based RBAC<br/>allowed hours?}
    K -->|no| K1([403 Blocked - Outside Hours<br/>blocked_until field])

    %% Performance - Caching
    K -->|yes| L[Fingerprint query<br/>normalize whitespace]
    L --> M{Cache hit?<br/>Redis lookup}
    M -->|yes| M1[Return cached result<br/>metadata]

    %% Performance - Cost Estimation
    M -->|no| N[EXPLAIN cost estimate]
    N --> O{Budget exceeded?<br/>daily limit}
    O -->|yes| O1([429 Budget Exhausted])

    %% Execution - Circuit Breaker
    O -->|no| P{Circuit breaker<br/>open?}
    P -->|yes| P1([503 Service Unavailable])

    %% Execution - Column Encryption
    P -->|no| Q[Decrypt columns<br/>AES-256-GCM]
    Q --> R{SELECT or<br/>INSERT/UPDATE?}

    %% Execution - Database
    R -->|SELECT| S1[Route to Replica<br/>read-only connection]
    R -->|INSERT/UPDATE| S2[Route to Primary<br/>write connection]
    S1 --> T[Execute with 5s timeout]
    S2 --> T
    T -->|transient error| T1[Retry backoff<br/>100/200/400ms]
    T1 --> T
    T -->|timeout| T2([504 Gateway Timeout])
    T -->|success| U[EXPLAIN ANALYZE<br/>index recommendations]

    %% Observability - Decryption & Masking
    U --> V[Decrypt columns<br/>AES-256-GCM]
    V --> W[Apply RBAC masking<br/>per-role PII redaction]

    %% Performance - Caching
    W --> X[Write to cache<br/>tagged by table<br/>cleanup stale tags]

    %% Observability - Audit & Metrics
    X --> Y[Write to audit log<br/>detailed query record]
    Y --> Z[Update metrics counters<br/>latency, cache hits, anomalies]

    %% Observability - Alerting
    Z --> AA{Slow query<br/>gt 200ms?}
    AA -->|yes| AA1[Fire webhook alert<br/>include analysis]
    AA1 --> AB{Rate spike<br/>anomaly?<br/>3x baseline}
    AA -->|no| AB
    AB -->|yes| AB1[Call explain-anomaly<br/>LLM explanation]
    AB1 --> AC[[Return Response<br/>+ Analysis + Recommendations]]
    AB -->|no| AC

```
