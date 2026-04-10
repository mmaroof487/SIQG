# <img src="../../frontend-ts/public/argus-logo.png" width="35" alt="Argus Sentinel Logo" />rgus System Architecture — Complete (Tiers 1-6, All 32 Steps)

## Overview

Argus complete 6-layer pipeline with all middleware, security hardening, polish features, and AI integration. Covers all 32 integration steps across Tiers 1-6.

**Tiers:**

- **Tier 1** (Steps 1-5): Security Fixes - Sensitive fields centralization, RBAC masking, pipeline order
- **Tier 2** (Steps 6-10): AI Reliability - NL→SQL quality, explanations, fallbacks, dry-run
- **Tier 3** (Steps 11-15): Frontend Build - React app, dashboards, visualizations
- **Tier 4** (Steps 16-19): Proof & Credibility - CI/CD, load testing, documentation
- **Tier 5** (Steps 20-24): Backend Extensions - Cache cleanup, slow query advisor, per-role rate limits, API scoping, whitelisting
- **Tier 6** (Steps 25-32): Polish - Time-based RBAC, query diff, dry-run UI, DDL copy, admin dashboard, HMAC signing, compliance reports, anomaly explanations

---

```mermaid
graph TB
    subgraph CLIENT["Client Layer (Steps 11-15, 19, 26-28)"]
        UI["React Frontend\n✅ NL Panel, Results, Metrics, Health\n✅ Query Diff Viewer, Dry-Run Panel\n✅ Index Suggestions, Admin Dashboard"]
        SDK["Python SDK + HMAC\n✅ Auto-sign with X-Timestamp\n✅ X-Signature headers"]
        CLI["CLI Tool\n✅ demo_cli.sh walkthrough"]
    end

    subgraph GATEWAY["Argus Gateway (FastAPI)"]
        subgraph SEC_TIER1["🔴 Tier 1: Security Fixes (1-5)"]
            TRACE["Step 1-5:\nTrace ID + Auth\n✅ SENSITIVE_FIELDS const\n✅ Block hashed_password\n✅ Pipeline: decrypt→mask"]
        end

        subgraph SEC_TIER5["🟧 Tier 5: Backend Extensions (20-24)"]
            CACHE_CLEAN["Step 20: Cache Cleanup\n✅ SSCAN stale tags\n✅ Auto-cleanup on 1000 keys"]
            SLOW_ADVISOR["Step 21: Slow Query Advisor\n✅ Merged recommendations\n✅ Index DDL suggestions"]
            ROLE_RATES["Step 22: Per-Role Rate Limits\n✅ admin: 500/min\n✅ readonly: 60/min\n✅ guest: 10/min"]
            API_SCOPE["Step 23: API Key Scoping\n✅ allowed_tables\n✅ allowed_query_types"]
            WHITELIST["Step 24: Query Whitelist\n✅ Fingerprint approval\n✅ Whitelist mode toggle"]
        end

        subgraph SEC_TIER6["🟩 Tier 6: Polish (25-32)"]
            TIME_RBAC["Step 25: Time-Based RBAC\n✅ allowed_hours\n✅ allowed_weekdays\n✅ pytz timezone support"]
            DIFF_UI["Step 26: Query Diff Viewer\n✅ Side-by-side SQL\n✅ Change highlighting"]
            DRY_RUN_UI["Step 27: Dry-Run UI\n✅ Pipeline checklist\n✅ Cost estimate preview"]
            DDL_COPY["Step 28: Index DDL Copy\n✅ One-click copy button\n✅ DBA-friendly format"]
            ADMIN_DASH["Step 29: Admin Dashboard\n✅ 7 management tabs\n✅ Audit, slow queries\n✅ Rules, users, whitelist"]
            HMAC["Step 30: HMAC Signing\n✅ validate_hmac_signature\n✅ Replay attack prevention"]
            COMPLIANCE["Step 31: Compliance Export\n✅ JSON/CSV/PDF\n✅ SOC2/HIPAA ready"]
            ANOMALY["Step 32: AI Anomaly Explain\n✅ explain-anomaly endpoint\n✅ Severity auto-detection"]
        end

        subgraph EXEC["Execution Layer (Tiers 2-6)"]
            VAL["Step 2: Injection Detector\n(13+ patterns)"]
            SENSITIVE["Step 2: Sensitive Columns\n(hashed_password block)"]
            RBAC["Step 3-4: RBAC + Masking\n✅ Column-level permissions\n✅ PII redaction"]
            RATE["Step. 22: Rate Limiter\n(per-role tiers + anomaly)"]
            TIME_CHECK["Step 25: Time-Based Check\n(hours/weekdays/timezone)"]
            SCOPE_CHECK["Step 23: API Key Scope\n(table/query whitelisting)"]
            CACHE_GET["Cache Check + Cleanup\n(Redis GET + SSCAN)"]
            COST_EST["Step 9, 27: Cost Estimator\n(EXPLAIN for budget)"]
            DRY_RUN["Step 9, 27: Dry-Run Mode\n(show would-execute)"]
            CB["Circuit Breaker\n(3 states + metrics)"]
            EXEC_ROUTE["Route & Execute\n(R/W split + timeout)"]
            EXPLAIN_POST["Step 21: EXPLAIN ANALYZE\n(slow query detection)"]
            DECRYPT["Decrypt + Decrypt\nColumns (AES-256-GCM)"]
            MASK_FINAL["Step 3-4: RBAC Masking\n(email→u***@***.com)"]
        end

        subgraph OBS["Observability Layer (Tiers 4-6)"]
            AUDIT_LOG["Audit Log\n(query, user, time)"]
            METRICS["Metrics Counters\n(latency, cache, RPM)"]
            WEBHOOK["Webhooks\n(Slack/Discord alerts)"]
            HEAT["Heat Map\n(table access frequency)"]
            CACHE_WRITE["Cache Setup + Cleanup\n(Redis SET + SSCAN)"]
        end

        subgraph AI["AI Layer (Tiers 2, 6)"]
            NL["Step 6: NL→SQL\n✅ Pattern guardrails\n✅ LIMIT accuracy"]
            EXPLAIN_Q["Step 7: Query Explain\n✅ Plain English\n✅ Mock generation"]
            GROQ["Step 8: Groq LLM\n(Primary provider)"]
            MOCK["Fallback Mock LLM\n✅ Pattern-based\n✅ Zero-failure fallback"]
            ANOMALY_AI["Step 32: Anomaly Explainer\n✅ Rate spike analysis\n✅ Severity determination"]
        end

        subgraph ADMIN_LAYER["Admin APIs (Step 29-31)"]
            AUDIT_EXPORT["GET /audit\n(Step 29 Tab 1)"]
            SLOW_EXPORT["GET /slow-queries\n(Step 29 Tab 2)"]
            BUDGET_EXPORT["GET /budget\n(Step 29 Tab 3)"]
            IP_MGMT["POST /ip-rules\n(Step 29 Tab 4)"]
            USER_MGMT["GET /users\n(Step 29 Tab 5)"]
            WHITELIST_API["POST /whitelist\n(Step 29 Tab 6)"]
            COMPLIANCE_API["GET /compliance-report\n(Step 31)"]
        end
    end

    subgraph INFRA["Infrastructure"]
        PG_PRIMARY["PostgreSQL Primary\n(writes)"]
        PG_REPLICA["PostgreSQL Replica\n(read-only)"]
        REDIS["Redis\n✅ Cache (Step 20 cleanup)\n✅ Rate limits (Step 22-25)\n✅ Circuit breaker state\n✅ Metrics"]
    end

    subgraph EXTERNAL["External Services"]
        GROQ_API["Groq API\n(Llama 3.1 8B)"]
        DISCORD["Discord/Slack\nWebhooks"]
    end

    CLIENT -->|REST API| GATEWAY

    TRACE -->|Auth| SENSITIVE
    SENSITIVE -->|Block| VAL
    VAL -->|Check| SCOPE_CHECK
    SCOPE_CHECK -->|Check| TIME_CHECK
    TIME_CHECK -->|Check| RATE
    RATE -->|Check| RBAC
    RBAC -->|Fingerprint| CACHE_GET
    CACHE_GET -->|miss| COST_EST
    CACHE_GET -->|hit| MASK_FINAL
    COST_EST -->|Budget| DRY_RUN
    DRY_RUN -->|Execute| CB
    CB -->|Route| EXEC_ROUTE
    EXEC_ROUTE -->|SELECT| PG_REPLICA
    EXEC_ROUTE -->|INSERT/UPDATE| PG_PRIMARY
    EXEC_ROUTE -->|Execute| EXPLAIN_POST
    EXPLAIN_POST -->|Decrypt| DECRYPT
    DECRYPT -->|Mask| MASK_FINAL
    MASK_FINAL -->|Cache + Audit| CACHE_WRITE
    CACHE_WRITE -->|Metrics| METRICS
    METRICS -->|Alert if slow| WEBHOOK
    WEBHOOK -->|Trigger anomaly| ANOMALY_AI
    ANOMALY_AI -->|Explain| GROQ

    NL -->|Pattern match| GROQ
    GROQ -->|Fallback| MOCK
    EXPLAIN_Q -->|Pattern| MOCK
    MOCK -->|Zero-failure| NL

    GROQ -->|Call API| GROQ_API
    WEBHOOK -->|Send alert| DISCORD

    ADMIN_DASH -->|Query data| AUDIT_EXPORT
    ADMIN_DASH -->|Query data| SLOW_EXPORT
    ADMIN_DASH -->|Query data| BUDGET_EXPORT
    ADMIN_DASH -->|Manage| IP_MGMT
    ADMIN_DASH -->|Manage| USER_MGMT
    ADMIN_DASH -->|Manage| WHITELIST_API
    COMPLIANCE_API -->|Generate| COMPLIANCE

    CACHE_GET -.->|GET/SET| REDIS
    CACHE_WRITE -.->|SET + SSCAN| REDIS
    RATE -.->|Counter| REDIS
    TIME_CHECK -.->|Timestamp compare| REDIS
    CB -.->|State| REDIS
    METRICS -.->|INCR| REDIS
    HMAC -.->|Sign request| SDK
```

