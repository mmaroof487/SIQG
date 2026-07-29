# Security Posture

Security is Argus's strongest selling point. The gateway operates on a Zero Trust model, assuming that both the incoming request and the backend database contain potentially hostile data.

## Layer 1 Defenses

### 1. Authentication
- **JWT**: Tokens are signed using HS256 with a 60-minute expiry.
- **Refresh Flow**: Tokens can be refreshed, but a 5-minute grace window is enforced to prevent replay abuse.
- **State Verification**: The `is_active` flag is checked on every login and refresh to instantly disable compromised accounts.
- **Frontend Storage**: JWT tokens are securely stored in `HttpOnly`, `Secure`, and `SameSite=Strict` cookies to mitigate XSS risks, completely avoiding `localStorage`.

### 2. SQL Validation & Sanitization
Argus parses incoming SQL strings into an Abstract Syntax Tree (AST) using `sqlglot` to comprehensively detect and block SQL injection vectors and unauthorized mutations before they reach the database.
- **Command Blocking**: `DROP`, `TRUNCATE`, `ALTER`, and `EXEC` are hard-blocked at the parser level.
- **Sensitive Column Blocking**: Direct queries targeting columns like `hashed_password`, `token`, and `api_key` are rejected.

### 3. Honeypots
Decoy tables (e.g., `_sys_config_backup`) are injected into the schema. If an automated scanner or attacker queries these tables, the system immediately returns a 403 Forbidden and adds the offending IP to a 24-hour blocklist.

### 4. Rate Limiting & Brute Force Protection
- **Sliding Window**: Role-based buckets ensure fair usage (Admin: 500/min, Readonly: 60/min).
- **AI Rate Limits**: Isolated 20 req/min limits across all AI endpoints prevent LLM API exhaustion.
- **Brute Force**: 5 consecutive failed logins trigger a 15-minute IP lockout.

## Layer 3 & 4 Defenses

### 5. Role-Based Access Control (RBAC) & Masking
Before results are returned to the user, Argus intercepts the JSON payload.
- Based on the user's role, columns are either dropped or masked (e.g., `email` becomes `u***@***.com`).
- Time-based RBAC allows access to specific connections only during configured business hours.

### 6. Cache Isolation
Cache keys include the user's role in the hash signature (`argus:cache:{role}:{hash}`). This ensures that an admin and a readonly user executing the exact same query will hit isolated cache buckets, preventing privilege escalation via cache poisoning.

### 7. Encryption at Rest
See [ENCRYPTION.md](ENCRYPTION.md) for full details on AES-256-GCM envelope encryption.

### 8. Audit Logging
Every query executed through the gateway is tracked asynchronously.
- `trace_id` for end-to-end request tracking.
- `user_id`, `execution_time`, `cache_hit` boolean.
- Webhook alerts are dispatched for slow queries or security threshold breaches.

### 9. Security Headers
The API responses enforce standard security headers, and webhook endpoints enforce `X-Signature` HMAC payload validation.
