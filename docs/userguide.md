## User Guide: Complete Step-by-Step Walkthrough

This section shows exactly what you'll see when using the gateway. Everything is explained as if you're a business user (not a developer) who wants to query a database safely and efficiently.

### 🚀 Step 1: Start the System

**What to do:**
Open a terminal in the project folder and run:

```bash
docker compose up --build
```

**What you'll see:**

```
[+] Running 5/5
 ✔ Container siqg-postgres-1         Healthy
 ✔ Container siqg-redis-1            Healthy
 ✔ Container siqg-postgres_replica-1 Started
 ✔ Container siqg-gateway-1          Started
```

**What's happening:**
The system is starting 4 services that work together:

- **PostgreSQL (Primary)** = Database that stores everything (port 5432)
- **PostgreSQL (Replica)** = Read-only copy for SELECT queries (port 5433)
- **Redis** = Ultra-fast memory cache (port 6379)
- **Gateway** = The security layer that controls all database access (port 8000)

The entire system is now running and waiting for your queries.

---

### 👤 Step 2: Create Your Account

**What to do:**
Open another terminal and create a user account:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@company.com",
    "password": "SecurePass123!"
  }'
```

**What you'll see:**

```json
{
	"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImlhdCI6MTcxNDcxNDA1MCwiZXhwIjoxNzE0ODAwMjUwfQ.abc123...",
	"token_type": "bearer",
	"role": "readonly"
}
```

**What's happening:**

- You've created an account with username `alice`
- The system issued you a **token** (long string) = your "digital key" to access the database
- Your **role** is "readonly" = you can only read data, not modify it
- The token expires after 24 hours (for security)

**Save your token:** You'll need it for every query going forward. Let's save it:

```bash
export TOKEN="<paste-the-access_token-value-here>"
```

---

### 📊 Step 3: Run Your First Simple Query

**What to do:**
Execute a simple SELECT query:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT 1 AS result"}'
```

**What you'll see:**

```json
{
	"trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
	"query_type": "SELECT",
	"rows": [{ "result": 1 }],
	"rows_count": 1,
	"latency_ms": 10.84,
	"cached": false,
	"slow": false,
	"cost": 0.01,
	"analysis": {
		"scan_type": "Result",
		"execution_time_ms": 0.002,
		"rows_processed": 1,
		"complexity": {
			"score": 0,
			"level": "low",
			"reasons": []
		}
	}
}
```

**What each field means:**

- **trace_id**: Unique ID for this query (for debugging and auditing)
- **query_type**: Type of query you ran (SELECT, INSERT, etc.)
- **rows**: The actual results from your query (you got 1 row with result=1)
- **latency_ms**: How fast was it? **10.84 milliseconds** ✓
- **cached**: false = This was the first time, so DB was hit. Next time will be faster!
- **slow**: false = The query was fast (anything under 200ms is good)
- **cost**: 0.01 = Estimated database cost (used for budget enforcement)
- **analysis**: Detailed info about how the query was executed (scan type, rows processed, complexity score)

---

### ⚡ Step 4: Run the Same Query Again (Watch Caching Work)

**What to do:**
Run the exact same query a second time:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT 1 AS result"}'
```

**What you'll see:**

```json
{
  "trace_id": "x9y8z7w6-v5u4-3210-tsrq-po9876543210",
  "query_type": "SELECT",
  "rows": [
    { "result": 1 }
  ],
  "rows_count": 1,
  "latency_ms": 2.13,
  "cached": true,
  "slow": false,
  "cost": 0.01,
  "analysis": { ... }
}
```

**The key difference:**

- **latency_ms**: NOW **2.13 milliseconds** (was 10.84 before)
- **cached**: true = Result came from Redis memory, NOT the database!

**Speed improvement:** 10.84 ÷ 2.13 = **5× faster! 🚀**

This is caching in action. The system fingerprints your query (ignores whitespace/formatting differences), stores the result in Redis, and serves it instantly next time. No database hit = super fast.

---

### 🔒 Step 5: Try Something That Gets Blocked (Security)

**What to do:**
Try to DROP a table (destructive query):

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "DROP TABLE users"}'
```

