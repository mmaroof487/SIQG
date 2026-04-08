# Argus — Complete Implementation Backlog

> Covers everything needed to take Argus from v1.0 to a complete, demo-ready, placement-winning project.
> Frontend serves two distinct audiences and is treated as a primary feature track alongside the backend.
> Incorporates all kanban items, bug fixes, and extended roadmap.

---

## Audience Split — Frontend Design Principle

The frontend must serve two audiences with different needs. Every UI decision should be made with this in mind.

**Non-dev users (primary target):**
Plain English input → results table → health status. They should never need to read JSON, understand query plans, or know SQL exists. The NL→SQL panel is their entry point. The health page tells them if something is wrong without reading logs. The index DDL copy button lets them hand actionable output to their DBA without touching the response body.

**Dev users:**
Monaco editor with the full analysis panel inline — scan type, cost estimate, index DDL suggestions, complexity score, and the raw EXPLAIN output all visible without leaving the page. They want control and visibility, not abstraction.

---

## Priority Legend

| Label | Meaning |
|-------|---------|
| 🔴 Fix Now | Blocking bugs — must be resolved before any demo or GitHub push |
| 🟥 Next Sprint | Build immediately — highest demo and interview value |
| 🟧 Backlog | Build after sprint — strong value, not blocking |
| 🟩 Polish | Add when core is solid — differentiation and completeness |
| ⚪ Future | V2 scope — mention as vision, do not build now |

---

## 🔴 Fix Now — 2 Critical Items

These block every demo and every GitHub push. Nothing else matters until these are done.

---

### FIX-1 — hashed_password Leaking to Non-Admin Roles `bug` `security`

`SELECT *` returns the full bcrypt hash to readonly and guest roles. The RBAC column deny list is not being applied after the NL→SQL pipeline — `strip_denied_columns()` is called for direct queries but the NL→SQL path bypasses it.

**Root cause:** `gateway/routers/v1/ai.py` calls `run_pipeline()` but the result rows are not passed through `apply_rbac_masking()` before being returned.

**Fix:**
- Ensure `apply_rbac_masking(role, rows)` is called on every result — including NL→SQL generated queries — before the response is serialised
- Verify `hashed_password` and `internal_notes` are in the deny list for readonly and guest roles
- Add a shell test: `SELECT * FROM users` as readonly → confirm `hashed_password` is absent from response

**Effort:** ~2 hours

---

### FIX-2 — Phase 5 Pipeline Not Shell-Verified `bug` `security`

Encryption, masking, circuit breaker, and retry are unit tested but not confirmed wired in `query.py`. Unit tests verify the modules work in isolation — they do not verify the modules are actually called during a live query.

**Fix — add 5 shell checks to the Phase 5 section of `test_all_phases.sh`:**

```bash
# 1. Circuit breaker blocks when open
redis-cli SET argus:circuit_breaker '{"state":"open","failures":5}' 
curl POST /api/v1/query → expect 503 instantly
redis-cli DEL argus:circuit_breaker

# 2. Encryption roundtrip
INSERT a row with ssn="123-45-6789"
Check DB directly → stored value is base64 ciphertext, not plaintext

# 3. Masking active in pipeline
SELECT a row with email column as readonly → expect u***@example.com

# 4. Masking strips denied columns
SELECT * FROM users as readonly → hashed_password must be absent

# 5. Retry wraps execution
Confirm execute_with_retry() is called, not direct conn.fetch()
```

**Effort:** ~1 day

---

## 🟥 Next Sprint — Build These Now

---

### SPRINT-1 — React Frontend: Non-Dev UX `feature` `ux`

The primary deliverable for placement demos. Serves both audiences from one interface.

**Non-dev layer (top of page):**
- Plain English input field above the Monaco editor — the NL→SQL panel (see SPRINT-5)
- Results table: clean tabular display, not raw JSON, with readable column headers
- Health status page: green/red indicators, no log reading required

**Dev layer (below results):**
- Monaco SQL editor with syntax highlighting
- Analysis panel showing scan type, cost estimate, complexity score, index DDL suggestions inline
- Query history (last 50, searchable)
- Schema browser from `information_schema`

