# Observability

Argus implements a comprehensive observability layer to track system health, user behavior, and performance bottlenecks without impacting query execution speed.

## Core Mechanisms

### 1. Tracing
Every incoming request is assigned a unique UUID `trace_id` by the Authentication layer. This ID is passed through every middleware layer, included in the final API response, and attached to all asynchronous audit logs, allowing for end-to-end debugging of a single request.

### 2. Metrics & Counters
Real-time metrics are maintained in Redis and exposed via the `/api/v1/metrics/live` endpoint.
- **Latency**: End-to-end request latency is tracked, allowing for P95/P99 calculations.
- **Cache Hits vs Misses**: `argus:metrics:cache_hit` and `argus:metrics:cache_miss`.
- **Error Rates**: HTTP 4xx and 5xx errors are counted.
- **RPM**: Requests Per Minute.

### 3. Heatmaps
Argus analyzes executed SQL and identifies the target tables. It increments a Redis Sorted Set (`argus:heatmap`). The `/api/v1/metrics/heatmap` endpoint exposes the most frequently accessed tables, enabling DBAs to proactively optimize indexes.

### 4. Audit Logging
Every query executed (or attempted) is tracked in the `audit_logs` PostgreSQL table.
Because writing to a database adds latency, Argus uses an `asyncio.create_task` fire-and-forget mechanism to flush the audit log payload to the database *after* the HTTP response has been sent to the user.

- **Tracked Data**: `trace_id`, `user_id`, `query_fingerprint`, `execution_time_ms`, `was_cached`, `error_message` (if any).

### 5. Health Endpoints
- `GET /health`: A lightweight, unauthenticated endpoint that returns `200 OK` for load balancer pinging.
- `GET /api/v1/status`: An authenticated, deep-health endpoint that checks the active status of PostgreSQL, Redis, Groq AI, and the Circuit Breaker.