**What you'll see:**

```json
{
	"detail": "DROP queries are not allowed"
}
```

HTTP Status: **400 Bad Request** ❌

**What's happening:**
Layer 1 (Security) blocked your query before it even reached the database. The system has a whitelist of allowed query types:

- ✅ SELECT (read data)
- ✅ INSERT (add data)
- ❌ DROP (blocked - destructive)
- ❌ DELETE (blocked - could lose data)
- ❌ TRUNCATE (blocked - deletes everything)

Your readonly role also means you can only run SELECT queries anyway. Double protection!

---

### 🛡️ Step 6: Try a SQL Injection Attack (Watch It Get Blocked)

**What to do:**
Attempt a SQL injection:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE id = 1 OR 1=1"}'
```

**What you'll see:**

```json
{
	"detail": "Potential SQL injection detected: OR 1=1 pattern"
}
```

HTTP Status: **400 Bad Request** ❌

**What's happening:**
The system scans every query for 13+ SQL injection patterns:

- `OR 1=1` → Always true (classic injection)
- `UNION SELECT` → Data exfiltration
- `--` or `/*` → Comments to hide SQL
- And many more sneaky patterns

Even if a developer accidentally includes user input without proper escaping, the gateway catches it. This is defense-in-depth.

---

### 💰 Step 7: Check Your Query Cost and Budget

**What to do:**
Query the current status and metrics:

```bash
curl -X GET http://localhost:8000/api/v1/status \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"status": "ok",
	"redis": "healthy",
	"daily_budget_cost": 50000.0,
	"daily_budget_remaining": 49999.98,
	"daily_budget_percent": 99.99
}
```

**What this means:**

- You have a **daily budget of 50,000 cost units** (configured per user)
- You've **used 0.02 units** (from your queries)
- You have **99.99% budget remaining**
- Expensive queries that would exceed your budget are blocked before they run

---

### 📈 Step 8: View Live Performance Metrics

**What to do:**
Check the live metrics dashboard:

```bash
curl -X GET http://localhost:8000/api/v1/metrics/live \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"requests_total": 7.0,
	"cache_hits": 1.0,
	"cache_misses": 6.0,
	"cache_hit_ratio": 14.3,
	"avg_latency_ms": 5.23,
	"p50_latency_ms": 2.5,
	"p95_latency_ms": 10.8,
	"p99_latency_ms": 45.2,
	"slow_queries": 0,
	"rate_limit_hits": 0,
	"errors": 0
}
```

**What each metric tells you:**
| Metric | Meaning |
|--------|---------|
| **requests_total** | 7 queries ran through the gateway |
| **cache_hit_ratio** | 14.3% of queries were served from cache (reused results) |
| **avg_latency_ms** | Average query response: 5.23ms |
| **p95_latency_ms** | 95% of queries finish in under 10.8ms (only 5% are slower) |
| **slow_queries** | 0 queries exceeded 200ms threshold |
| **rate_limit_hits** | 0 times Rate limiting kicked in (you're within 60 req/min limit) |
| **errors** | 0 failed queries |

This is your real-time performance dashboard. In production, you'd monitor these metrics to spot issues early.

---

### 🤖 Step 9: Use AI to Generate SQL from Plain English

**What to do:**
Ask the AI to convert English to SQL:

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me all users who signed up in the last 7 days"
  }'
```

**What you'll see:**

```json
{
	"original_question": "Show me all users who signed up in the last 7 days",
	"generated_sql": "SELECT id, username, email, created_at FROM users WHERE created_at > NOW() - INTERVAL '7 days' ORDER BY created_at DESC LIMIT 1000",
	"status": "success",
	"message": null
}
```

**What's happening:**

- You asked a question in plain English
- The AI (GPT-4o-mini) converted it to SQL
- You got back correct, executable SQL instantly
- No need to memorize SQL syntax!

If you like the SQL, copy it and use it in the next step.

---

### 🔍 Step 10: Ask the AI to Explain a Complex Query

**What to do:**
Get a plain English explanation of a SQL query:

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT u.id, u.email, COUNT(o.id) AS order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.role = '\''admin'\'' GROUP BY u.id HAVING COUNT(o.id) > 5 LIMIT 100"
  }'
```

**What you'll see:**

```json
{
	"query": "SELECT u.id, u.email, COUNT(o.id) AS order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.role = 'admin' GROUP BY u.id HAVING COUNT(o.id) > 5 LIMIT 100",
	"explanation": "This query finds admin users who have placed more than 5 orders. It joins the users table with orders, counts how many orders each admin has, and returns only those with more than 5 orders. The result shows the admin's ID, email, and total order count, limited to 100 rows."
}
```

**What's happening:**

- Complex SQL is explained in simple English
- Perfect for learning SQL or understanding old queries written by others
- Helps audit queries and understand business logic

---

### 🌍 Step 11: Check System Health (DB + Cache)

**What to do:**
Verify everything is running healthy:

```bash
curl -X GET http://localhost:8000/health
```

**What you'll see:**

```json
{
	"status": "ok",
	"db": "ok",
	"redis": "ok"
}
```

**What this means:**

- ✅ **status**: Overall system is healthy
- ✅ **db**: PostgreSQL database is responding
- ✅ **redis**: Cache is responding

If any service goes down, you'd see:

```json
{
	"status": "degraded",
	"db": "unhealthy",
	"redis": "ok"
}
```

This helps you know when infrastructure issues occur.

---

### 📋 Step 12: Dry-Run Mode (Validate Without Executing)

**What to do:**
Test a query without actually running it (cost estimation only):

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM large_table WHERE name LIKE '\''%smith%'\''",
    "dry_run": true
  }'
```

**What you'll see:**

```json
{
	"trace_id": "dry-run-xxxxx",
	"query_type": "SELECT",
	"rows": [],
	"rows_count": 0,
	"latency_ms": 25.5,
	"cached": false,
	"slow": false,
	"cost": 2500.5,
	"analysis": {
		"scan_type": "Sequential Scan",
		"execution_time_ms": 0.0,
		"rows_processed": 0,
		"complexity": {
			"score": 45,
			"level": "medium",
			"reasons": ["LIKE pattern matching without index"]
		},
		"index_suggestions": ["CREATE INDEX idx_users_name ON large_table (name)"]
	}
}
```

**What's happening:**

- **dry_run: true** = Don't actually execute, just analyze
- **rows**: Empty (no results returned, just analysis)
- **cost**: 2500.5 (estimated cost if you ran it for real)
- **complexity**: Medium (LIKE with wildcard is slow)
- **index_suggestions**: "Create this index to make it 10× faster"

Perfect for testing expensive queries before running them!

---

### ⚠️ Step 13: Rate Limiting in Action

**What to do:**
Send 65 rapid queries (limit is 60 per minute):

```bash
for i in {1..65}; do
  curl -s -X POST http://localhost:8000/api/v1/query/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query":"SELECT 1"}' | jq '.detail' &
done
wait
```

**What you'll see (at request #61+):**

```json
{
	"detail": "Rate limit exceeded: 61/60 requests per minute"
}
```

HTTP Status: **429 Too Many Requests** ⛔

**What's happening:**

- System allows 60 requests per minute per user
- On request 61, you hit the limit
- Requests 61-65 are rejected
- Protects database from being hammered
- Limit resets after 1 minute

This prevents accidental DDOS (like a broken loop querying forever).

---

### 🔐 Step 14: Logout / Token Expiry

**What to do:**
Wait until your token expires OR manually revoke it. Tokens last 24 hours.

After expiry, try to run a query:

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT 1"}'
```

**What you'll see:**

```json
{
	"detail": "Invalid or expired token"
}
```

HTTP Status: **401 Unauthorized** ❌

**What's happening:**

- Token has expired (24 hours passed)
- You need to login again to get a new token
- This is security: old tokens can't be reused

Login again:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!"
  }'
```

Get new token, set it:

```bash
export TOKEN="<new-token-here>"
```

Now you're good for another 24 hours!

---