**Key constraint:** Non-dev users should be able to use the full product without ever opening the Monaco editor or reading a JSON response body.

**Effort:** ~3 days total (if building from scratch), ~1 day if enhancing existing React app

---

### SPRINT-2 — Live Metrics Dashboard `feature` `ux`

Recharts polling `/metrics/live` every 5 seconds. No authentication required — ops and non-dev users can bookmark this page.

**Components:**
- P50/P95/P99 latency line chart (last 60 minutes)
- Cache hit ratio gauge (current session)
- Table access heat map (sorted by query count)
- Slow query count with link to slow query log
- Circuit breaker state indicator (closed/open/half-open)
- Requests per minute bar chart

**Effort:** ~1.5 days

---

### SPRINT-3 — GitHub Actions CI Badge Green `infra`

`ci.yml` is written but not pushed. Without the badge on the README, the CI claim on a resume is unverifiable.

**Steps:**
1. Push to main branch
2. Confirm GitHub Actions run passes (pytest + coverage)
3. Copy badge URL → paste into README header
4. Verify badge shows green on the public repo page

**Effort:** ~1 hour

---

### SPRINT-4 — README with Screenshots `dx`

The README is the first thing a recruiter sees. It is marketing, not documentation.

**Required sections:**
- One-liner pitch at the top (one sentence, no jargon)
- Architecture ASCII diagram (the 4-layer pipeline)
- Feature table (what it does, what problem it solves)
- `docker compose up` quick start — must work in under 3 commands
- 4 screenshots minimum:
  1. Swagger docs page at `/api/v1/docs`
  2. Query response showing `analysis`, `cached`, `complexity` fields
  3. Cache miss → cache hit latency difference
  4. Metrics dashboard live
- CI badge, test count badge

**Effort:** ~1 day

---

### SPRINT-5 — NL→SQL UI Panel `feature` `ux`

Plain English input field above the Monaco editor. The entry point for non-dev users.

**Flow:**
1. User types: "Show me all users created in the last 7 days"
2. On submit: call `/api/v1/ai/nl-to-sql` → show generated SQL in Monaco editor
3. Auto-execute the SQL → show results in results table
4. Add "Explain this" button next to each result row → calls `/api/v1/ai/explain` → shows plain-English explanation inline

**Why it matters:** The backend endpoints already exist. This is pure frontend wiring. In a demo, type English → get results → no SQL knowledge needed. Every audience understands it immediately.

**Effort:** ~1 day

---

## 🟧 Backlog — Build After Sprint

---

### BL-1 — Dry-Run Mode UI `feature` `ux`

Toggle in the frontend that enables dry-run mode on query submission. Shows pipeline checks, cost estimate, and a `would_execute` diff — without touching the database.

**What it shows non-dev users:** "Your query would cost 42 units, would scan 10,000 rows, and would be cached. Confirm to execute."

**Implementation:** `dry_run: true` flag already accepted by the query endpoint. Frontend toggle sends it, renders the `pipeline_checks` response object as a human-readable checklist.

**Effort:** ~half day

---

### BL-2 — Admin Dashboard Panel `feature` `ux`

Admin-only route in the frontend. Non-dev admins can manage the system without touching the API directly.

**Panels:**
- Audit log table with filters by user, time range, query type, block reason
- Slow query list with execution time, fingerprint, and recommendation
- Budget usage per user (bar chart, current day)
- IP blocklist management: view, add, remove entries
- User management: roles, API key rotation, deactivation

**Effort:** ~2 days

---

### BL-3 — Locust Load Test Screenshots `dx`

100 users, 60-second run. Screenshot the P95 cached vs uncached latency difference. Paste the numbers into the README.

**Why it matters:** "Cache reduces P95 latency from 180ms to 4ms under 100 concurrent users" is a sentence that changes how interviewers read your project. It turns a feature claim into a measured result.

**Steps:**
1. Run `locust -f tests/load/locustfile.py --host http://localhost:8000 -u 100 -r 10 -t 60s`
2. Screenshot the latency distribution chart from Locust web UI
3. Note P50, P95, P99 for cached and uncached queries
4. Add to README under "Performance" section

**Effort:** ~2 hours

---

### BL-4 — Index DDL Copy Button `ux`

