# Argus Implementation Checklist — Current Status (June 2026)

> Last updated after: Multi-DB Workbench + Security Hardening + AI Rate Limiting + Auth Fixes

---

## Layer 1 — Security

- [x] **JWT authentication** — `gateway/middleware/security/auth.py`, `create_jwt` / `decode_jwt`
- [x] **API Key auth (SHA-256 hashed + Redis cache)** — `get_current_user()` with Redis fast-path + DB fallback
- [x] **API Key scoping** — `allowed_tables`, `allowed_query_types`, `rate_limit_override` per key
- [x] **Brute-force protection** — `gateway/middleware/security/brute_force.py` — 5 attempts → 15-min lockout
- [x] **IP allowlist/blocklist** — `IPRule` model, Redis `SISMEMBER` on every request
- [x] **Honeypot auto-ban** — `HONEYPOT_TABLES` config, auto-ban 24h on access
- [x] **Rate limiting (per-role sliding window)** — admin:500 / readonly:60 / guest:10 req/min
- [x] **SQL injection detection (13+ patterns)** — regex-based, `gateway/middleware/security/`
- [x] **Query type allowlist (DROP/EXEC/TRUNCATE blocked)** — query validator
- [x] **RBAC (table allowlists, column deny list, PII masking)** — `gateway/middleware/security/rbac.py`
- [x] **Sensitive column block** — `hashed_password`, `password`, `secret`, `token`, `api_key` blocked at query level
- [x] **HMAC request signing** — `validate_hmac_signature()` in auth.py + SDK sends `X-Timestamp`/`X-Signature`

**Auth Hardening (June 2026):**
- [x] **Username validation** — 3–32 chars, `[a-zA-Z0-9_-]` only (Pydantic `field_validator`)
- [x] **Email validation** — format regex + 254-char max, lowercased on register
- [x] **Password validation** — 8–128 chars, ≥1 letter + ≥1 digit required
- [x] **Input whitespace stripping** — `username` and `password` stripped on login/register
- [x] **`is_active` enforced on login** — disabled accounts get 403
- [x] **`is_active` enforced on token refresh** — disabled accounts get 403
- [x] **`Role.readonly` enum on register** — not bare string `"readonly"`
- [x] **Enum-safe JWT encoding** — `role.value` extracted before `create_jwt()`
- [x] **5-minute token refresh grace window** — accepts recently-expired tokens, re-reads role from DB
- [x] **`bare except` fixed** — `except Exception:` in API key cache write

---

## Layer 2 — Performance

- [x] **Query fingerprinting** — normalize whitespace + replace literals + SHA-256
- [x] **Redis query caching (role-scoped, TTL, tag invalidation)** — `argus:cache:{fp}:{role}`, 60s TTL
- [x] **Cache cleanup (SSCAN stale tags)** — auto-cleanup when tag set grows beyond 1000 keys
- [x] **Automatic LIMIT injection** — `AUTO_LIMIT_DEFAULT=1000` if no LIMIT in query
- [x] **Pre-flight cost estimation (EXPLAIN JSON)** — budget check before execution
- [x] **Daily query budget (Redis INCRBYFLOAT)** — per-user per-day credit system
- [x] **Read/write routing** — SELECT → replica, INSERT/UPDATE → primary (asyncpg pools)

---

## Layer 3 — Execution

- [x] **Circuit breaker (Redis-backed, 3 states)** — per-connection-label breaker state
- [x] **Column encryption (AES-256-GCM)** — gateway-level + per-connection config
- [x] **Retry with exponential backoff** — 100/200/400ms on transient errors
- [x] **EXPLAIN ANALYZE post-execution + index recommendations** — slow query detection
- [x] **Query complexity scoring** — cost estimator
- [x] **5-second query timeout** — hard timeout on all DB calls
- [x] **External DB routing (Multi-DB Workbench)** — `connection_id` routes to `user_databases`

---

## Layer 4 — Observability

- [x] **Trace IDs in every request** — UUID per request, in every log line and response
- [x] **Immutable audit log (async write)** — `AuditLog` model, fire-and-forget
- [x] **Redis metrics counters** — `requests_total`, `cache_hits`, `latency_samples`, `errors`
- [x] **`GET /api/v1/metrics/live`** — real-time dashboard metrics
- [x] **Webhook alerts (Discord/Slack) async** — slow query + circuit trip + anomaly
- [x] **Table access heat map (Redis ZINCRBY)** — `GET /api/v1/metrics/heatmap`
- [x] **Health and status endpoints** — `GET /health`, `GET /api/v1/status`
- [x] **SLA snapshots** — hourly `SLASnapshot` records

---

## Layer 5 — Hardening

- [x] **AES-256-GCM column encryption** — random nonce per encrypt
- [x] **DLP scanning** — PII regex (email, SSN, credit card) on result rows
- [x] **Time-based RBAC** — `allowed_hours` + `allowed_weekdays` + timezone
- [x] **Compliance export** — `GET /admin/compliance-report` (JSON/CSV)
- [x] **Query whitelist mode** — approved fingerprints only, `QueryWhitelist` table
- [x] **IP management API** — admin can add/remove IP rules at runtime

