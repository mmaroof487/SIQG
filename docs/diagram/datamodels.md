# Data Models — Persistent Storage (Phase 1-6)

## Overview

Core PostgreSQL data models for user management, API keys, rules, audit trails, and SLA tracking.

**Scope:** These models are unchanged across all 6 phases.

**Phase 6 Notes:**

- No new database tables added in Phase 6
- AI features (NL→SQL, Explainer) are stateless endpoints
- All trace data flows through existing `audit_logs` table

---

```mermaid
erDiagram
    USERS {
        uuid id PK
        string username
        string email
        string hashed_password
        enum role
        bool is_active
        datetime created_at
    }

    API_KEYS {
        uuid id PK
        uuid user_id FK
        string key_hash
        string label
        bool is_active
        datetime grace_until
        datetime created_at
    }

    IP_RULES {
        uuid id PK
        string ip_address
        string rule_type
        uuid created_by FK
        datetime created_at
    }

    AUDIT_LOGS {
        uuid id PK
        string trace_id
        uuid user_id FK
        string role
        string query_fingerprint
        string query_type
        float latency_ms
        string status
        bool cached
        bool slow
        bool anomaly_flag
        text error_message
        json execution_plan
        datetime created_at
    }

    SLOW_QUERIES {
        uuid id PK
        string trace_id
        uuid user_id FK
        string query_fingerprint
        float latency_ms
        string scan_type
        int rows_scanned
        int rows_returned
        text recommended_index
        json execution_plan
        datetime created_at
    }

    SLA_SNAPSHOTS {
        uuid id PK
        datetime hour
        float uptime_percent
        float p50_latency_ms
        float p95_latency_ms
        float p99_latency_ms
        int total_requests
        int failed_requests
        float cache_hit_ratio
        datetime created_at
    }

    USERS ||--o{ API_KEYS : "has"
    USERS ||--o{ AUDIT_LOGS : "generates"
    USERS ||--o{ SLOW_QUERIES : "causes"
```