In the analysis panel, show each `CREATE INDEX` suggestion with a one-click copy button next to it.

**Why it matters:** Non-dev users can hand the exact DDL to their DBA without reading the JSON response body or reformatting anything. This is the difference between "here's a suggestion" and "here's the command, ready to run."

**Implementation:** Index suggestions already returned in `analysis.index_suggestions[]`. Each suggestion renders as a code block with a copy-to-clipboard button.

**Effort:** ~2 hours

---

### BL-5 — Health Status Page `feature` `ux`

Visual `/health` page in the frontend. Non-dev users can see system health at a glance without reading logs or calling the API manually.

**Components:**
- Green/red indicator for: PostgreSQL primary, PostgreSQL replica, Redis, circuit breaker state
- Last successful query timestamp
- Current request rate
- Updates every 10 seconds automatically

**Effort:** ~half day

---

### BL-6 — SSCAN Stale Tag Cleanup `bug`

Cache tag sets (`siqg:cache_tags:{table}`) grow unbounded over time. When a cache key expires via TTL, the corresponding entry in the tag set remains. Over weeks, those sets grow without bound and SSCAN over them gets slower.

**Fix:** After `DEL`-ing a cache key during invalidation, also call `SREM siqg:cache_tags:{table} {cache_key}` to remove the stale entry from the tag set.

**Effort:** ~1 hour

---

### BL-7 — SDK CLI Demo Recording `dx`

Record `argus login → argus query → argus status` in a terminal session. Embed as an asciinema recording or GIF in the README.

**Why it matters:** Shows the CLI works end-to-end without an interviewer having to install anything. A recruiter or interviewer watching it sees a real tool, not a code dump.

**Steps:**
1. Install `asciinema`
2. Record: `asciinema rec demo.cast`
3. Run: `argus login http://localhost:8000 admin admin123` → `argus query "SELECT COUNT(*) FROM users"` → `argus status`
4. Upload to asciinema.org or convert to GIF with `agg`
5. Embed in README

**Effort:** ~1 hour

---

## 🟩 Optional Polish — Differentiation Items

---

### POL-1 — Time-Based Access Rules `feature` `security`

No database proxy — not even Formal or DataSunrise — has this. Two hours of implementation, one unique sentence in every interview.

**What it does:** Restrict query execution based on configurable time windows per role. "readonly role blocked after 10pm IST."

```python
# RBAC config
"readonly": {
    "allowed_hours": [9, 22],       # 9am to 10pm
    "allowed_weekdays": [0,1,2,3,4] # Mon-Fri only
    "timezone": "Asia/Kolkata"
}
```

**Implementation:**
- Add `allowed_hours`, `allowed_weekdays`, `timezone` to RBAC role config
- Check `datetime.now(tz)` in auth middleware before pipeline entry
- Return 403 with `"blocked_until": "09:00 IST Monday"` when outside window
- Redis TTL enforcement: set a key that expires at the next allowed window start

**Effort:** ~2 hours

---

### POL-2 — Compliance Report Export `feature`

One-click JSON or PDF export from the audit log. Argus already collects all the data — this is pure aggregation.

**Report includes:**
- PII fields accessed (by user, by role, by time range)
- Injection attempts blocked (pattern matched, source IP)
- Slow queries (fingerprint, execution time, user)
- Budget usage summary
- Anomaly flags raised

**Endpoint:** `GET /api/v1/admin/compliance-report?period=30d&format=json`

Frontend: "Export Report" button in the admin dashboard panel that downloads the JSON or triggers PDF generation.

**Effort:** ~1 day

---

### POL-3 — Query Diff Viewer `ux`

Side-by-side display in the frontend: original query the user typed vs. the actual query Argus executed, with all modifications highlighted.

```
Original:   SELECT * FROM users
Executed:   SELECT id, name, email FROM users LIMIT 1000
                                               ^^^^^^^^^^^^^^^^^^^
                                               [LIMIT injected by Argus]
```

**Implementation:** `query_diff` field already returned in the API response. Frontend renders it using `react-diff-viewer` or a custom highlight component.

**Effort:** ~half day

---

### POL-4 — HMAC Request Signing `security`