---

## Component Mapping to Steps

| Step  | Component                       | Details                                                                                                |
| ----- | ------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 1-5   | Security fixes, pipeline order  | Centralized SENSITIVE_FIELDS, RBAC masking, decrypt→mask order                                         |
| 6-10  | AI reliability, NL→SQL, explain | Pattern matching, Groq fallback, mock LLM, dry-run                                                     |
| 11-15 | React frontend                  | Dashboard, metrics, health, results table, NL panel                                                    |
| 16-19 | CI/CD, testing, demo            | GitHub Actions, load tests, SDK CLI, README metrics                                                    |
| 20-24 | Backend extensions              | Cache cleanup (SSCAN), slow query advisor, per-role limits, API scoping, whitelisting                  |
| 25-32 | Polish features                 | Time-based RBAC, diff viewer, dry-run UI, DDL copy, admin dashboard, HMAC, compliance, anomaly explain |

---

## Data Flow Example: Complete Query Journey (All Tiers)

```
User enters English question:
"Show top 5 users created last week"
            ↓
[Tier 2, Step 6] NL→SQL (Groq/Mock)
"SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '7 days' LIMIT 5"
            ↓
[Tier 1, Step 2] Injection detection ✅ Safe
            ↓
[Tier 1, Step 2] Sensitive column check ✅ No hashed_password
            ↓
[Tier 1, Step 4] RBAC check ✅ Readonly role can access users
            ↓
[Tier 5, Step 22] Rate limit check (readonly = 60/min) ✅ Within limit
            ↓
[Tier 6, Step 25] Time-based check (readonly 9-5 EST) ✅ During work hours
            ↓
[Tier 5, Step 23] API key scope check ✅ users table allowed
            ↓
[Tier 2, Step 9 / Tier 6, Step 27] Dry-run mode? ← User can preview here
            ↓
[Tier 2, Step 9] Cost estimation (EXPLAIN) = 42.5 units ✅ Budget available
            ↓
[Tier 5, Step 20] Cache check (fingerprint) ✅ Hit! Return instantly (2.1ms)
            ↓
[Tier 1, Step 4] RBAC masking (email→u***@***.com) ✅ PII masked
            ↓
[Tier 5, Step 20] Cache cleanup (if >1000 tags) ← Auto SSCAN
            ↓
[Tier 4] Audit log entry ← What query, who, when
            ↓
[Tier 4] Metrics update ← latency, cache hit, cost
            ↓
[Tier 6, Step 26] Show query diff (← Original vs Argus version)
            ↓
[Tier 6, Step 31] Compliance record ← PII masked, success logged
            ↓
Return: 5 rows, 2.1ms, cached ✅ 8.8× faster than first run!
```

---

## All 32 Steps at a Glance

✅ All 32 steps complete and integrated into production gateway:

- Tier 1-5: Core security, performance, intelligence
- Tier 6: Enterprise polish, compliance, observability
