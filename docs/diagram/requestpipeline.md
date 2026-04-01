# Request Pipeline — Standard Query Flow (Phase 1-5)

## Overview
Complete flow of a standard query request through all security, performance, execution, and observability layers.

**Scope:** This diagram shows the core pipeline for `/api/v1/query` endpoint.

**Phase 6 Addition:** AI endpoints (`/api/v1/ai/nl-to-sql`, `/api/v1/ai/explain`) have separate pipelines — see [systemarchitecture.md](systemarchitecture.md) for AI layer components.

---

```mermaid
flowchart TD
    A([Incoming Request]) --> B[Generate trace_id]
    B --> C{JWT or API Key?}
    C -->|invalid| C1([401 Unauthorized])
    C -->|valid| D{IP blocked?}
    D -->|yes| D1([403 Forbidden])
    D -->|no| E{Brute forced?}
    E -->|yes| E1([423 Locked])
    E -->|no| F{Rate limited?}
    F -->|yes| F1([429 Too Many Requests])
    F -->|no| G{Injection detected?}
    G -->|yes| G1([400 Injection Blocked])
    G -->|no| H{Query type allowed?}
    H -->|no| H1([400 Type Not Allowed])
    H -->|yes| I{Honeypot table?}
    I -->|yes| I1([403 + IP Banned + Alert])
    I -->|no| J{RBAC pass?}
    J -->|no| J1([403 Table/Column Denied])
    J -->|yes| K[Fingerprint + Hash]
    K --> L{Cache hit?}
    L -->|yes| L1[Return cached result]
    L -->|no| M[EXPLAIN cost estimate]
    M --> N{Budget exceeded?}
    N -->|yes| N1([429 Budget Exhausted])
    N -->|no| O[Inject LIMIT if missing]
    O --> P{Circuit open?}
    P -->|yes| P1([503 DB Unavailable])
    P -->|no| Q[Encrypt columns AES-256-GCM]
    Q --> R{SELECT or write?}
    R -->|SELECT| S1[Replica connection]
    R -->|INSERT/UPDATE| S2[Primary connection]
    S1 --> T[Execute + 5s timeout]
    S2 --> T
    T -->|transient error| T1[Retry backoff 100/200/400ms]
    T1 --> T
    T -->|timeout| T2([504 Gateway Timeout])
    T -->|success| U[EXPLAIN ANALYZE]
    U --> V[Decrypt + PII mask by role]
    V --> W[Write to Redis cache]
    W --> X[Write to audit log]
    X --> Y[Update metrics counters]
    Y --> Z{Slow query?}
    Z -->|yes| Z1[Fire webhook alert]
    Z -->|no| AA([Return response + analysis])
```