Timestamp-signed requests to prevent replay attacks. Uses `secrets.compare_digest()` for constant-time comparison (currently flagged as unchecked in the correctness checklist).

**What it does:** Every API request includes an HMAC-SHA256 signature of `timestamp + method + path + body`. The gateway validates the signature and rejects requests where the timestamp is older than 30 seconds.

**Implementation:**
- Client adds headers: `X-Timestamp`, `X-Signature`
- Gateway validates: `HMAC-SHA256(secret, f"{timestamp}:{method}:{path}:{body}")`
- Use `secrets.compare_digest()` — never `==` for token comparison
- Add to SDK client automatically

**Effort:** ~half day

---

### POL-5 — AI Anomaly Explanation `feature`

No competitor explains anomalies — they only detect and flag them. This is a genuine gap.

**What it does:** When an anomaly is flagged (3× baseline rate from a new IP, unusual hour, unusual table target), an LLM wraps the raw anomaly data in a plain-English explanation and recommendation.

```
Anomaly flagged:
"User ran 340 queries in 5 minutes targeting the payments table at 2am 
from an IP not seen in the last 30 days. Recommend: alert admin, 
temporarily rate-limit this IP, require re-authentication."
```

**Implementation:**
- Anomaly detection already fires webhooks with raw data
- Add a call to `/api/v1/ai/explain` with the anomaly context
- Attach explanation to the webhook payload and the in-app notification

**Effort:** ~1 day

---

## Extended Backend Backlog

These are not on the kanban board but belong in the full roadmap.

---

### EXT-1 — Explainable Query Blocks `feature` 🟧

Return structured `block_reasons[]` and `suggested_fix` in every 400 response. Currently rejections return a single reason string with no actionable guidance.

```json
{
  "blocked": true,
  "block_reasons": ["Missing LIMIT clause — potential full table scan"],
  "suggested_fix": "Add LIMIT 1000 to your query"
}
```

Map each validation rule to a message + fix string. Required before the Block Explainer UI panel can be built.

**Effort:** ~1 day

---

### EXT-2 — API Key Scoping `feature` 🟧

API keys restricted to specific tables and query types. How Stripe and Twilio do it.

```
key: prod_readonly_abc123
  allowed_tables: [products, orders]
  allowed_query_types: [SELECT]
  rate_limit: 100/min
```

**Effort:** ~1 day

---

### EXT-3 — Per-Role Rate Limit Tiers `feature` 🟩

admin: 500/min, readonly: 60/min, guest: 10/min. One config dict lookup + one Redis key suffix change.

**Effort:** ~2 hours

---

### EXT-4 — Query Whitelisting Mode `feature` 🟩

Admin toggle: only pre-approved query fingerprints can execute. Everything else returns 403. No open-source proxy does this.

```bash
POST /api/v1/admin/whitelist/{fingerprint}  # approve
GET  /api/v1/admin/whitelist                # list approved
```

**Effort:** ~1 day

---

### EXT-5 — Slow Query Advisor `feature` 🟧

Combine EXPLAIN ANALYZE output + index suggestions + complexity score into a single `recommendation` field on slow query responses. All data already exists separately — this is one function to merge them.

**Effort:** ~2 hours

---

### EXT-6 — Schema Change Detection `feature` 🟩

Poll `information_schema`, store a schema hash, fire a webhook alert if the structure changes — new table, dropped column, changed type. Catches accidental migrations in staging.

**Effort:** ~half day

---

### EXT-7 — TOTP 2FA for Admin Accounts `security` 🟩

QR code on first admin login. Verify code on subsequent logins. Uses `pyotp`. Completes the security story: JWT + RBAC + 2FA.

**Effort:** ~half day

---

### EXT-8 — Query Result Pagination `feature` 🟩

Cursor-based (keyset) pagination. Accepts `cursor` + `page_size`, returns `next_cursor`. Prevents memory spikes on large result sets.

**Effort:** ~1 day

---

### EXT-9 — Batch Query Execution `feature` 🟩

`POST /api/v1/query/batch` — array of queries, returns array of results with individual timings, cache status, and per-query error detail.

**Effort:** ~1 day

---

## ⚪ Future / Enterprise Vision (V2)

> Do not build these for placement season. Mention when asked about product direction.

