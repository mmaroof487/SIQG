# Argus Tier 6: Advanced Features Guide (Steps 25-32)

This guide covers the final tier of Argus — the polish and compliance features that make it enterprise-ready.

---

## Step 25: Time-Based Access Control

**What it is:** Restrict database access to specific hours or days.

**Example use case:** Your readonly role can only access data during business hours (9 AM - 5 PM EST, Monday - Friday).

**Try it:**

```bash
# As a readonly user during allowed hours (e.g., 2 PM EST on Tuesday)
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users LIMIT 5"}'
```

**Result (during allowed hours):**

```json
{
  "rows": [...],
  "rows_count": 5,
  "latency_ms": 12.3
}
```

✅ **Query succeeded**

**After business hours (e.g., 6 PM EST):**

```json
{
	"detail": "Access blocked: Your role (readonly) has access only 09:00-17:00 EST, Monday-Friday. Next access: Monday 09:00 EST",
	"blocked_until": "2026-04-07T14:00:00-04:00"
}
```

HTTP Status: **403 Forbidden** 🔒

**Configuration:**

Admin can set time-based rules per role in `gateway/config.py`:

```python
TIME_BASED_RBAC = {
    "readonly": {
        "allowed_hours": "09:00-17:00",  # 9 AM to 5 PM
        "allowed_weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "timezone": "America/New_York"
    },
    "guest": {
        "allowed_hours": "10:00-16:00",  # More restrictive
        "allowed_weekdays": ["Monday", "Tuesday", "Wednesday"],
        "timezone": "UTC"
    }
}
```

---

## Step 26: Query Diff Viewer

**What it is:** See exactly what Argus modified in your query before execution.

**Why you need it:** Transparency. Understand LIMIT injection, column stripping, etc.

**Example:**

You submit:

```sql
SELECT * FROM users WHERE id = 1
```

Argus shows:

```diff
  SELECT * FROM users WHERE id = 1
+ LIMIT 50  ← Injected for safety
```

**In the web UI:**

- **Original**: Your query (left side)
- **Modified**: Argus version (right side)
- **Diff highlight**: Red/green showing changes
- **Toggle**: Side-by-side or inline view

**Example response:**

```json
{
	"original_query": "SELECT * FROM users WHERE id = 1",
	"modified_query": "SELECT * FROM users WHERE id = 1 LIMIT 50",
	"changes": [
		{
			"type": "LIMIT injection",
			"reason": "Safety guardrail to prevent runaway queries"
		}
	],
	"will_execute": true
}
```

---

## Step 27: Dry-Run Mode

**What it is:** Preview what a query WOULD do without actually running it.

**Why you need it:** Estimate cost, check permissions, verify logic before expensive queries.

**Try it:**

```bash
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query":"SELECT * FROM orders WHERE amount > 1000",
    "dry_run": true
  }'
```

**Result:**

```json
{
	"would_execute": true,
	"reason": "Query passed all security checks",
	"pipeline_checks": [
		{
			"stage": "1. Authentication",
			"status": "pass",
			"detail": "Valid JWT token"
		},
		{
			"stage": "2. Security",
			"status": "pass",
			"detail": "No SQL injection detected"
		},
		{
			"stage": "3. RBAC",
			"status": "pass",
			"detail": "Role 'readonly' can access 'orders' table"
		},
		{
			"stage": "4. Budget",
			"status": "pass",
			"detail": "Estimated cost 42.5 < remaining 48749.5"
		},
		{
			"stage": "5. Circuit Breaker",
			"status": "pass",
			"detail": "Database is healthy"
		}
	],
	"estimated_cost": 42.5,
	"estimated_rows": 1024,
	"estimated_latency_ms": 18.2
}
```

**If it would fail (blocked query):**

```json
{
	"would_execute": false,
	"reason": "RBAC violation",
	"blocked_at_stage": "3. RBAC",
	"block_detail": "Your role cannot access sensitive table 'admin_settings'"
}
```

---

## Step 28: Index DDL Copy Button

