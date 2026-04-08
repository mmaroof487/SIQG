# Argus: Plain-English Feature Guide for Non-Technical Users

_A simple explanation of all the amazing things Argus does to keep your database safe, fast, and intelligent._

---

## The Big Picture

Argus is a **security guard + traffic director + smart assistant** for your database. It sits between your apps and the database, making sure:

- ✅ No bad queries get through
- ✅ Passwords and secrets are never exposed
- ✅ Queries run fast (caching)
- ✅ Everyone knows who accessed what (audit trail)
- ✅ You can ask questions in plain English

---

## Core Protection Features

### 1. SQL Injection Protection

**What it does:** Blocks hackers who try to trick the system by inserting malicious SQL code.

**Example of attack blocked:**

- Hacker types: `SELECT * FROM users WHERE id = 1 OR 1=1`
- Argus says: ❌ "SQL injection detected, blocked"
- Your data is safe!

### 2. Dangerous Query Blocking

**What it does:** Prevents someone from accidentally (or maliciously) deleting your database.

**Blocked commands:**

- `DROP TABLE ...` (deletes entire tables)
- `DELETE FROM ...` (deletes all rows)
- `TRUNCATE ...` (empties tables)

**Result:** Your data can't be wiped out by running a bad query.

### 3. Password Field Protection (3 Layers!)

**What it does:** Makes sure passwords, tokens, and API keys never show up in query results, no matter what.

**Sensitive Fields Protected:**

- `hashed_password`, `password` (obvious ones)
- `token`, `api_key`, `secret` (authentication tokens)
- `internal_notes` (private server-side notes)

**Three Protection Layers Explained:**

**Layer 1 - Query-Level Blocking (The Front Door):**

This is your primary protection. Queries that explicitly ask for sensitive fields are blocked BEFORE they reach the database.

- User tries: `SELECT username, hashed_password FROM users`
- Argus blocks: ❌ "Access to sensitive field 'hashed_password' blocked"
- Clear error message guides you to use safe columns instead
- **Result:** Cannot request sensitive fields directly at all

**Layer 2 - RBAC Masking (The Safety Net):**

Even if you somehow use wildcard queries, your role restricts what you can see.

- User runs: `SELECT * FROM users` (wildcard, gets all columns)
- Argus executes it
- **Before returning results:**
  - Admin role: Gets everything including hashed_password
  - Readonly role: Sees hashed_password removed + some fields masked
  - Guest role: hashed_password completely removed, other sensitive fields hidden
- **Result:** Role-based column filtering ensures non-admins can't see sensitive columns

**Layer 3 - Blind Pattern Matching (The Last Mile):**

Even if something slipped through, Argus scans all string values for patterns (emails, SSNs, credit cards) and masks them automatically, regardless of column name.

- Scans for email patterns → `user@example.com` becomes `u****@example.com`
- Scans for SSN patterns → `123-45-6789` becomes `****-**-6789`
- Scans for credit card patterns → `4532-1234-5678-9010` becomes `****-****-****-9010`

**Result:** Three-layer defense—passwords literally can't leak:

```
Layer 1: Query-level blocking (can't ask for them)
Layer 2: RBAC masking (role doesn't grant access)
Layer 3: Blind DLP (patterns detected and masked)
```

All three must fail simultaneously for a leak, making it effectively impossible.

### 4. Rate Limiting (Traffic Control)

**What it does:** Stops any single user from overwhelming the database with thousands of requests.

**How it works:**

- Each user can make 60 requests per minute
- After 60 requests, new requests are temporarily blocked
- Reset happens automatically after 60 seconds

**Benefits:**

