# Request Pipeline

This document walks through the entire lifecycle of a request flowing through the Argus Gateway. The system is designed as a series of 6 middleware layers, ensuring that requests are fully validated, authorized, and tracked before they ever reach the database.

## Example Request Lifecycle

The following demonstrates a complete query request passing through every system layer.

```mermaid
sequenceDiagram
    participant User
    participant React as React Frontend
    participant Fast as FastAPI
    participant Auth as Auth Layer
    participant Sec as Security (L1)
    participant Perf as Performance (L2)
    participant Exec as Execution (L3)
    participant AI as AI Layer
    participant Cache as Redis Cache
    participant DB as PostgreSQL
    participant Audit as Observability (L5)
    
    User->>React: Write NL Query
    React->>Fast: POST /ai/nl-to-sql
    
    %% AI Generation Flow
    Fast->>Auth: Validate JWT
    Auth->>AI: Rate Limit (20/min) & Topic Guard
    AI->>React: Return SQL string
    
    React->>Fast: POST /query/execute
    
    %% Standard Request Flow
    Fast->>Auth: Validate JWT & Extract Role
    Auth->>Sec: IP Filter & Honeypot Check
    Sec->>Sec: SQL Injection Check
    Sec->>Perf: Rate Limit Check (e.g. 60/min)
    Perf->>Perf: RBAC Time/Scope Checks
    
    %% Performance & Execution
    Perf->>Cache: Generate Fingerprint
    Cache-->>Perf: Miss
    Perf->>Exec: Pre-flight EXPLAIN (Cost Check)
    Exec->>DB: Check Budget Limit
    Exec->>Exec: Check Circuit Breaker State
    
    %% DB Access
    Exec->>DB: Execute Query (with 10s timeout)
    DB-->>Exec: Return Rows
    
    %% Post-Processing
    Exec->>Exec: Decrypt Columns (AES-GCM)
    Exec->>Exec: Apply RBAC Masking (e.g., hash PII)
    Exec->>Cache: Write result to cache (60s TTL)
    
    %% Observability
    Exec->>Audit: Async Write to Audit Log
    Audit->>Audit: Update Live Metrics
    
    Exec-->>React: Return JSON Response
    React-->>User: Display Results
```

### Detailed Layer Breakdown

#### 1. React Frontend
- The user initiates an action, such as executing a query or chatting with the schema.
- The React application attaches the user's JWT and an `X-Timestamp` / `X-Signature` HMAC for payload verification.

#### 2. Auth Layer
- **JWT Validation**: Ensures the token is valid, hasn't expired, and the user is `is_active`.
- **Trace ID**: A unique `uuid` is assigned to the request for distributed tracing across logs.

#### 3. Security Layer (L1)
- **Rate Limiting**: Enforces strict role-based buckets (e.g., Admin: 500/min, Readonly: 60/min).
- **RBAC**: Ensures the user has permissions for the target tables.
- **SQL Validation**: Blocks `DROP`, `TRUNCATE`, and queries targeting sensitive columns like `hashed_password` directly.
- **Honeypot**: If decoy tables are accessed, the IP is instantly banned.

#### 4. Performance Layer (L2)
- **Fingerprinting**: Whitespace is normalized and a SHA-256 hash of the query is generated.
- **Cache Lookup**: Looks up the fingerprint in Redis.
- **Budgeting**: Runs `EXPLAIN` to estimate query cost before it executes.

#### 5. Execution Layer (L3)
- **Circuit Breaker**: Skips execution if the DB is marked as `open` due to repeated failures.
- **Query Execution**: Routes `SELECT` to replicas and `INSERT`/`UPDATE` to primary databases.
- **Decryption**: Envelope decryption is applied to securely decrypt any masked column values using AES-256-GCM.

#### 6. Observability Layer (L5)
- **Audit Logging**: Asynchronously logs the trace ID, user ID, execution time, and query fingerprint.
- **Metrics**: Updates Prometheus counters and Redis heatmaps.
