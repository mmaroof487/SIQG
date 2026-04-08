## User Guide: Complete Step-by-Step Walkthrough

This section shows exactly what you'll see when using Argus, the Secure Intelligent Query Gateway. Everything is explained as if you're a business user (not a developer) who wants to query a database safely and efficiently.

---

## Overview: The 6 Layers of Argus

Argus protects your database with 6 security and performance layers:

| Layer                        | Purpose                | What It Does                                                      |
| ---------------------------- | ---------------------- | ----------------------------------------------------------------- |
| **Layer 1: Security**        | Block harmful queries  | SQL injection, DROP/DELETE detection, rate limiting, RBAC masking |
| **Layer 2: Performance**     | Make queries fast      | Intelligent caching, query fingerprinting, cost estimation        |
| **Layer 3: Execution**       | Run queries safely     | Circuit breaker (auto-fail on errors), timeout protection         |
| **Layer 4: Observability**   | Track everything       | Audit logs, metrics, heatmaps, webhooks, slow query alerts        |
| **Layer 5: Hardening**       | Extra security         | Encryption, IP filtering, brute force detection, honeypot tables  |
| **Layer 6: AI Intelligence** | Generate & explain SQL | Natural language → SQL, query explanations, GROQ + fallback       |

All 6 layers work together seamlessly. You just need to ask questions!

---

## 🚀 Phase 0: Start the System

**What to do:**
Open a terminal in the project folder and run:

```bash
docker compose up --build
```

**What you'll see:**

```
[+] Running 4/4
 ✔ Container siqg-postgres-1         Healthy
 ✔ Container siqg-redis-1            Healthy
 ✔ Container siqg-postgres_replica-1 Started
 ✔ Container siqg-gateway-1          Started
```

**What's happening:**
The system starts 4 Docker containers that work together:

- **PostgreSQL (Primary)** = Database that stores everything (port 5432)
- **PostgreSQL (Replica)** = Read-only copy for SELECT queries (port 5433)
- **Redis** = Ultra-fast memory cache (port 6379)
- **Argus Gateway** = The security + AI layer (port 8000)

The entire system is now ready for queries. Keep this terminal open!

---

## 👤 Phase 1: Authentication & Account Management

**What to do:**
Create a user account in a new terminal:

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
	"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YjNkZjQ0ZC1hOTk3LTQwZDMtYmRmYS1iZGI5YTVjODYyYTMiLCJyb2xlIjoicmVhZG9ubHkiLCJleHAiOjE3NzUxNDExMjMsImlhdCI6MTc3NTEzNzUyM30.2zbPMQf4jhJcctPqaaPPJtF0GxWu98DhMMTIYWtQpPE",
	"token_type": "bearer",
	"role": "readonly"
}
```

**Key Information:**

- **access_token**: Your digital "key" to access the database (long string)
- **role**: "readonly" = You can only read data, not modify it
- **Expires**: After 24 hours (for security)

**Save your token immediately:**

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YjNkZjQ0ZC1hOTk3LTQwZDMtYmRmYS1iZGI5YTVjODYyYTMiLCJyb2xlIjoicmVhZG9ubHkiLCJleHAiOjE3NzUxNDExMjMsImlhdCI6MTc3NTEzNzUyM30.2zbPMQf4jhJcctPqaaPPJtF0GxWu98DhMMTIYWtQpPE"
```

**Login (if token expired):**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!"
  }'