**What it is:** Show recommended SQL CREATE INDEX statements with one-click copy.

**Why you need it:** Give index recommendations to your DBA without manual SQL writing.

**Example response:**

```json
{
	"query": "SELECT * FROM users WHERE email LIKE '%gmail%'",
	"analysis": {
		"scan_type": "Sequential Scan (slower)",
		"index_recommendations": [
			{
				"index_name": "idx_users_email",
				"ddl": "CREATE INDEX idx_users_email ON users(email);",
				"reason": "Query filtered by email column, full table scan detected",
				"estimated_speedup": "15-25x faster"
			},
			{
				"index_name": "idx_users_created",
				"ddl": "CREATE INDEX idx_users_created ON users(created_at DESC);",
				"reason": "Consider for ordering by creation date",
				"estimated_speedup": "8-12x faster"
			}
		]
	}
}
```

**In the web UI:**

- Each recommendation shows the DDL
- Click "Copy DDL" button
- Paste into your DBA's ticket/chat
- DBA runs the CREATE INDEX statement

---

## Step 29: Admin Dashboard

**What it is:** Full admin control panel for system management.

**Who uses it:** Database admins, security officers, compliance teams.

**Tabs available:**

### Tab 1: Audit Log

Who queried what, when:

```
User: alice           | Query: SELECT * FROM users | Time: 14:32 | Status: ✅
User: bob             | Query: SELECT * FROM admin  | Time: 14:30 | Status: ❌ (blocked)
User: charlie         | Query: SELECT id FROM users | Time: 14:25 | Status: ✅
```

Filter by:

- Date range
- User
- Status (success/blocked)
- Query pattern

### Tab 2: Slow Queries

Queries taking > 200ms:

```
Query: SELECT * FROM orders WHERE status='pending'
Executed: 8 times
Avg Latency: 542ms
Max Latency: 1023ms
Recommendation: Add index on orders(status)
```

### Tab 3: Budget Usage

Per-user spending:

```
alice:     Used  1,250 / 50,000 units (2.5%)   ▌░░░░░░░░░░░
bob:       Used    450 / 50,000 units (0.9%)   ░░░░░░░░░░░
charlie:   Used 15,200 / 50,000 units (30.4%)  █████░░░░░░░
```

### Tab 4: IP Rules & Blocklist

```
Blocked IPs (24-hour auto-unblock):
- 192.168.1.100  (honeypot detection)    Expires: 2026-04-07 14:32
- 10.0.0.50      (brute force)           Expires: 2026-04-07 13:15
```

Whitelist IPs:

```
Trusted IPs (permanent):
- 203.0.113.0    (Company VPN)
- 198.51.100.0   (Partner API)
```

### Tab 5: User Management

```
User      | Role      | Created  | Last Login | Status
alice     | readonly  | Apr 1    | Apr 7 14:5 | ✅ Active
bob       | guest     | Apr 2    | Apr 6 10:2 | ✅ Active
charlie   | admin     | Mar 30   | Apr 7 09:1 | ✅ Active
dave      | readonly  | Apr 5    | Never      | ⚠️ Never Logged In
```

### Tab 6: Query Whitelist

Approved queries for locked-down mode:

```
Query Fingerprint                      | Approved By | Status
5a7a9f2e8c6d1b4e3a2f9c5d1e7a8b...   | alice@admin | ✅ Approved (50 uses)
7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d...   | bob@admin   | ✅ Approved (12 uses)
```

Action: Click "Approve" to whitelist new queries.

### Tab 7: Compliance Export

Download audit-ready reports:

```
Period: Last 30 days

Summary:
- Total Queries: 4,521
- Successful: 4,456 (98.6%)
- Blocked: 65 (1.4%)
- PII Accessed: 12 times (masked in logs)
- Anomalies Detected: 3 (rate spike, brute force, pattern)

Export as: [JSON] [CSV] [PDF]
```

---

## Step 30: HMAC Request Signing

**What it is:** Sign your API requests with HMAC-SHA256 for extra security.

