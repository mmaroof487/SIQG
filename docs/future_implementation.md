# 📦 Argus / ARGUS – FEATURE BACKLOG

> A structured backlog of features for future development, prioritized for maximum impact, feasibility, and interview value.

---

# 🧠 PRIORITY LEGEND

- 🔴 P0 → Must Have (Core Differentiators)
- 🟠 P1 → High Value (Strong Impact)
- 🟡 P2 → Nice to Have (If Time Allows)
- ⚪ P3 → Stretch / Future Scope
- ✅ → **Already Implemented**

---

# 🔴 P0 — CORE DIFFERENTIATORS

## 1. Explainable Query Blocks

> **STATUS: 🚧 Partially Implemented**
> Validator returns structured reason (injection type, blocked query type) but no suggested fix yet.

### Description

Provide detailed, human-readable explanations for why a query was blocked.

### Example Output

```
Blocked Query: SELECT * FROM users

Reasons:
- Missing LIMIT → potential full table scan
- Accessing restricted column: ssn

Suggested Fix:
- Add LIMIT 1000
- Remove restricted columns
```

### Remaining Work

- Map each validation rule → human-readable explanation + suggested fix
- Return structured response with `block_reasons[]` and `suggested_fix`

---

## 2. Time-Based Access Control

> **STATUS: 🚧 Not Yet Implemented**

### Description

Restrict query execution based on time windows.

### Example

```
Intern role: Only 9am-5pm weekdays
Admin role: Unrestricted
```

### Implementation

- Add `allowed_hours` to RBAC role config
- Check `datetime.utcnow()` in RBAC middleware

---

## 3. Compliance Report Generator

> **STATUS: 🚧 Partially Implemented**
> Audit log data exists and CSV export works. Needs structured compliance report format.

### Description

Generate reports summarizing system activity.

### Report Includes

- Total queries
- Blocked queries
- PII access count
- Masked columns
- User activity

### Output Formats

- JSON
- PDF (optional)

### Remaining Work

- Aggregate audit data into compliance report schema
- Add `/admin/compliance-report` endpoint
- Optional: scheduled report generation

---

# 🟠 P1 — HIGH VALUE FEATURES

## ✅ 4. Query Complexity Scoring — IMPLEMENTED

> **File:** `middleware/performance/complexity.py`
> Scores queries based on JOIN count, subquery count, SELECT *, missing WHERE clause.
> Integrated into query pipeline response as `analysis.complexity`.

---

## ✅ 5. Automatic LIMIT Injection — IMPLEMENTED

> **File:** `middleware/performance/auto_limit.py`
> Injects `LIMIT {default}` on SELECT queries without bounds when cost exceeds threshold.
> Configurable via `AUTO_LIMIT_DEFAULT` env var.

---

## ✅ 6. Cache + Smart Invalidation — IMPLEMENTED

> **File:** `middleware/performance/cache.py`
> Redis-backed caching with fingerprint-based keys, role-aware TTL, and SSCAN-based table-tagged invalidation on writes.

---

## ✅ 7. Audit Logging System — IMPLEMENTED

> **File:** `middleware/observability/audit.py`
> Fire-and-forget async audit logs with trace_id, user_id, role, fingerprint, latency, status, cached, slow, anomaly_flag.
> Admin endpoints: paginated view, CSV streaming export.

---

## ✅ 8. Slow Query Detection — IMPLEMENTED

> **Files:** `middleware/execution/analyzer.py`, `models/audit_log.py`
> Queries exceeding `SLOW_QUERY_THRESHOLD_MS` are logged to `slow_queries` table with EXPLAIN ANALYZE data and index recommendations.
> Admin endpoint: `GET /api/v1/admin/slow-queries`.

---

# 🟡 P2 — NICE TO HAVE

## 9. Policy Simulation Mode

> **STATUS: 🚧 Not Yet Implemented**

### Description

Test rules before applying (dry-run for policy changes).

### Example

```
New Rule: block SELECT *
Impact: 43 queries affected
```

---

## ✅ 10. Column-Level Encryption — IMPLEMENTED

> **File:** `middleware/security/encryption.py`
> AES-256-GCM encryption with per-request random 12-byte nonces.
> Encrypts configured columns on INSERT/UPDATE, decrypts on SELECT.
> Configured via `ENCRYPT_COLUMNS` env var.

---

## ✅ 11. Circuit Breaker — IMPLEMENTED

> **File:** `middleware/execution/circuit_breaker.py`
> Redis-backed 3-state machine (CLOSED → OPEN → HALF_OPEN).
> Configurable failure threshold, cooldown period, and single-probe logic.

---

## ✅ 12. Retry with Exponential Backoff — IMPLEMENTED

> **File:** `middleware/execution/executor.py`
> 3-retry pattern with 100ms → 200ms → 400ms backoff on transient DB failures.
> Combined with circuit breaker checks.

---

# ⚪ P3 — FUTURE / STRETCH

## 13. AI Query Explainer

> **STATUS: 🚧 Not Yet Implemented** — Requires OpenAI API integration.

### Description

Explain SQL queries in plain English using LLM.

---

## 14. NL → SQL

> **STATUS: 🚧 Not Yet Implemented** — Phase 5 feature.

### Description

Convert natural language questions to SQL queries.

---

## 15. AI Anomaly Explanation

> **STATUS: 🚧 Not Yet Implemented**

### Description

Explain why a query is flagged as anomaly using AI context.

---

## 16. Chat Interface

> **STATUS: 🚧 Not Yet Implemented** — Phase 6 feature.

### Description

Conversational DB querying via chat UI.

---

# 📊 IMPLEMENTATION STATUS SUMMARY

| # | Feature | Status | Phase |
|---|---------|--------|-------|
| 1 | Explainable Query Blocks | 🟡 Partial | P0 |
| 2 | Time-Based Access Control | ❌ Pending | P0 |
| 3 | Compliance Report Generator | 🟡 Partial | P0 |
| 4 | Query Complexity Scoring | ✅ Done | P1 |
| 5 | Automatic LIMIT Injection | ✅ Done | P1 |
| 6 | Cache + Smart Invalidation | ✅ Done | P1 |
| 7 | Audit Logging System | ✅ Done | P1 |
| 8 | Slow Query Detection | ✅ Done | P1 |
| 9 | Policy Simulation Mode | ❌ Pending | P2 |
| 10 | Column-Level Encryption | ✅ Done | P2 |
| 11 | Circuit Breaker | ✅ Done | P2 |
| 12 | Retry with Backoff | ✅ Done | P2 |
| 13 | AI Query Explainer | ❌ Pending | P3 |
| 14 | NL → SQL | ❌ Pending | P3 |
| 15 | AI Anomaly Explanation | ❌ Pending | P3 |
| 16 | Chat Interface | ❌ Pending | P3 |

**Score: 8/16 done, 2/16 partial, 6/16 pending**

---

# 🧠 FINAL NOTES

## Core Philosophy

Build fewer features, but execute them deeply.

## Next Priority Build Order

1. Complete P0 gaps (Explainable Blocks, Time-Based Access)
2. Policy Simulation Mode (P2)
3. Phase 5: AI features (NL→SQL, AI Explainer)
4. Phase 6: Client SDKs + Chat Interface

---

# 🚀 END GOAL

A system that is:

- Secure
- Intelligent
- Performant
- Observable

> Not just feature-rich, but production-like.