```

---

## 🔐 Phase 2: Security Layer (SQL Injection Protection)

**What to do:**
Try a SQL injection attack and watch it get blocked:

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
Layer 1 (Security) blocked your query. The system detects 13+ injection patterns:

- `OR 1=1` → Always true (classic injection)
- `UNION SELECT` → Data theft
- `--` or `/*` → Comment tricks
- `DROP`, `DELETE`, `TRUNCATE` → Destructive commands
- `xp_cmdshell`, `COPY`, `EXECUTE` → System commands

**Also blocked (defensive guardrail): Direct access to sensitive fields**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, username, hashed_password FROM users"}'
```

**What you'll see:**

```json
{
	"detail": {
		"blocked": true,
		"block_reasons": ["Query references sensitive field: hashed_password"],
		"suggested_fix": "Remove 'hashed_password' from query"
	}
}
```

HTTP Status: **403 Forbidden** 🔒

**Understanding the 3-Layer Protection:**

The system protects sensitive fields (passwords, tokens, API keys) at THREE different levels:

**Layer 1: Query-Level Blocking (Your Primary Guard)**

- Blocks explicit references to sensitive fields: `hashed_password`, `password`, `token`, `api_key`, `secret`, `internal_notes`
- Examples of blocked queries:
  - ❌ `SELECT id, hashed_password FROM users` → 403 Forbidden
  - ❌ `SELECT * FROM users WHERE password = 'abc'` → 403 Forbidden (uses password in WHERE)
- **This is the main line of defense** — prevents direct sensitive field access

**Layer 2: RBAC Masking (Safety Net)**

- Even if you use `SELECT *` (wildcard), your role restricts which columns you can see
- Admin role: Sees everything
- Readonly role: Sensitive columns removed from results
- Guest role: Even more columns hidden

**Layer 3: Blind DLP Regex (Last Mile)**

- Even if something slipped through, all string values are scanned for patterns
- Emails masked: `alice@company.com` → `a****@company.com`
- SSNs masked: `123-45-6789` → `****-**-6789`

**Safe queries you can run:**

✅ `SELECT id, username, email FROM users` — No sensitive fields
✅ `SELECT * FROM users` — Allowed (sensitive columns stripped by RBAC)
✅ `SELECT id, username FROM users WHERE is_active = true` — Specific columns, safe

**Try a safe query instead:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, username, email FROM users WHERE is_active = true LIMIT 10"}'
```

**What you'll see:**

```json
{
	"trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
	"query_type": "SELECT",
	"rows": [
		{ "id": 1, "username": "alice", "email": "alice@company.com" },
		{ "id": 2, "username": "bob", "email": "bob@company.com" }
	],
	"rows_count": 2,
	"latency_ms": 12.5,
	"cached": false,
	"slow": false
}
```

✅ **Query succeeded!** Your data is safe. Three-layer protection ensures sensitive fields cannot leak out.

---

## ⚡ Phase 3: Performance Layer (Caching & Query Optimization)

**First query (cache miss):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, username FROM users WHERE is_active = true LIMIT 10"}'
```

**What you'll see (first time):**

```json
{
	"trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
	"query_type": "SELECT",
	"rows": [
		{ "id": 1, "username": "alice" },
		{ "id": 2, "username": "bob" },
		{ "id": 3, "username": "charlie" }
	],
	"rows_count": 3,
	"latency_ms": 18.5,
	"cached": false,
	"slow": false,
	"cost": 5.25,
	"analysis": {
		"scan_type": "Sequential Scan",
		"complexity": {
			"score": 25,
			"level": "low"
		}
	}
}
```

**Metrics explained:**

- **latency_ms**: 18.5ms = How long the query took (slow, hitting actual DB)
- **cached**: false = Result came from database
- **cost**: 5.25 = Estimated cost of this query

**Now run the same query again (cache hit):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, username FROM users WHERE is_active = true LIMIT 10"}'
```

**What you'll see (second time):**

```json
{
	"trace_id": "a1b2c3d5-e5f6-7890-abcd-ef1234567891",
	"rows_count": 3,
	"latency_ms": 2.1,
	"cached": true,
	"cost": 5.25
}
```

**Speed improvement:** 18.5 ÷ 2.1 = **8.8× faster!** 🚀

**What's happening:**

1. First query: 18.5ms (reached database, computed fingerprint, stored in Redis)
2. Second query: 2.1ms (hit Redis cache, returned instantly)
3. Savings: 16.4ms per repeated query

The system fingerprints queries (ignores whitespace, formatting), stores results in Redis, and serves cached results instantly next time.

---

## 📊 Phase 4: Budget & Rate Limiting

**Check your remaining budget:**

```bash
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"daily_budget": 50000,
	"current_usage": 1250.5,
	"remaining": 48749.5,
	"resets_at": "2026-04-03T00:00:00Z"
}
```

**What each field means:**

| Field             | Meaning                                    |
| ----------------- | ------------------------------------------ |
| **daily_budget**  | Total daily limit = 50,000 cost units      |
| **current_usage** | How much you've used today = 1,250.5 units |
| **remaining**     | How much is left = 48,749.5 units          |
| **resets_at**     | When budget resets = midnight UTC          |

**Budget enforcement:**

- Each query has an estimated cost
- If a query exceeds your budget, it's blocked with 400 error
- Budget resets automatically at midnight UTC
- Admins bypass budget limits (for testing)

**Test rate limiting (60 requests/minute per user):**

```bash
for i in {1..65}; do
  curl -s http://localhost:8000/api/v1/status \
    -H "Authorization: Bearer $TOKEN" > /dev/null &
done
wait
```

**What happens:**

- Requests 1-60: Succeed (200 OK)
- Requests 61-65: Fail (429 Too Many Requests)

**When you get blocked:**

```json
{
	"detail": "Rate limit exceeded: 61/60 requests per minute"
}
```

HTTP Status: **429 Too Many Requests** ⛔

**Why rate limiting matters:**

- Protects database from being overwhelmed
- Ensures fair access for all users
- Prevents accidental DOS attacks
- Resets every 60 seconds (sliding window)

---

## 📈 Phase 5: Observability & Monitoring

**Check system health:**

```bash
curl -X GET http://localhost:8000/api/v1/status \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"status": "ok",
	"redis": "healthy"
}
```

**View live metrics:**

```bash
curl -X GET http://localhost:8000/api/v1/metrics/live \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"requests_total": 142.0,
	"cache_hits": 78.0,
	"cache_misses": 64.0,
	"cache_hit_ratio": 54.9,
	"avg_latency_ms": 4.87,
	"p50_latency_ms": 2.1,
	"p95_latency_ms": 11.2,
	"p99_latency_ms": 42.5,
	"slow_queries": 2,
	"rate_limit_hits": 8,
	"errors": 0
}
```

**Metrics explained:**

| Metric              | Meaning                                      |
| ------------------- | -------------------------------------------- |
| **cache_hit_ratio** | 54.9% of queries served from cache (faster!) |
| **avg_latency_ms**  | Average query time: 4.87 milliseconds        |
| **p50_latency_ms**  | 50% complete in 2.1ms (median)               |
| **p95_latency_ms**  | 95% of queries complete in 11.2ms or less    |
| **p99_latency_ms**  | 99% of queries complete in 42.5ms            |
| **slow_queries**    | 2 queries exceeded 200ms threshold           |
| **rate_limit_hits** | 8 times users hit rate limit                 |
| **errors**          | 0 failed queries (100% success rate)         |

**Performance interpretation:**

- ✅ Good: cache_hit_ratio > 40% (means caching is working)
- ✅ Good: p95_latency < 50ms (fast for most users)
- ⚠️ Warning: slow_queries > 0 (some queries need indexing)
- ⚠️ Warning: errors > 0 (something is wrong, investigate)

---

## 🤖 Phase 6: AI Intelligence to SQL

This is the most powerful feature: **Ask questions in plain English, get SQL instantly.**

### The AI Architecture: Groq + Fallback

Argus uses a **resilient two-tier AI system:**

```
Your Question
    ↓
[Tier 1: Groq (Primary)]
    ↓
  Falls Back to:
    ↓
[Tier 2: Mock (Fallback)]
    ↓
Generated SQL
```

**Why this design:**

- **Groq**: Faster, more capable LLM (Llama 3.1 8B)
- **Mock**: Instant, pattern-based, never fails
- **Fallback**: Any Groq error (timeout, API limit, network) → Switch to Mock
- **Result**: Zero failures, seamless experience

**Example flows:**

| Scenario       | What Happens                                             |
| -------------- | -------------------------------------------------------- |
| Groq works     | ✅ Fast, sophisticated SQL from real AI                  |
| Groq times out | ⚠️ Auto-fallback, uses pattern matching, works instantly |
| Groq API error | ⚠️ Auto-fallback, uses pattern matching, works instantly |
| Network down   | ⚠️ Auto-fallback, uses pattern matching, works instantly |

**You see the same result either way**—no retry needed, no error messages, just SQL.

---

### AI Feature 1: Generate SQL from Natural Language

**Question 1: Show all users**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me all users"}'
```

**Result:**

```json
{
	"original_question": "Show me all users",
	"generated_sql": "SELECT * FROM users LIMIT 1000",
	"result": {
		"rows": [
			{ "id": 1, "username": "alice", "email": "alice@company.com", "is_active": true },
			{ "id": 2, "username": "bob", "email": "bob@company.com", "is_active": true }
		],
		"rows_count": 22,
		"latency_ms": 15.2,
		"cached": false
	},
	"status": "success"
}
```

**What happens behind the scenes:**

1. Groq LLM generates: `SELECT * FROM users`
2. Argus checks for LIMIT clause (missing!)
3. Argus auto-injects LIMIT 1000: `SELECT * FROM users LIMIT 1000`
4. Executes against replica database
5. Applies RBAC masking: removes `hashed_password`, `internal_notes` for non-admin users
6. Returns safe results

---

**Question 2: Users created in the last 7 days**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show username and email for users created in the last 7 days"}'
```

**Generated SQL:**

```sql
SELECT username, email, created_at
FROM users
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 1000
```

**Result:**

```json
{
	"rows": [
		{ "username": "alice", "email": "alice@company.com", "created_at": "2026-04-02T10:15:00Z" },
		{ "username": "bob", "email": "bob@company.com", "created_at": "2026-04-02T09:22:00Z" }
	],
	"rows_count": 22,
	"latency_ms": 18.4,
	"cached": false
}
```

---

**Question 3: How many active users count by role?**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Count active users by role"}'
```

**Generated SQL:**

```sql
SELECT role, COUNT(*) AS user_count
FROM users
WHERE is_active = true
GROUP BY role
ORDER BY user_count DESC
LIMIT 1000
```

---

**Question 4: Top 5 users (IMPORTANT: Pattern-matched for accuracy)**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Top 5 users created in the last 7 days"}'
```

**Generated SQL:**

```sql
SELECT id, username, email, created_at
FROM users
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 5
```

**Why LIMIT 5 (not 1000)?**

Argus detects "top 5" pattern BEFORE calling Groq and pre-enforces the correct LIMIT. This ensures:

- ✅ Semantic accuracy (questions asking for "top N" get exactly N results)
- ✅ Zero LLM ambiguity (prevents "top 5" being interpreted as 1000)
- ✅ Instant answer (pattern matching returns result <10ms, no LLM call)

**Pattern Matching Guardrails (Pre-LLM):**

- "top 5" → `LIMIT 5`
- "how many" → `COUNT(*)`
- "average salary" → `AVG(salary)`
- "unique countries" → `SELECT DISTINCT country`

These are matched instantly without calling Groq, improving speed and reliability.

---

### AI Feature 2: Explain SQL in Plain English

**Explain a simple query:**

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT id, username FROM users WHERE is_active = true LIMIT 10"}'
```

**Result:**

```json
{
	"query": "SELECT id, username FROM users WHERE is_active = true LIMIT 10",
	"explanation": "This query retrieves the ID and username of users who are currently active, limited to the first 10 results."
}
```

---

**Explain a complex query:**

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT role, COUNT(*) AS user_count FROM users WHERE is_active = true GROUP BY role ORDER BY user_count DESC"}'
```

**Result:**

```json
{
	"query": "SELECT role, COUNT(*) AS user_count FROM users WHERE is_active = true GROUP BY role ORDER BY user_count DESC",
	"explanation": "This query counts active users grouped by their role and sorts the results in descending order based on the count. The role with the most active users appears first."
}
```

**Explanation details:**

- ✅ Identifies the main action: "counts active users"
- ✅ Explains the grouping: "grouped by their role"
- ✅ Explains the sorting: "sorts in descending order based on count"
- ✅ Plain English: "The role with the most users appears first"

---

### AI Configuration

**Current AI Provider:** Groq (free, fast, no rate limits inside the fallback)

Switch AI providers by editing `.env`:

```bash
AI_PROVIDER=groq           # Primary: Llama 3.1 8B (fast, reliable)
# AI_PROVIDER=mock         # Fallback: Pattern-based (instant, no API calls)
# AI_PROVIDER=openai       # Alternative: GPT-4o-mini (requires key)
# AI_PROVIDER=gemini       # Alternative: Gemini 2.0 Flash (requires key)
```

**Automatic Fallback:**
If Groq fails for ANY reason:

- Timeout (>10 seconds)
- API error (500, 429, etc.)
- Invalid response
- Network down

The system instantly switches to Mock and succeeds.

**You never see an AI error**—either Groq works or Mock takes over.

---

## 📋 Complete Workflow: From English to Results

Here's the complete flow:

```
┌──────────────────────────────────────┐
│ You: "Show top 5 users from last week"│
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Pattern Matching: "top 5" detected   │
│ Force: LIMIT 5 (not LLM default)     │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ AI (Groq): Convert to SQL            │
│ "SELECT * FROM users WHERE          │
│  created_at >= NOW() - INTERVAL...   │
│  ORDER BY created_at DESC LIMIT 5"   │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Security (Layer 1): Check for SQL    │
│ injection, dangerous commands        │
│ ✅ Query is safe                     │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Performance (Layer 2): Check cache   │
│ ❌ Cache miss (first time)           │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Execute: Run against PostgreSQL      │
│ Found 5 rows in 12ms                 │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Cache (Layer 2): Store in Redis      │
│ Next identical query: 8× faster!     │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Observability (Layer 5): Log audit   │
│ track metrics, track user behavior   │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ You: Get results with metadata       │
│ 5 users, 12ms, cached: false         │
└──────────────────────────────────────┘
```

---

## 🎯 Common Use Cases

### Use Case 1: Report Generation

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show active users by role with their signup dates"}'
```

AI generates the query, execute it, get your report instantly.

### Use Case 2: Quick Data Checks

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"How many users signed up in the last 24 hours?"}'
```

No SQL knowledge needed—just ask!

### Use Case 3: Query Auditing

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"<paste-legacy-query-here>"}'
```

Understand what an old query does before running it.

### Use Case 4: Learning SQL

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Find users with gmail accounts"}'
```

See the generated SQL and learn syntax over time!

---

## ⚡ Pro Tips

**Tip 1: Be specific in your questions**

- ❌ "Show users" → Returns all columns
- ✅ "Show username and email for users" → Returns 2 columns

**Tip 2: Request limited results**

- ❌ "Get all orders" → Returns thousands, slow
- ✅ "Show top 10 orders by date" → Returns 10, fast

**Tip 3: Use the explain endpoint to learn**

- Copy SQL generated by AI
- Run other queries and explain them
- Build SQL knowledge over time

**Tip 4: Check budget before heavy queries**

- Always call `/api/v1/query/budget` first
- Check how much budget remains
- Dry-run expensive queries before executing

**Tip 5: Leverage caching for performance**

- Run query once → hits database (10-20ms)
- Run same query again → instant from cache (2-5ms)
- 5-10× speed improvement for common queries

**Tip 6: Understand fallback AI**

- Groq usually responds in <1s
- If Groq times out or fails → Mock takes over
- You get SQL either way, no retries needed
- Fallback is instant and reliable

---

## 🔒 Security Summary

Argus protects your data at **every layer**:

| Layer                | Protection                                                 |
| -------------------- | ---------------------------------------------------------- |
| **1. Query Level**   | Pattern matching blocks SQL injection + dangerous commands |
| **2. Field Level**   | `hashed_password`, `token`, `api_key` explicitly blocked   |
| **3. Role Level**    | RBAC masking strips columns based on user role             |
| **4. Access Level**  | Rate limiting (60 req/min), brute force detection          |
| **5. Network Level** | IP filtering, HTTPS required in production                 |
| **6. Audit Trail**   | Every query logged with user, timestamp, duration          |

**Your passwords are never exposed:**

- Blocked from direct SQL query
- Masked from results by RBAC
- Never visible to AI
- Encrypted in storage

---

---

### 🚀 Phase 0: Start the System

**What to do:**
Open a terminal in the project folder and run:

```bash
docker compose up --build
```

**What you'll see:**

```
[+] Running 4/4
 ✔ Container siqg-postgres-1         Healthy
 ✔ Container siqg-redis-1            Healthy
 ✔ Container siqg-postgres_replica-1 Started
 ✔ Container siqg-gateway-1          Started
```

**What's happening:**
The system starts 4 Docker containers that work together:

- **PostgreSQL (Primary)** = Database that stores everything (port 5432)
- **PostgreSQL (Replica)** = Read-only copy for SELECT queries (port 5433)
- **Redis** = Ultra-fast memory cache (port 6379)
- **Argus Gateway** = The security + AI layer (port 8000)

The entire system is now ready for queries. Keep this terminal open!

---

### 👤 Phase 1: Authentication & Account Management

**What to do:**
Create a user account in a new terminal:

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
	"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YjNkZjQ0ZC1hOTk3LTQwZDMtYmRmYS1iZGI5YTVjODYyYTMiLCJyb2xlIjoicmVhZG9ubHkiLCJleHAiOjE3NzUxNDExMjMsImlhdCI6MTc3NTEzNzUyM30.2zbPMQf4jhJcctPqaaPPJtF0GxWu98DhMMTIYWtQpPE",
	"token_type": "bearer",
	"role": "readonly"
}
```

**Key Information:**

- **access_token**: Your digital "key" to access the database (long string)
- **role**: "readonly" = You can only read data, not modify it
- **Expires**: After 24 hours (for security)

**Save your token immediately:**

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YjNkZjQ0ZC1hOTk3LTQwZDMtYmRmYS1iZGI5YTVjODYyYTMiLCJyb2xlIjoicmVhZG9ubHkiLCJleHAiOjE3NzUxNDExMjMsImlhdCI6MTc3NTEzNzUyM30.2zbPMQf4jhJcctPqaaPPJtF0GxWu98DhMMTIYWtQpPE"
```

**Login (if expired):**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "SecurePass123!"
  }'
```

---

### 🔐 Phase 2: Security Layer (SQL Injection Protection)

**What to do:**
Try a SQL injection attack and watch it get blocked:

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
Layer 1 (Security) blocked your query. The system detects 13+ injection patterns:

- `OR 1=1` → Always true (classic injection)
- `UNION SELECT` → Data theft
- `--` or `/*` → Comment tricks
- `DROP`, `DELETE`, `TRUNCATE` → Destructive commands
- `xp_cmdshell`, `COPY`, `EXECUTE` → System commands

**Try a safe query instead:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT id, username, email FROM users WHERE is_active = true LIMIT 10"}'
```

---

### ⚡ Phase 3: Performance Layer (Caching & Query Optimization)

**First query (cache miss):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE is_active = true LIMIT 10"}'
```

**What you'll see (first time):**

```json
{
	"trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
	"query_type": "SELECT",
	"rows_count": 10,
	"latency_ms": 15.5,
	"cached": false,
	"slow": false,
	"cost": 5.25,
	"analysis": {
		"scan_type": "Sequential Scan",
		"complexity": {
			"score": 25,
			"level": "low"
		}
	}
}
```

**Run the same query again (cache hit):**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE is_active = true LIMIT 10"}'
```

**What you'll see (second time):**

```json
{
	"latency_ms": 2.1,
	"cached": true,
	"cost": 5.25
}
```

**Speed improvement:** 15.5 ÷ 2.1 = **7.4× faster!** 🚀

The system fingerprints queries (ignores whitespace), stores results in Redis, and serves cached results instantly next time.

---

### 📊 Phase 4: Execution Layer (Budget & Rate Limiting)

**Check your budget:**

```bash
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"daily_budget": 50000,
	"current_usage": 1250.5,
	"remaining": 48749.5,
	"resets_at": "2026-04-03T00:00:00Z"
}
```

**What each field means:**

- **daily_budget**: Your total daily limit = 50,000 cost units
- **current_usage**: How much you've used today = 1,250.5 cost units
- **remaining**: How much is left = 48,749.5 cost units
- **resets_at**: When budget resets = midnight UTC

**Budget enforcement:**

- Each query has an estimated cost
- If a query exceeds your budget, it's blocked with 400 error
- Budget resets automatically at midnight UTC
- Admins bypass budget limits (for testing)

**Check rate limits (60 requests/minute per user):**

```bash
for i in {1..65}; do
  curl -s http://localhost:8000/api/v1/status \
    -H "Authorization: Bearer $TOKEN" &
done
wait
```

**On request 61+, you'll see:**

```json
{
	"detail": "Rate limit exceeded: 61/60 requests per minute"
}
```

HTTP Status: **429 Too Many Requests** ⛔

---

### 📈 Phase 5: Observability Layer (Metrics & Audit Logs)

**Check system health:**

```bash
curl -X GET http://localhost:8000/api/v1/status \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"status": "ok",
	"redis": "healthy"
}
```

**View live metrics:**

```bash
curl -X GET http://localhost:8000/api/v1/metrics/live \
  -H "Authorization: Bearer $TOKEN"
```

**What you'll see:**

```json
{
	"requests_total": 42.0,
	"cache_hits": 8.0,
	"cache_misses": 34.0,
	"cache_hit_ratio": 19.0,
	"avg_latency_ms": 5.23,
	"p50_latency_ms": 2.5,
	"p95_latency_ms": 10.8,
	"p99_latency_ms": 45.2,
	"slow_queries": 0,
	"rate_limit_hits": 0,
	"errors": 0
}
```

**Metrics explained:**
| Metric | Meaning |
|--------|---------|
| **cache_hit_ratio** | 19% of queries served from Redis (faster!) |
| **avg_latency_ms** | Average speed: 5.23 milliseconds |
| **p95_latency_ms** | 95% of queries finish in 10.8ms or less |
| **slow_queries** | 0 queries exceeded 200ms threshold |
| **rate_limit_hits** | How many times users hit rate limit |
| **errors** | Failed queries count |

---

### 🤖 Phase 6: AI Intelligence Layer (Natural Language → SQL)

This is the most powerful feature: **Ask questions in plain English, get SQL instantly.**

#### AI Feature 1: Generate SQL from Natural Language

**Question 1: Show all users**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me all users"}'
```

**Result:**

```json
{
  "original_question": "Show me all users",
  "generated_sql": "SELECT * FROM users LIMIT 1000;",
  "result": {
    "rows": [...],
    "rows_count": 22,
    "latency_ms": 22.09,
    "cached": false,
    "cost": 10.5
  },
  "status": "success"
}
```

---

**Question 2: Show users created in last 7 days (specific columns)**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show username and email for users created in the last 7 days"}'
```

**Result:**

```json
{
	"original_question": "Show username and email for users created in the last 7 days",
	"generated_sql": "SELECT username, email, created_at FROM users WHERE created_at >= NOW() - INTERVAL '7 days' ORDER BY created_at DESC LIMIT 1000;",
	"result": {
		"rows": [
			{ "username": "verifyuser", "email": "v***@test.com", "created_at": "2026-04-02T06:15:48.812326" },
			{ "username": "testuser", "email": "t***@example.com", "created_at": "2026-04-02T09:22:14.497474" }
		],
		"rows_count": 22,
		"latency_ms": 19.44,
		"cached": false,
		"cost": 10.88
	},
	"status": "success"
}
```

---

**Question 3: Count active users**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"How many active users are there?"}'
```

**Expected SQL:**

```sql
SELECT COUNT(*) FROM users WHERE is_active = true;
```

---

**Question 4: Top 5 users (best practice for reducing output)**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show top 5 users created in the last 7 days"}'
```

**Expected SQL:**

```sql
SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '7 days' LIMIT 5;
```

---

**Question 5: Users by role (aggregation)**

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Group users by role and count them"}'
```

**Expected SQL:**

```sql
SELECT role, COUNT(*) as user_count FROM users GROUP BY role;
```

---

#### AI Feature 2: Explain SQL in Plain English

**Explain a simple query:**

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users WHERE is_active = true"}'
```

**Result:**

```json
{
	"query": "SELECT * FROM users WHERE is_active = true",
	"explanation": "This query retrieves all users from the users table who are currently active (is_active = true). It returns all columns for each active user."
}
```

---

**Explain a complex query:**

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT role, COUNT(*) as user_count, AVG(id) FROM users GROUP BY role ORDER BY user_count DESC"}'
```

**Result:**

```json
{
	"query": "SELECT role, COUNT(*) as user_count, AVG(id) FROM users GROUP BY role ORDER BY user_count DESC",
	"explanation": "This query groups users by their role and shows statistics for each group. For each role, it counts how many users have that role and calculates the average ID. The results are sorted by user count in descending order (most users first)."
}
```

---

#### AI Configuration

**Current AI Provider:** Groq (Llama 3.1 8B Instant)

The system supports multiple AI providers. Switch them by editing `.env`:

```bash
AI_PROVIDER=groq           # Fast, free tier, no rate limits
# AI_PROVIDER=mock         # Heuristic patterns (great for demos)
# AI_PROVIDER=openai       # GPT-4o-mini (requires API key)
# AI_PROVIDER=gemini       # Google Gemini 2.0 Flash (requires API key)
```

**Rate Limit Resilience:**
If Groq hits rate limit (429), Argus automatically retries with exponential backoff:

- Attempt 1: Wait 1 second
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds

You see the final result transparently, no need to retry manually.

---

## 📋 Complete Workflow: From English to Results

Here's the complete flow from question → answer:

```
┌─────────────────────────────────────┐
│ You: "Show users created last 7 days"│
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ AI (Groq): Convert to SQL           │
│ "SELECT ... FROM users WHERE        │
│  created_at >= NOW() - INTERVAL...  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Security: Check for injections      │
│ ✅ Query is safe                    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Cache: Check Redis for results      │
│ ❌ Cache miss (first time)          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Database: Execute against PostgreSQL│
│ Found 22 rows in 19ms               │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Cache: Store results in Redis       │
│ Next time: 7.5× faster!             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ You: Get results with metadata      │
│ 22 users, 19ms, cost: 10.88         │
└─────────────────────────────────────┘
```

---

## 🎯 Common Use Cases

### Use Case 1: Report Generation

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me active users by role with signup dates"}'
```

AI generates the query, execute it, get your report.

### Use Case 2: Quick Data Checks

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"How many users signed up today?"}'
```

No SQL knowledge needed—just ask!

### Use Case 3: Query Auditing

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"<paste-old-query-here>"}'
```

Understand what an old query does before running it.

### Use Case 4: Learning SQL

```bash
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Find users with gmail accounts"}'
```

See the generated SQL and learn the SQL syntax!

---

## ⚡ Pro Tips

**Tip 1: Be specific in your questions**

- ❌ "Show users" → Returns all columns
- ✅ "Show username and email for users" → Returns 2 columns

**Tip 2: Request limited results**

- ❌ "Get all orders" → Returns thousands
- ✅ "Show top 10 orders by date" → Returns 10

**Tip 3: Use the explain endpoint to learn**

- Copy SQL generated by AI
- Run other queries and explain them
- Build SQL knowledge over time

**Tip 4: Check budget before heavy queries**

- Always call `/api/v1/query/budget` first
- Dry-run expensive queries before executing
- Watch the cost estimate

**Tip 5: Leverage caching**

- Run query once → hits database
- Run same query again → instant from cache
- 5-10× speed improvement for common queries

---

## 🚀 Advanced Features (Tier 6: Steps 25-32)

Argus includes **8 advanced enterprise features** for production deployments:

- **Step 25:** Time-based access control (hourly/weekday restrictions with timezone support)
- **Step 26:** Query diff viewer (side-by-side comparison of SQL queries)
- **Step 27:** Dry-run UI panel (pipeline checklist + cost estimate before execution)
- **Step 28:** Index DDL copy (one-click suggestions for missing indexes)
- **Step 29:** Admin dashboard (7 tabs: audit log, slow queries, budget, IP rules, users, whitelist, compliance)
- **Step 30:** HMAC request signing (timing-attack safe authentication headers)
- **Step 31:** Compliance report export (JSON/CSV format with audit summary, metrics, security stats)
- **Step 32:** AI anomaly explanation (severity auto-detection, LLM-based explanations for anomalies)

**→ See [TIER6_FEATURES_GUIDE.md](TIER6_FEATURES_GUIDE.md) for complete documentation and examples.**