| Feature | Why It Matters |
|---------|---------------|
| ML-Based Anomaly Detection | Isolation Forest on 30 days of audit logs — replace hard-coded thresholds with learned patterns. Requires real production traffic. |
| Policy Simulation Mode | Test what impact a RBAC rule change would have before applying it. "72 existing queries would be blocked." |
| Multi-Database Support | MySQL, SQLServer, Snowflake, BigQuery via SQLAlchemy dialects. Enterprise requirement. |
| Advanced RBAC / ABAC | OPA policy engine: "Analyst CAN SELECT IF department=analytics." |
| Scheduled Query Execution | Cron-based automated reports. APScheduler + email/webhook delivery. |
| Query Versioning | Git-style diff, rollback, annotation history for saved queries. |
| AI Chat Interface (full) | Persistent conversation context with multi-turn query refinement. |
| Slack / Discord Integration | Conversational querying from messaging tools using existing NL→SQL endpoint. |

---

## Ordered Build Plan

Everything above in the sequence that maximises interview readiness per hour spent.

| Order | Item | Type | Effort | Why |
|-------|------|------|--------|-----|
| 1 | FIX-1 — hashed_password bug | Bug | 2h | Blocks every demo |
| 2 | FIX-2 — Phase 5 shell verification | Bug | 1d | Must be verifiably done |
| 3 | SPRINT-3 — CI badge green | Infra | 1h | Resume claim needs proof |
| 4 | SPRINT-5 — NL→SQL UI panel | Feature | 1d | Non-dev entry point |
| 5 | SPRINT-1 — React frontend UX | Feature | 1-3d | Primary demo surface |
| 6 | BL-5 — Health status page | Feature | 0.5d | Non-dev audience |
| 7 | BL-4 — Index DDL copy button | UX | 2h | Non-dev to DBA handoff |
| 8 | SPRINT-2 — Live metrics dashboard | Feature | 1.5d | Visual proof of observability |
| 9 | POL-3 — Query diff viewer | UX | 0.5d | Makes pipeline transparent |
| 10 | BL-6 — SSCAN stale tag cleanup | Bug | 1h | Silent production bug |
| 11 | EXT-5 — Slow query advisor | Feature | 2h | Combine existing outputs |
| 12 | EXT-1 — Explainable query blocks | Feature | 1d | No competitor has this |
| 13 | POL-1 — Time-based access rules | Feature | 2h | Unique, minimal effort |
| 14 | BL-2 — Admin dashboard panel | Feature | 2d | Non-dev admin audience |
| 15 | BL-1 — Dry-run mode UI | Feature | 0.5d | Non-dev safety check |
| 16 | EXT-2 — API key scoping | Feature | 1d | How real platforms work |
| 17 | POL-4 — HMAC request signing | Security | 0.5d | Correctness checklist gap |
| 18 | EXT-3 — Per-role rate limits | Feature | 2h | Completes RBAC story |
| 19 | EXT-4 — Query whitelisting mode | Feature | 1d | Unique vs PgBouncer |
| 20 | POL-2 — Compliance report export | Feature | 1d | Enterprise credibility |
| 21 | EXT-7 — TOTP 2FA | Security | 0.5d | Completes security story |
| 22 | POL-5 — AI anomaly explanation | Feature | 1d | No competitor explains anomalies |
| 23 | BL-3 — Locust screenshots | DX | 2h | Numbers beat claims |
| 24 | BL-7 — SDK CLI recording | DX | 1h | Shows CLI without install |
| 25 | SPRINT-4 — README + screenshots | DX | 1d | Most important deliverable |

---

## Summary Count

| Track | Fix Now | Next Sprint | Backlog | Polish | Future |
|-------|---------|-------------|---------|--------|--------|
| Frontend | — | 3 | 4 | 2 | 2 |
| Backend | 2 | — | 3 | 4 | 8 |
| Infra / DX | — | 2 | 2 | — | — |
| **Total** | **2** | **5** | **9** | **6** | **10** |

**32 items total. The first 3 (both fixes + CI badge) should be done before anything else is touched.**

---

*Argus v1.0 — 151 tests passing. This backlog defines v1.1 and the path to v2.0.*