**Why you need it:** Prevent replay attacks, ensure request authenticity.

**How it works:**

1. Client generates: `X-Timestamp: 1712412000` (current Unix time)
2. Client creates: `signature = HMAC-SHA256(timestamp:method:path:body, api_secret)`
3. Client sends: `X-Signature: <signature>` header
4. Gateway validates:
   - Timestamp is fresh (within 30 seconds)
   - Signature matches using stored secret
   - Request is authentic

**Example (using SDK):**

```python
from argus_sdk import Client

client = Client(
    api_key="your-api-key",
    api_secret="your-api-secret",  # Required for HMAC signing
    base_url="http://localhost:8000"
)

# SDK automatically signs the request
response = client.query("SELECT * FROM users LIMIT 5")
```

**Headers sent by SDK:**

```
Authorization: Bearer eyJhbGci...
X-Timestamp: 1712412000
X-Signature: 8f7e6d5c4b3a2f1e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a
```

**Manual HMAC calculation (if not using SDK):**

```bash
TIMESTAMP=$(date +%s)
METHOD="POST"
PATH="/api/v1/query/execute"
BODY='{"query":"SELECT 1"}'
SECRET="your-api-secret"

# Create message to sign
MESSAGE="$TIMESTAMP:$METHOD:$PATH:$BODY"

# Calculate HMAC
SIGNATURE=$(echo -n "$MESSAGE" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)

# Make request with signature
curl -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Timestamp: $TIMESTAMP" \
  -H "X-Signature: $SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

**If signature is invalid:**

```json
{
	"detail": "Invalid request signature. Request may have been tampered with."
}
```

HTTP Status: **401 Unauthorized** 🔒

---

## Step 31: Compliance Report Export

**What it is:** Generate audit-compliant reports for SOC2, HIPAA, etc.

**Why you need it:** Prove security posture to auditors and compliance teams.

**Get compliance report:**

```bash
curl -X GET "http://localhost:8000/api/v1/admin/compliance-report?period=30d&format=json" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Result (JSON format):**

```json
{
	"period": "30 days (March 8 - April 7, 2026)",
	"generated_at": "2026-04-07T14:32:00Z",
	"generated_by": "admin@example.com",

	"audit_summary": {
		"total_queries": 4521,
		"successful_queries": 4456,
		"blocked_queries": 65,
		"success_rate": "98.6%",
		"average_latency_ms": 5.23,
		"p95_latency_ms": 15.8,
		"p99_latency_ms": 42.5
	},

	"security_events": {
		"sql_injections_blocked": 12,
		"brute_force_attempts": 3,
		"honeypot_triggers": 2,
		"ip_blocks": 5,
		"sensitive_field_access_attempts": 8
	},

	"pii_accessed": {
		"total_records_returned": 8492,
		"pii_fields_masked": 1247,
		"fields": ["email", "phone", "ssn"],
		"roles_accessing_pii": ["readonly", "analyst"],
		"most_accessed_pii_table": "users (email field)"
	},

	"rate_limiting": {
		"rate_limit_hits": 42,
		"users_affected": 3,
		"most_limited_user": "charlie (8 hits)",
		"busiest_hour": "14:00-15:00 UTC"
	},

	"anomalies": {
		"rate_spikes": 2,
		"performance_degradations": 1,
		"unusual_patterns": 3,
		"total_anomalies": 6
	},

	"budget_compliance": {
		"total_budget_available": 150000,
		"total_spent": 52143,
		"utilization_percent": "34.8%",
		"overages": 0,
		"users_exceeding_limits": 0
	},

	"top_users": [
		{
			"username": "alice",
			"query_count": 1542,
			"success_rate": "99.1%",
			"avg_latency_ms": 4.2
		},
		{
			"username": "bob",
			"query_count": 1203,
			"success_rate": "97.8%",
			"avg_latency_ms": 6.1
		}
	]
}
```

**CSV format:**

