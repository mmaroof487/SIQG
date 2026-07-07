# Argus API Reference

All API requests must be directed to `/api/v1`. The API requires standard HTTP methods and returns JSON responses.

---

## Authentication

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/login` | Authenticate with username/password to receive a JWT. |
| `POST` | `/auth/register` | Register a new user account. |
| `POST` | `/auth/refresh` | Refresh an expiring JWT (includes a 5-minute grace period). |

---

## Connections

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/connections` | List all registered external database connections. |
| `POST` | `/connections` | Register a new external PostgreSQL database. |
| `DELETE`| `/connections/{id}` | Remove a database connection. |
| `POST` | `/connections/{id}/test`| Test connectivity and credentials. |

---

## Queries

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/query/execute` | Execute a SQL query against a connection. Runs through all 6 security layers. |
| `POST` | `/query/dry-run` | Preview the query pipeline (cost, cache status) without executing. |
| `GET` | `/query/budget` | View your remaining daily query budget. |
| `GET` | `/query/history` | View paginated query history for the current user. |

---

## Schema & Intelligence

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/connections/{id}/schema`| Retrieve full schema metadata (tables, columns, types, FKs). |
| `POST`| `/connections/{id}/scan` | Trigger a background PII scan to find sensitive columns. |
| `POST`| `/ai/nl-to-sql` | Translate natural language to SQL based on schema context. |
| `POST`| `/ai/explain` | Get a plain-English explanation of a SQL query. |
| `POST`| `/ai/insights` | Get AI-generated data insights from query results. |
| `POST`| `/ai/schema-chat` | Ask natural language questions about the database structure. |

---

## Encryption

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/connections/{id}/encryption` | Configure a column for envelope encryption. |
| `POST` | `/encryption/rotate` | Trigger Key Rotation (Generates new DEKs and starts migration). |
| `GET` | `/connections/{id}/migration-status` | Check the background re-encryption status. |

---

## Admin
*(Requires `admin` role)*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/admin/audit` | View the global asynchronous audit trail. |
| `GET` | `/admin/slow-queries` | View queries that exceeded the 200ms threshold. |
| `POST` | `/admin/ip-rules` | Add an IP address to the allow/block list. |
| `GET` | `/admin/ip-rules` | List all IP rules. |
| `POST` | `/admin/whitelist` | Whitelist specific queries to bypass AI filters. |
| `GET` | `/admin/compliance-report`| Export security and encryption compliance data (JSON/CSV). |

---

## Observability & Health

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/metrics/live` | Real-time Prometheus metrics, latency, and cache hit ratios. |
| `GET` | `/metrics/heatmap` | Most frequently accessed tables across the system. |
| `GET` | `/health` | Lightweight HTTP 200 OK for load balancers. |
| `GET` | `/status` | Deep health check (Verifies PG Primary, Replica, Redis, and Groq). |
| `GET` | `/version` | Returns the current Gateway version and build hash. |