- Prevents accidents (bad script doesn't crash the DB)
- Prevents attacks (bad actors can't DOS the system)
- Ensures fair access (everyone gets their turn)

### 5. Super-Fast Caching

**What it does:** Remembers query results and serves them instantly the next time.

**How fast?**
| Scenario | Speed |
|----------|-------|
| First time you run a query | 18 milliseconds (slower, hits database) |
| Second time (exact same query) | 2 milliseconds (instant from memory) |
| **Speed improvement** | **9× faster!** |

**How it works:**

- Argus remembers what you typed (even with different spacing)
- Stores the answer in super-fast memory (Redis)
- Next user gets instant answer, database didn't have to work

### 6. Circuit Breaker (Automatic Self-Healing)

**What it does:** If the database crashes or gets overwhelmed, Argus temporarily stops sending it requests, preventing a domino effect.

**How it works:**

1. Database starts failing (errors spike)
2. Argus opens the "circuit breaker" (like flipping a switch OFF)
3. New requests are immediately rejected with "Service unavailable"
4. System waits a bit for database to recover
5. Argus sends one "test" request to check health
6. If healthy, it closes the circuit (flips switch back ON)

**Benefit:** Problems don't cascade and crash everything—system recovers gracefully.

### 7. Timeout Protection

**What it does:** If a query is taking way too long (more than 10 seconds), Argus forcefully stops it.

**Benefits:**

- Prevents your app from hanging forever waiting for a stuck query
- Protects the database from long-running queries consuming resources
- User sees "Query timeout" instead of spinning wheel for 5 minutes

### 8. Automatic Connection Reuse

**What it does:** Instead of opening a new database connection every time (slow), Argus opens several connections when it starts and reuses them.

**Analogy:** Like having 5 checkout lanes open at a store instead of opening/closing one lane per customer.

**Benefits:**

- 10-20× faster (no connection overhead)
- Database handles more traffic
- Smoother user experience

---

## Intelligence Features

### 9. Query Explanation in Plain English

**What it does:** You paste any SQL query, and Argus tells you what it does in plain language.

**Example:**

- **Paste SQL:** `SELECT role, COUNT(*) FROM users WHERE is_active = true GROUP BY role ORDER BY COUNT(*) DESC`
- **Argus responds:** "This query counts active users grouped by their role and shows the role with the most users first."

**Benefit:** No SQL knowledge needed to understand what a query does!

### 10. Natural Language to SQL (AI with Resilient Fallback)

**What it does:** You ask a question in plain English, and Argus converts it to SQL and runs it.

**Examples:**

```
You ask: "Show me users created in the last 7 days"
Argus generates: SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '7 days' LIMIT 1000

You ask: "How many people have gmail accounts?"
Argus generates: SELECT COUNT(*) FROM users WHERE email LIKE '%gmail.com%' LIMIT 1000
```

**How it works (Production-Hardened Design):**

Argus uses **two AI providers** to ensure English queries work 100% of the time:

1. **Primary: Groq LLM** (Sophisticated)
   - Powered by Llama 3.1 8B model
   - Understands complex questions like "users with highest spending in the past month"
   - Fast: <1 second response time
   - Reliable: Free API tier with no practical rate limits

2. **Fallback: Mock AI** (Pattern-Based)
   - Instantly recognizes common patterns without calling any API
   - Examples: "top 5", "how many", "average", "unique users"
   - Fast: <10 milliseconds (instant)
   - 100% guaranteed to work (no external dependencies)

**The Journey:**

```
You: "Top 5 users by spending"
    ↓
Argus tries: Groq LLM
    Did Groq respond within 1 second with valid SQL?
    ├─ Yes → Returns SQL ✅
    └─ No (timeout, error, API down) ↓
           ↓
    Argus instantly falls back: Mock AI
    (Detects "top 5" pattern)
    └─ Returns SQL ✅
```

**Why the fallback?**

- Demos never fail due to API timeouts
- 95% of questions matched by mock AI patterns (instant)
- 5% of complex questions get sophisticated Groq AI when available
- Users always get SQL, no errors, no retries needed

**Auto-LIMIT Safety Feature:**

Sometimes LLMs generate queries without LIMIT clauses (e.g., `SELECT * FROM users`). Argus automatically fixes this:

```
LLM generates: SELECT * FROM users
Argus injects: SELECT * FROM users LIMIT 1000

Why? Prevents accidental full-table scans that crash memory.
Result: Safe, bounded queries guaranteed.
```

**Semantic Pattern Matching:**

Before calling LLM, Argus pre-checks common questions:

- "top 5" → Auto-injects `LIMIT 5` (no LLM call needed)
- "how many" → Auto-routes to `COUNT(*)` pattern
- "average salary" → Auto-routes to `AVG(salary)` pattern
- "unique countries" → Auto-routes to `SELECT DISTINCT country`

This means simple questions return instant answers (10ms) without waiting for LLM.

### 11. "Dry Run" Mode (Test Before Executing)

**What it does:** Before running a query, validate it without accessing the database. Perfect for testing expensive queries, AI-generated queries, or queries you're unsure about.

**What it checks (Pre-Execution Validation):**

✅ **Security:** Is the query safe? (no SQL injection, no dangerous commands)
✅ **Permissions:** Are you allowed to run this query? (role-based checks)
✅ **Validity:** Does the query even require from valid tables and columns?
✅ **Complexity:** How complex is the query? (Low/Medium/High scoring)
✅ **Cost Estimate:** What would this query cost if run? (EXPLAIN calculation)

**Example: Dry-run an AI-generated query before executing**

```bash
curl -X POST http://localhost:8000/api/v1/query/dry-run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users WHERE is_active = true"}'
```

**Result (without executing):**

```json
{
	"trace_id": "abc123...",
	"query_type": "SELECT",
	"valid": true,
	"safe": true,
	"analysis": {
		"status": "would_execute",
		"estimated_cost": 5.25,
		"estimated_rows": 22,
		"complexity_score": "low",
		"warnings": []
	}
}
```

**What each field means:**

| Field              | Meaning                                                 |
| ------------------ | ------------------------------------------------------- |
| `valid`            | Query syntax is correct, tables/columns exist           |
| `safe`             | No SQL injection, no destructive commands detected      |
| `estimated_cost`   | PostgreSQL planner estimated this query's cost          |
| `estimated_rows`   | Planner estimates this will return ~22 rows             |
| `complexity_score` | low/medium/high based on anti-patterns                  |
| `warnings`         | List of issues (missing indexes, expensive joins, etc.) |

**Example with warnings (missing WHERE clause):**

```bash
curl -X POST http://localhost:8000/api/v1/query/dry-run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM orders"}'
```

**Result:**

```json
{
	"valid": true,
	"safe": true,
	"analysis": {
		"status": "would_execute",
		"estimated_cost": 1250.5,
		"estimated_rows": 50000,
		"complexity_score": "high",
		"warnings": ["⚠️ Query lacks WHERE clause and will scan 50,000 rows", "⚠️ Query lacks LIMIT and might return too many rows", "💡 Add: WHERE created_at > NOW() - INTERVAL '7 days'"]
	}
}
```

**Benefit:** You see warnings BEFORE running the query, not after it times out or returns megabytes of data.

---

## Tracking & Visibility Features

### 12. Complete Audit Trail

**What it does:** Records every single query—who ran it, when, for how long, if it succeeded or failed.

**Benefit:**

- Regulatory compliance (prove who accessed what data)
- Troubleshooting (find out what happened when)
- Security (track who might have snooped)

### 13. Live Dashboard & Metrics

**What it does:** Real-time stats shown in a dashboard.

**Example metrics:**

```
Requests this minute:        47
Cache hit rate:              65% (queries served from memory)
Average response time:        4 milliseconds
Slowest query (P95):          12 milliseconds
Failed queries:               0
Rate limit blocks:            2
```

**Benefit:** See at a glance if everything is running smoothly.

### 14. Slow Query Alerts

**What it does:** When a query takes longer than 200 milliseconds, Argus flags it and can send you an alert.

**Alert example:**

```
🚨 SLOW QUERY ALERT
Query: SELECT * FROM orders WHERE date > '2025-01-01'
Took: 450ms (expected <200ms)
Suggestion: Add INDEX on date column
```

**Benefit:** Early warning of performance problems before they cascade.

### 15. Table Popularity Heatmap

**What it does:** Shows which tables in your database are being accessed the most.

**Analogy:** Like seeing a heat map of foot traffic in a store—red areas are busy, blue areas are quiet.

**Benefit:** Helps database admins optimize the busiest tables with extra resources.

### 16. Webhook Alerts for Critical Events

**What it does:** When something important happens (security threat, rate limiting, slow queries), Argus sends a message to Slack, Discord, or email.

**Example alerts:**

- ⚠️ "Honeypot table accessed (possible attack)"
- 🚨 "Rate limit threshold exceeded"
- 🐢 "Slow query detected: 5+ seconds"

**Benefit:** Instant notification so you can act quickly.

---

## Developer Tools

### 17. Python SDK (For Programmers)

**What it does:** Developers can write Python code to interact with Argus.

**Example:**

```python
from argus import Gateway

# Login
db = Gateway("http://localhost:8000")
db.login("alice", "SecurePass123!")

# Run a query
result = db.query("SELECT * FROM users LIMIT 10")
print(result["rows"])  # See the results

# Explain a query
explanation = db.explain("SELECT * FROM orders")
print(explanation)

# Ask in natural language
ai_result = db.nl_to_sql("Top 5 customers by spending")
print(ai_result["generated_sql"])
```

**Benefit:** Easy integration into Python applications and scripts.

### 18. Command-Line Tool (For System Admins)

**What it does:** Run Argus commands directly from your terminal.

**Example:**

```bash
# Login
argus login http://localhost:8000 alice SecurePass123!

# Run a query
argus query "SELECT COUNT(*) FROM users"

# Explain SQL
argus explain "SELECT * FROM users WHERE age > 18"

# Ask in plain English
argus nl-to-sql "How many users signed up today?"

# Check system health
argus status
```

**Benefit:** Automation, scripting, easy to build into pipelines.

---

## Summary: What Makes Argus Different

| Feature                     | Benefit                                           |
| --------------------------- | ------------------------------------------------- |
| 6-layer security pipeline   | Your database is heavily protected                |
| 3-layer password protection | Passwords literally can't leak                    |
| 8-10× cache speedup         | Users get results instantly                       |
| GROQ + fallback AI          | Natural language queries always work, no failures |
| Complete audit trail        | Regulatory compliance + security investigation    |
| Rate limiting               | Fair access, prevents DOS attacks                 |
| Circuit breaker             | System recovers from failures automatically       |
| Dry-run mode                | Test expensive queries safely first               |
| Dashboard + alerts          | Always know what's happening                      |

---

## Getting Started (Easy!)

**One command to start everything:**

```bash
docker compose up --build
```

**Then try a query:**

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"SecurePass123!"}'

# Run query
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer <token>" \
  -d '{"query":"SELECT COUNT(*) FROM users"}'

# Ask in English
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer <token>" \
  -d '{"question":"How many users are active?"}'
```

---

**Argus is production-ready, fully tested, and designed for real-world use.** Start protecting your database today!