```csv
Period,30 days (March 8 - April 7, 2026)
Generated At,2026-04-07T14:32:00Z
Generated By,admin@example.com

Audit Summary
Total Queries,4521
Successful Queries,4456
Blocked Queries,65
Success Rate,98.6%
Average Latency,5.23 ms
P95 Latency,15.8 ms

Security Events
SQL Injections Blocked,12
Brute Force Attempts,3
Honeypot Triggers,2
IP Blocks,5

PII Summary
Total Records Returned,8492
PII Fields Masked,1247
Accessed Fields,email;phone;ssn
```

**Usage:**

- **For auditors:** "Here's our 30-day security report"
- **For compliance:** Evidence of PII masking, access control, anomaly detection
- **For management:** Metrics showing system health and uptime
- **For planning:** Identify slow queries, usage patterns

---

## Step 32: AI Anomaly Explanation

**What it is:** Get human-readable explanations of detected anomalies.

**Why you need it:** Understand "why" not just "what" when alerts fire.

**Example 1: Rate limit spike**

Imagine the system detects: 600 requests in 60 seconds (normal is 60).

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain-anomaly \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_type": "rate_limit_spike",
    "baseline_value": 60,
    "detected_value": 600,
    "user_id": "bob",
    "additional_context": "Requests concentrated on SELECT queries against users table",
    "timestamp": "2026-04-07T14:32:00Z"
  }'
```

**Result:**

```json
{
	"anomaly_type": "rate_limit_spike",
	"severity": "critical",
	"explanation": "An unusual spike in query requests (10x higher than baseline) was detected from user 'bob'. This could indicate a broken loop in client code, aggressive automation, or a potential brute force attack.",
	"recommended_action": "Immediately review recent code changes for 'bob's' application. Check API key access patterns and recent logs. If unauthorized, restrict the API key and investigate.",
	"context": {
		"affected_user": "bob",
		"magnitude": "10x increase",
		"duration": "approximately 5 minutes",
		"pattern": "Concentrated on users table SELECT queries"
	}
}
```

**Example 2: Performance degradation**

Detect: Queries taking 5x longer than normal (100ms average vs 20ms normal).

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain-anomaly \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_type": "performance_degradation",
    "baseline_value": 20,
    "detected_value": 100,
    "additional_context": "Affects queries on orders table"
  }'
```

**Result:**

```json
{
	"anomaly_type": "performance_degradation",
	"severity": "high",
	"explanation": "Database performance degraded significantly. Query response times are 5x slower than normal. This may be caused by missing indexes on the orders table, table locks, or excessive concurrent queries.",
	"recommended_action": "Run EXPLAIN ANALYZE on recent slow queries. Check for missing indexes (recommendations available via admin dashboard). Verify database load and connection count.",
	"suggested_checks": ["Look for missing indexes on frequently filtered columns", "Check table lock status", "Monitor concurrent connection count", "Review recent schema changes"]
}
```

**Example 3: Unusual access pattern**

Detect: User accessing tables they normally don't access.

```bash
curl -X POST http://localhost:8000/api/v1/ai/explain-anomaly \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_type": "unusual_access_pattern",
    "user_id": "dave",
    "additional_context": "User 'dave' suddenly accessed admin_logs and admin_settings tables (normally only queries users table)",
    "timestamp": "2026-04-07T13:15:00Z"
  }'
```

**Result:**

```json
{
	"anomaly_type": "unusual_access_pattern",
	"severity": "high",
	"explanation": "An unusual query pattern was detected. User 'dave' suddenly accessed sensitive admin tables (admin_logs, admin_settings) which differs significantly from their normal behavior (querying users table only).",
	"recommended_action": "This could indicate unauthorized access or compromised credentials. Immediately revoke the user's API keys if they were recently exposed. Review full audit log for this user. Contact them to confirm the access was authorized.",
	"actions_to_consider": [
		"Check if user's API key was recently compromised",
		"Review full audit log for user 'dave' past 24 hours",
		"Verify access to sensitive tables was intentional",
		"Reset user credentials if suspicious"
	]
}
```

