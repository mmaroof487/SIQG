# Argus Cache Architecture

This document describes the caching layer of the Argus Gateway, which is designed to provide high-speed responses for read-heavy workloads while maintaining strict data consistency through smart, table-tagged invalidation.

## Architecture Overview

Argus utilizes **Redis** as the high-speed caching backend. The cache sits in the query execution pipeline (inside `gateway/routers/v1/query.py`) and intercepts incoming SQL `SELECT` queries before they hit the underlying database. 

The architecture is built around three core principles:
1. **Perfect Isolation**: Cache keys are scoped to prevent data leakage between different databases, user roles, or query parameters.
2. **Surgical Invalidation**: We do not flush the entire cache on writes. Instead, we only invalidate the exact queries affected by a database mutation.
3. **Scalability & Safety**: We use memory-efficient Redis commands (`SSCAN`) and asynchronous background garbage collection to prevent memory bloat.

---

## 1. Cache Keys & Fingerprinting

The cache key strictly isolates data. It is structured as follows:

```text
argus:cache:<conn_scope>:<query_fingerprint>:<role>
```

- **`conn_scope`**: Defines the database connection. For internal Argus metadata queries, this is `default`. For external connected databases, this is the unique `connection_id`. This prevents cross-tenant data collisions (e.g., `db1.users` vs `db2.users`).
- **`query_fingerprint`**: A SHA-256 hash of the incoming query. 
  - *Crucial Detail:* We use a specialized `fingerprint_cache_key` function (in `fingerprinter.py`) that normalizes whitespace and capitalization, but **keeps literal string and number parameters intact**. This ensures that `SELECT * FROM users WHERE id=1` and `SELECT * FROM users WHERE id=2` generate completely distinct cache keys.
- **`role`**: The RBAC role (e.g., `admin`, `readonly`, `guest`) of the user executing the query. This guarantees that a guest user cannot access cached data originally fetched by an admin user.

---

## 2. Table-Tagged Smart Invalidation

The biggest challenge in database caching is invalidation. Argus solves this using **Table Tags**.

### Writing to the Cache (Tagging)
When a `SELECT` query results in a cache miss, the gateway executes the query against the database and caches the result. During this step:
1. The gateway parses the SQL query to extract which tables it touched (e.g., `SELECT * FROM users JOIN roles` touches `users` and `roles`).
2. The gateway adds the newly generated `cache_key` into a **Redis Set** specific to each table and connection scope.

Example:
```redis
SADD argus:cache_tags:<conn_scope>:users <cache_key>
SADD argus:cache_tags:<conn_scope>:roles <cache_key>
```

### Invalidating the Cache (Sweeping)
When a user executes a mutating query (`INSERT`, `UPDATE`, `DELETE`), Argus:
1. Extracts the tables affected by the mutation.
2. Triggers the `invalidate_table_cache` function for those specific tables.
3. Looks up the tag set for the affected table (e.g., `argus:cache_tags:<conn_scope>:users`).
4. Iterates through the set using Redis's `SSCAN` command.
5. Deletes every `cache_key` it finds, effectively purging all cached `SELECT` queries that relied on the mutated table.

*Why `SSCAN`?* Using `SMEMBERS` on a tag set with 100,000 cached queries would load all 100,000 keys into memory at once, potentially crashing the gateway or blocking Redis. `SSCAN` cursors through the set in small, highly efficient batches (O(1) per batch).

---

## 3. Background Garbage Collection

Cache keys naturally expire on their own via a TTL (Time-To-Live). However, when a cache key naturally expires, its reference inside the tag set (`argus:cache_tags:...`) remains. Over time, these "ghost" tags can cause the tag sets to grow indefinitely.

To prevent memory leaks:
- During the `write_cache` phase, Argus checks the size of the table's tag set (an O(1) operation using `SCARD`).
- If the tag set exceeds 1,000 items, the gateway spawns a fire-and-forget asynchronous background task called `cleanup_stale_tags`.
- This background worker cursors through the tag set, verifies if the underlying `cache_key` still exists, and removes any dead references. 

---

## 4. Telemetry and Audit Tracing

Whenever an invalidation sweep occurs, Argus records detailed telemetry. This is invaluable for observing system behavior and debugging caching anomalies.

The `invalidate_table_cache` function tracks the number of keys deleted and the millisecond duration of the sweep, outputting a structured JSON trace:

```json
{
  "event": "CACHE_INVALIDATION",
  "tables": ["users"],
  "keys_deleted": 143,
  "duration_ms": 12,
  "conn_scope": "athletiq-prod-db-1"
}
```

---

## 5. Fallback TTLs & The External Write Weakness

**The TTL Safety Net:**
While Argus's invalidation logic is highly accurate, every cached item still receives a TTL (e.g., 5, 10, or 15 minutes). This is not used for primary cache rotation, but rather as a safety mechanism. If an invalidation event ever fails (e.g., network partition to Redis), the stale data will naturally self-heal.

**The Middleware Limitation:**
Because Argus acts as a gateway middleware, its cache invalidation depends on writes passing *through* Argus. 

If a system administrator connects to the underlying PostgreSQL database directly via `pgAdmin` or `psql` and runs an `UPDATE users`, Argus will never see the mutation and will not trigger cache invalidation. In these scenarios, the cache will remain stale until the aforementioned TTL expires. 