---

## Layer 6 — AI Intelligence

- [x] **NL→SQL (LLM + schema_hint + pattern guardrails)** — `POST /ai/nl-to-sql`
- [x] **Query explanation (LLM)** — `POST /ai/explain`
- [x] **Data insights** — `POST /ai/insights`
- [x] **AI anomaly explanation** — `POST /ai/explain-anomaly`
- [x] **Schema Chat (NEW)** — `POST /ai/schema-chat` — natural language schema Q&A
- [x] **GROQ + MOCK fallback** — zero failure: Groq primary, mock pattern-based fallback
- [x] **AI rate limit (NEW)** — 20 req/min per user across all AI endpoints (Redis)
- [x] **AI topic enforcement (NEW)** — 60+ SQL/DB keywords required, 2000-char max input
- [x] **Dry-run mode** — pipeline preview without execution

---

## Multi-DB Workbench (Phase B, NEW)

- [x] **Register external PostgreSQL connections** — conn string encrypted at rest
- [x] **Connection ownership enforcement** — `user_id` FK, users can only access own connections
- [x] **Test connectivity** — `POST /connections/{id}/test`
- [x] **Schema exploration** — `GET /connections/{id}/schema` (tables, columns, types, indexes)
- [x] **Query routing** — `connection_id` field routes execution to external DB
- [x] **Per-connection encryption config** — `ColumnEncryptionConfig` model
- [x] **Per-connection circuit breaker** — `argus:circuit:{connection_id}` in Redis

---

## Frontend (React + TypeScript + Vite)

- [x] **Login / Register page** — JWT-based auth with brute-force awareness
- [x] **Password strength indicator** — live bar on register (Weak/Fair/Good/Strong)
- [x] **Client-side input validation** — mirrors backend rules (username regex, password complexity)
- [x] **Pydantic v2 error parsing** — array format errors displayed as `field: message`
- [x] **`useNavigate` on login** — no more `window.location.href` hard reload
- [x] **RequireAuth route guard** — JWT expiry checked client-side, redirect to `/login`
- [x] **RequireAdmin route guard** — JWT role decoded, non-admin redirected to `/dashboard`
- [x] **Query Workbench** — Monaco Editor, connection selector, result grid
- [x] **Multi-DB Connection Manager** — register/test/delete external DB connections
- [x] **NL→SQL Panel** — natural language input, generated SQL preview
- [x] **Schema Browser** — per-connection table/column explorer
- [x] **Dashboard** — metrics, health status, heatmap
- [x] **Query Diff Viewer** — side-by-side SQL comparison
- [x] **Dry-Run Panel** — pipeline checklist preview
- [x] **Admin Dashboard** — 7 tabs (audit, slow queries, budget, IP rules, users, whitelist, compliance) — admin only

---

## SDK & CLI

- [x] **Python SDK (`argus-gateway`)** — `sdk/argus/client.py`
- [x] **HMAC signing** — `X-Timestamp` + `X-Signature` headers auto-added
- [x] **Typer CLI** — `login`, `query`, `explain`, `nl-to-sql`, `status` commands

---

## Deployment & CI

- [x] **One-command Docker Compose** — `docker compose up --build`
- [x] **GitHub Actions CI** — `.github/workflows/ci.yml` — pytest on every push
- [x] **163+ passing tests** — 100% green

---

## Open Issues / Technical Debt

| Severity | Item | File |
|----------|------|------|
| 🔴 Critical | Rotate `GROQ_API_KEY` — was committed to repo | `.env` |
| 🔴 Critical | CORS `allow_origins=["*"]` — must be explicit list | `gateway/main.py` |
| 🔴 Critical | JWT in `localStorage` — XSS risk; consider `HttpOnly` cookie | `frontend-ts/src/` |
| 🔴 Critical | HMAC validation always returns `True` — not enforced | `middleware/security/auth.py` |
| 🟠 High | `UNION ALL SELECT` not blocked (only `UNION SELECT`) | SQL validator |
| 🟠 High | Raw DB error messages on external connection failures | `routers/v1/connections.py` |
| 🟠 High | Brute force per-IP only — no per-account global counter | `brute_force.py` |
| 🟠 High | Plaintext connection string logged on registration | `routers/v1/connections.py` |
| 🟡 Medium | `redis.keys(pattern)` O(N) in budget endpoint — use SCAN | `routers/v1/query.py` |
| 🟡 Medium | `datetime.utcnow()` deprecated (Python 3.12+) — use `timezone.utc` | multiple files |

---

## Test Coverage

| Suite | Count | Status |
|-------|-------|--------|
| Security unit tests | 40+ | ✅ Pass |
| Performance unit tests | 25+ | ✅ Pass |
| Execution unit tests | 20+ | ✅ Pass |
| AI unit tests | 15+ | ✅ Pass |
| Integration tests | 10+ | ✅ Pass |
| **Total** | **163+** | **✅ 100% green** |

---

_Last Updated: June 2026_