**Severity levels:**

| Severity     | Color     | Meaning                        | Action               |
| ------------ | --------- | ------------------------------ | -------------------- |
| **low**      | 🟢 Yellow | Minor deviation, likely benign | Monitor              |
| **medium**   | 🟡 Orange | Possible issue, investigate    | Review within 1 hour |
| **high**     | 🔴 Red    | Likely issue, take action      | Review immediately   |
| **critical** | 🟣 Purple | Urgent, potential breach       | Take action now      |

**Integration with notifications:**

When severity = "critical", the system auto-triggers:

```
✉️ Email alert:     "CRITICAL: Rate limit spike detected"
🔔 Slack alert:      @channel-security "CRITICAL anomaly: rapid queries from user bob"
📞 PagerDuty alert:  Sends page to on-call security staff
```

---

## Complete Tier 6 Feature Set

**Summary of all Tier 6 features (Steps 25-32):**

| Step   | Feature                | Purpose                                         |
| ------ | ---------------------- | ----------------------------------------------- |
| **25** | Time-Based RBAC        | Restrict access to specific hours/days per role |
| **26** | Query Diff Viewer      | See exactly what Argus modifies in your query   |
| **27** | Dry-Run Mode           | Preview query execution without running it      |
| **28** | Index DDL Copy         | Copy-paste recommended indexes to your DBA      |
| **29** | Admin Dashboard        | Full control panel for system management        |
| **30** | HMAC Signing           | Sign requests for replay attack prevention      |
| **31** | Compliance Reports     | Audit-ready JSON/CSV/PDF reports                |
| **32** | AI Anomaly Explanation | MLL-powered explanations of detected anomalies  |

---

## Why These Features Matter

### For Security Teams:

- Time-based access = granular control
- HMAC signing = request authenticity
- Anomaly explanations = understand threats
- Compliance reports = prove compliance

### For Operations:

- Dry-run mode = safe testing
- Query diff = transparency
- Admin dashboard = centralized control
- Slow query detection = performance troubleshooting

### For Compliance:

- Audit logs = everything traceable
- PII masking = HIPAA/GDPR ready
- Compliance reports = audit readiness
- Rate limiting = DoS protection

### For Developers:

- AI anomaly descriptions = debugging insights
- DDL copy = index creation made easy
- Dry-run = cost estimation
- Query diff = understand modifications

---

## Advanced Usage Patterns

### Pattern 1: Cost-Conscious Querying

```bash
# 1. Dry-run to check cost
curl -X POST http://localhost:8000/api/v1/query/execute \
  -d '{"query":"<big query>", "dry_run":true}'

# 2. Check estimated_cost
echo "Cost: $estimated_cost units"

# 3. Check remaining budget
curl -X GET http://localhost:8000/api/v1/query/budget \
  -H "Authorization: Bearer $TOKEN"

# 4. If affordable, execute for real
curl -X POST http://localhost:8000/api/v1/query/execute \
  -d '{"query":"<big query>"}'
```

### Pattern 2: Emergency Debugging

```bash
# 1. Something is slow
# System detects performance anomaly

# 2. Get AI explanation
POST /api/v1/ai/explain-anomaly
  anomaly_type: performance_degradation

# 3. Read: "Missing index on orders(status)"

# 4. Copy DDL from admin dashboard
# CREATE INDEX idx_orders_status ON orders(status);

# 5. DBA runs it
# Performance restored!
```

### Pattern 3: Compliance Audit

```bash
# 1. Quarter-end: Get compliance report
curl -X GET "http://localhost:8000/api/v1/admin/compliance-report?period=90d&format=pdf"

# 2. Generate Excel summary with:
#    - 4,521 queries executed
#    - 98.6% success rate
#    - 0 data breaches
#    - 1,247 PII fields masked
#    - 12 SQL injections blocked

# 3. Send to external auditor
# "Here's material evidence of our security controls"
```

---

**You're now ready to deploy Argus to production with all 32 features!** 🚀
