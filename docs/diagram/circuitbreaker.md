# Circuit Breaker — Resilience Pattern (Tier 3, Step 11)

## Overview

3-state state machine that prevents cascading database failures by fast-failing requests when the database becomes unavailable.

**Scope:** Implemented in Tier 3 (Frontend Build), Layer 3 (Execution).

**Integration:**

- Activated in the Execution Layer (after performance checks, before DB calls)
- Part of Step 11 (React frontend integration) in the complete request pipeline
- See [systemarchitecture.md](systemarchitecture.md) Tier 3 for context

---

```mermaid
stateDiagram-v2
    [*] --> CLOSED

    CLOSED --> CLOSED : Query succeeds\nfailure_count = 0

    CLOSED --> OPEN : 5 consecutive\nDB failures\nStore opened_at in Redis

    OPEN --> OPEN : Request arrives\nbefore cooldown\nReturn 503 instantly

    OPEN --> HALF_OPEN : 30s cooldown elapsed\nAllow 1 probe request

    HALF_OPEN --> CLOSED : Probe succeeds\nReset failure count\nResume traffic

    HALF_OPEN --> OPEN : Probe fails\nReset cooldown timer\nFire webhook alert

    note right of CLOSED
        All requests pass through
        Failure counter tracked in Redis
        Reset on any success
    end note

    note right of OPEN
        Fast fail — no DB calls
        503 returned in microseconds
        Prevents cascade failure
    end note

    note right of HALF_OPEN
        Exactly 1 request allowed
        Acts as health probe
        Binary outcome only
    end note
```
