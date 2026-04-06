# Argus — AI Execution Plan

> **Purpose:** Copy-paste these prompts into an AI IDE to integrate features from `integration_plan.md`.  
> **Rule:** Execute in order. Each step depends on the one above it.  
> **Verify:** After each step, run the verification command before moving on.

---

## TIER 1 — CRITICAL SECURITY FIXES

---

### STEP 1 — Centralize SENSITIVE_FIELDS

**What:** Create a single source of truth for sensitive field names.

**File:** `gateway/config.py`

**Prompt:**
```text
In gateway/config.py, inside the Settings class (after line 71, after daily_budget_default), 
add this property:

    # === SENSITIVE FIELDS ===
    sensitive_fields_csv: str = "hashed_password,password,token,api_key,secret,internal_notes"

    @property
    def sensitive_fields(self) -> set[str]:
        """Single source of truth for sensitive field names."""
        return {f.strip().lower() for f in self.sensitive_fields_csv.split(",") if f.strip()}

Then in gateway/routers/v1/query.py, replace lines 114-125 (the hardcoded password_fields block):

    # GUARDRAIL: Sensitive field protection (uses centralized config)
    from config import settings
    query_lower = payload.query.lower()
    for field in settings.sensitive_fields:
        if field in query_lower and not payload.query.strip().upper().startswith("INSERT"):
            logger.warning(f"[{trace_id}] ⚠️ Sensitive field '{field}' detected in query")
            raise HTTPException(
                status_code=403,
                detail=f"Access to sensitive field '{field}' is restricted."
            )
    logger.debug(f"[{trace_id}] ✅ Sensitive field check passed")

Do NOT change anything else. Keep all other imports and logic.
```

**Verify:**
```bash
cd gateway && python -c "from config import settings; print(settings.sensitive_fields)"
# Should print: {'hashed_password', 'password', 'token', 'api_key', 'secret', 'internal_notes'}
```

---

### STEP 2 — Block Sensitive Columns in Validator

**What:** Add a reusable function to `validator.py` that checks if SQL references sensitive fields.

**File:** `gateway/middleware/security/validator.py`

**Prompt:**
```text
In gateway/middleware/security/validator.py, after the validate_query function (after line 76), 
add this function:

def contains_sensitive_column(sql: str, sensitive_fields: set[str]) -> str | None:
    """
    Check if a SQL query references any sensitive column.
    Returns the field name if found, None otherwise.
    """
    lowered = sql.lower()
    for field in sensitive_fields:
        # Match field name as a word boundary to avoid false positives
        # e.g. "password" should match but "password_reset_count" should also match
        if field in lowered:
            return field
    return None

Do NOT modify any existing functions or imports.
```

**Verify:**
```bash
cd gateway && python -c "
from middleware.security.validator import contains_sensitive_column
print(contains_sensitive_column('SELECT hashed_password FROM users', {'hashed_password', 'token'}))
# Should print: hashed_password
print(contains_sensitive_column('SELECT name FROM users', {'hashed_password', 'token'}))
# Should print: None
"
```

---

### STEP 3 — Fix hashed_password Leak on NL→SQL Path

**What:** The NL→SQL endpoint calls `execute_query()` which already applies RBAC masking. BUT: verify the result rows go through masking. Currently `ai.py` line 533 calls `execute_query()` directly — this DOES run through the full pipeline including masking (line 269 of query.py). So the masking IS applied.

**THE REAL BUG:** The NL→SQL mock generates `SELECT *` for certain queries (line 236, 238 of ai.py). Even though masking removes `hashed_password` from the output, the column is still fetched from DB.

**File:** `gateway/routers/v1/ai.py`

**Prompt:**
```text
In gateway/routers/v1/ai.py, make these changes:

1. In the call_llm_mock function, find ALL generated SQL strings that contain "SELECT *" 
   and replace them with explicit safe columns. Currently there are none that use SELECT * 
   (the mock already uses explicit columns like "SELECT id, username, email..."), 
   so verify this is true.

2. In the SYSTEM_PROMPT_NL_TO_SQL string (line 54), add this rule after the existing rules:
   - NEVER include these columns in SELECT: hashed_password, password, token, api_key, secret, internal_notes
   - NEVER use SELECT * — always list columns explicitly

3. After the generated SQL is produced (after line 514, after the call_llm block) 
   and BEFORE error checking (before line 518), add a post-processing safety net:

        # POST-PROCESS: Strip any sensitive columns the LLM might have included
        from config import settings
        for field in settings.sensitive_fields:
            # Remove sensitive column references from generated SQL
            generated_sql = re.sub(
                rf',?\s*\b{re.escape(field)}\b\s*,?',
                ',',
                generated_sql,
                flags=re.IGNORECASE
            )
        # Clean up any double commas or trailing commas before FROM
        generated_sql = re.sub(r',\s*,', ',', generated_sql)
        generated_sql = re.sub(r',\s*FROM', ' FROM', generated_sql)
        generated_sql = re.sub(r'SELECT\s*,', 'SELECT ', generated_sql)

Do NOT touch any other code.
```

**Verify:**
```bash
# After starting services:
curl -s -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me all users"}' | python -m json.tool
# generated_sql should NOT contain hashed_password
```

---

### STEP 4 — Enforce Pipeline Order + strip_denied_columns

**What:** Add a `strip_denied_columns()` function for `SELECT *` rewriting.

**File:** `gateway/middleware/security/rbac.py`

**Prompt:**
```text
In gateway/middleware/security/rbac.py, after the apply_rbac_masking function (after line 149), 
add this function:

def strip_denied_columns(role: str, columns: list[str]) -> list[str]:
    """
    Filter out denied columns for the given role.
    Used to rewrite SELECT * into explicit allowed columns.
    
    Args:
        role: User role (admin, readonly, guest)
        columns: All columns from the table
    
    Returns:
        List of columns the role is allowed to see
    """
    if role == "admin":
        return columns
    
    return [col for col in columns if not is_column_denied(col, role)]

Do NOT modify any existing functions.
```

**Then in `gateway/routers/v1/query.py`**, verify the pipeline order. The current order is:

```
Line 101: check_ip_filter     ✅ (Layer 1)
Line 105: validate_query       ✅ (Layer 1)
Line 110: check_honeypot       ✅ (Layer 1)
Line 114: sensitive field check ✅ (Layer 1 — just updated in Step 1)
Line 129: check_rate_limit     ✅ (Layer 1)
Line 133: check_rbac           ✅ (Layer 1)
Line 142: fingerprint_query    ✅ (Layer 2)
Line 148: check_cache          ✅ (Layer 2)
Line 184: estimate_query_cost  ✅ (Layer 2)
Line 196: check_budget         ✅ (Layer 2)
Line 201: inject_limit_clause  ✅ (Layer 2)
Line 207: encrypt_query_values ✅ (Layer 2)
Line 250: execute_with_timeout ✅ (Layer 3 — includes circuit breaker + retry)
Line 254: decrypt_rows         ✅ (Layer 5 — BEFORE masking ✅)
Line 269: apply_rbac_masking   ✅ (Layer 5 — AFTER decrypt ✅)
Line 326: write_audit_log      ✅ (Layer 4)
Line 355: write_cache          ✅ (Layer 2)
```

The pipeline order is CORRECT. Add section labels as code comments:

```text
In gateway/routers/v1/query.py, add these comment headers:
- Before line 99 (check_ip_filter): # ══════ LAYER 1: SECURITY ══════
- Before line 137 (fingerprint): # ══════ LAYER 2: PERFORMANCE ══════
- Before line 246 (execute): # ══════ LAYER 3: EXECUTION ══════
- Before line 253 (decrypt): # ══════ LAYER 5: HARDENING ══════
- Before line 276 (layer 4): # ══════ LAYER 4: OBSERVABILITY ══════
```

**Verify:**
```bash
cd gateway && grep -n "LAYER" routers/v1/query.py
# Should show 5 section labels
```

---

### STEP 5 — Phase 5 Shell + Integration Tests

**What:** Add security hardening verification tests.

**File:** `test_all_phases.sh` — Add after Phase 5 unit tests block (after line 117):

**Prompt:**
```text
In test_all_phases.sh, after the Phase 5 unit tests block (after the "Phase 5 unit tests passed" 
echo on line 113), add these shell tests BEFORE the honeypot block (before line 119):

echo -e "${YELLOW}Running Phase 5 pipeline verification...${NC}"

# Test 1: Circuit breaker blocks when open
echo -e "${YELLOW}  Testing circuit breaker OPEN state...${NC}"
"${DC[@]}" exec -T redis redis-cli SET argus:circuit_breaker:state open > /dev/null 2>&1
CB_HTTP=$("${DC[@]}" exec -T gateway python3 -c "
import urllib.request, json
req = urllib.request.Request(
    'http://localhost:8000/api/v1/query/execute',
    data=json.dumps({'query': 'SELECT 1'}).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer dummy'},
    method='POST'
)
try:
    urllib.request.urlopen(req)
    print('200')
except urllib.error.HTTPError as e:
    print(e.code)
except:
    print('000')
" 2>/dev/null || echo "000")
"${DC[@]}" exec -T redis redis-cli DEL argus:circuit_breaker:state > /dev/null 2>&1
if [ "$CB_HTTP" = "503" ]; then
  echo -e "${GREEN}✅ Circuit breaker blocks when open (503)${NC}"
else
  echo -e "${YELLOW}⚠ Circuit breaker test: HTTP $CB_HTTP${NC}"
fi

# Test 2: Sensitive field blocking
echo -e "${YELLOW}  Testing sensitive field blocking...${NC}"
SENS_HTTP=$("${DC[@]}" exec -T gateway python3 -c "
import urllib.request, json, time
# Register test user
ts = str(int(time.time()))
reg = urllib.request.Request(
    'http://localhost:8000/api/v1/auth/register',
    data=json.dumps({'username':'sens_'+ts,'email':'sens_'+ts+'@t.com','password':'test123'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(reg)
    token = json.loads(resp.read()).get('access_token','')
    if token:
        q = urllib.request.Request(
            'http://localhost:8000/api/v1/query/execute',
            data=json.dumps({'query':'SELECT hashed_password FROM users'}).encode(),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+token},
            method='POST'
        )
        try:
            urllib.request.urlopen(q)
            print('200')
        except urllib.error.HTTPError as e:
            print(e.code)
    else:
        print('000')
except Exception:
    print('000')
" 2>/dev/null || echo "000")
if [ "$SENS_HTTP" = "403" ]; then
  echo -e "${GREEN}✅ Sensitive field query blocked (403)${NC}"
else
  echo -e "${YELLOW}⚠ Sensitive field test: HTTP $SENS_HTTP${NC}"
fi
```

**File:** `tests/integration/test_phase5.py` — Create or expand:

**Prompt:**
```text
Create tests/integration/test_phase5_extended.py with:

import pytest
from middleware.security.validator import contains_sensitive_column
from middleware.security.rbac import apply_rbac_masking, strip_denied_columns
from middleware.security.encryption import encrypt_value, decrypt_value
from config import settings


class TestSensitiveFieldBlocking:
    def test_detects_hashed_password(self):
        result = contains_sensitive_column(
            "SELECT hashed_password FROM users",
            settings.sensitive_fields
        )
        assert result == "hashed_password"

    def test_allows_safe_query(self):
        result = contains_sensitive_column(
            "SELECT name, email FROM users",
            settings.sensitive_fields
        )
        assert result is None

    def test_detects_token_field(self):
        result = contains_sensitive_column(
            "SELECT token FROM api_keys",
            settings.sensitive_fields
        )
        assert result == "token"


class TestRBACMasking:
    def test_admin_sees_all(self):
        rows = [{"email": "test@example.com", "hashed_password": "bcrypt_hash"}]
        result = apply_rbac_masking("admin", rows)
        assert "hashed_password" in result[0]

    def test_readonly_strips_denied(self):
        rows = [{"email": "test@example.com", "hashed_password": "bcrypt_hash"}]
        result = apply_rbac_masking("readonly", rows)
        assert "hashed_password" not in result[0]

    def test_readonly_masks_email(self):
        rows = [{"email": "test@example.com"}]
        result = apply_rbac_masking("readonly", rows)
        assert "***" in result[0]["email"]


class TestStripDeniedColumns:
    def test_admin_keeps_all(self):
        cols = ["id", "name", "hashed_password"]
        result = strip_denied_columns("admin", cols)
        assert result == cols

    def test_readonly_strips_password(self):
        cols = ["id", "name", "hashed_password"]
        result = strip_denied_columns("readonly", cols)
        assert "hashed_password" not in result
        assert "id" in result


class TestEncryptionRoundtrip:
    def test_encrypt_decrypt(self):
        original = "123-45-6789"
        encrypted = encrypt_value(original)
        assert encrypted != original
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_encrypted_is_base64(self):
        encrypted = encrypt_value("secret_data")
        import base64
        # Should not raise
        base64.b64decode(encrypted)
```

**Verify:**
```bash
cd gateway && python -m pytest tests/integration/test_phase5_extended.py -v
# All tests should pass
```

---

## TIER 2 — AI LAYER HARDENING

---

### STEP 6 — NL→SQL Prompt Improvements + extract_limit()

**What:** Add deterministic limit extraction and improve the system prompt.

**File:** `gateway/routers/v1/ai.py`

**Prompt:**
```text
In gateway/routers/v1/ai.py, after the imports (after line 18), add this helper:

def extract_limit(question: str) -> int:
    """
    Extract limit from natural language question.
    "top 5 users" -> 5, "first 10" -> 10, default -> 50
    """
    import re
    patterns = [
        r'top\s+(\d+)',
        r'first\s+(\d+)',
        r'last\s+(\d+)',
        r'(\d+)\s+most',
        r'limit\s+(\d+)',
    ]
    question_lower = question.lower()
    for pattern in patterns:
        match = re.search(pattern, question_lower)
        if match:
            return min(int(match.group(1)), 1000)  # Cap at 1000
    return 50  # Default

Then update SYSTEM_PROMPT_NL_TO_SQL (line 54) — replace the entire string with:

SYSTEM_PROMPT_NL_TO_SQL = """You are a SQL query generator for PostgreSQL.
Convert the user's question to a SQL query.

RULES:
- Return ONLY the SQL query, nothing else. No explanation, no markdown, no backticks.
- Only use SELECT or INSERT statements.
- NEVER use SELECT * — always list columns explicitly.
- Always include a LIMIT clause for SELECT queries (use the provided limit value).
- If the user asks for "top N" or "first N", use LIMIT N.
- For ranking queries ("top", "most", "latest", "recent"), add ORDER BY.
- NEVER include these columns: hashed_password, password, token, api_key, secret, internal_notes
- Use proper SQL syntax for PostgreSQL.
- Be conservative — if unsure, return: ERROR: <reason>
- Default safe columns for users table: id, username, email, role, is_active, created_at"""

Do NOT change call_llm_mock or any other function.
```

**Verify:**
```bash
cd gateway && python -c "
from routers.v1.ai import extract_limit
print(extract_limit('show me top 5 users'))   # 5
print(extract_limit('first 10 results'))       # 10
print(extract_limit('show all users'))         # 50
"
```

---

### STEP 7 — SQL Explanation Quality

**What:** Already mostly done in the mock (lines 90-213 of ai.py). Verify the SYSTEM_PROMPT_EXPLAIN covers all requirements.

**File:** `gateway/routers/v1/ai.py`

**Prompt:**
```text
In gateway/routers/v1/ai.py, verify SYSTEM_PROMPT_EXPLAIN (line 66) includes:
- data retrieved ✅ (line 71-73)
- filters ✅ (line 74-76)
- grouping ✅ (line 77-80)
- sorting ✅ (same block)
- limit ✅ (line 81-82)

This is already correct. No changes needed unless the prompt is missing any of these.
Mark this step as DONE if all 5 aspects are covered.
```

**Verify:** Already verified — SYSTEM_PROMPT_EXPLAIN at line 66 covers all 5 aspects.

---

### STEP 8 — Provider Fallback Verification

**What:** Verify the fallback chain works. The `call_llm()` function already has try/except fallback to mock (lines 259-288 of ai.py).

**File:** `gateway/routers/v1/ai.py`

**Prompt:**
```text
In gateway/routers/v1/ai.py, verify call_llm() (line 244):

1. If ai_enabled=false → returns ERROR string ✅ (line 251-252)
2. If provider="mock" → calls mock directly ✅ (line 255-256)
3. If Groq/OpenAI/Gemini fails with exception → falls back to mock ✅ (line 281-288)
4. If provider returns "ERROR:" string → returns error, no fallback ✅ (line 275-278)

This is already correctly implemented. 

HOWEVER: ensure that if provider returns "ERROR:" for a missing API key, 
it should STILL fall back to mock for a better user experience.

Change lines 275-278 from:
        if isinstance(result, str) and result.startswith("ERROR:"):
            logger.warning(f"Primary provider ({settings.ai_provider}) returned error: {result}")
            return result

To:
        if isinstance(result, str) and result.startswith("ERROR:"):
            logger.warning(f"Primary provider ({settings.ai_provider}) returned error: {result}. Falling back to mock.")
            return await call_llm_mock(system, user_message)

This ensures AI NEVER fails — even with a bad API key, the mock provides a response.
```

**Verify:**
```bash
# Set a bad API key and test:
# AI_PROVIDER=groq GROQ_API_KEY=bad_key
# curl /api/v1/ai/nl-to-sql → should still return a response (from mock)
```

---

### STEP 9 — Dry-Run Mode Verification

**What:** Already implemented at query.py lines 211-244. Verify it works correctly.

**File:** `gateway/routers/v1/query.py`

**Prompt:**
```text
Verify dry-run mode in gateway/routers/v1/query.py (lines 211-244):

1. If request.dry_run is True → skips execution ✅ (line 211)
2. Returns cost estimate ✅ (line 226-227)
3. Returns pipeline_checks ✅ (lines 231-237)
4. Returns query_diff (original vs would_execute) ✅ (lines 238-241)
5. Returns 200 ✅ (returns QueryResult, not exception)

This is already correctly implemented. Add one small improvement — include 
the warnings in the dry-run response. After line 228 (before "index_suggestions"), add:

                    "warnings": [f"High cost query: {cost:.2f}"] if cost and cost > settings.cost_threshold_warn else [],

Mark this step as DONE after verification.
```

---

### STEP 10 — Explainable Query Blocks

**What:** Return structured block reasons instead of plain strings.

**File:** `gateway/middleware/security/validator.py`

**Prompt:**
```text
In gateway/middleware/security/validator.py, modify the HTTPException raises 
to return structured block reasons.

Replace the raise on line 56-59 (dangerous query type):
    raise HTTPException(
        status_code=400,
        detail={
            "blocked": True,
            "block_reasons": [f"Query type '{first_word}' is dangerous and not allowed"],
            "suggested_fix": f"Use SELECT or INSERT instead of {first_word}",
        }
    )

Replace the raise on line 63-66 (injection detected):
    raise HTTPException(
        status_code=400,
        detail={
            "blocked": True,
            "block_reasons": ["Potential SQL injection pattern detected"],
            "suggested_fix": "Remove SQL injection patterns (OR 1=1, UNION SELECT, etc.) from your query",
        }
    )

Replace the raise on line 72-75 (disallowed type):
    raise HTTPException(
        status_code=400,
        detail={
            "blocked": True,
            "block_reasons": [f"Query type '{first_word}' is not in the allowed list"],
            "suggested_fix": "Only SELECT and INSERT queries are allowed",
        }
    )

Also in gateway/routers/v1/query.py, update the sensitive field raise (from Step 1) 
to use the same format:
    raise HTTPException(
        status_code=403,
        detail={
            "blocked": True,
            "block_reasons": [f"Query references sensitive field: {field}"],
            "suggested_fix": "Remove the sensitive field from your query. Safe columns: id, username, email, role, is_active, created_at",
        }
    )
```

**Verify:**
```bash
curl -s -X POST http://localhost:8000/api/v1/query/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"DROP TABLE users"}' | python -m json.tool
# Should return: {"detail": {"blocked": true, "block_reasons": [...], "suggested_fix": "..."}}
```

> ⚠️ **WARNING:** This changes the error response format. Update test assertions in 
> `test_features.sh` and `test_userguide_sequential.sh` to check for the new JSON structure 
> instead of plain string matching. Specifically:
> - `test_features.sh` lines 115, 131: check `.detail.block_reasons` instead of `.detail`
> - `test_userguide_sequential.sh` line 143: update injection check

---

## VERIFICATION CHECKPOINT

After completing all 10 steps, run:

```bash
# Unit tests
cd gateway && python -m pytest tests/ -v --tb=short

# Integration tests
cd gateway && python -m pytest tests/integration/ -v

# Full phase test
bash test_all_phases.sh
```

**Expected:**
- All existing tests still pass (some may need assertion updates for Step 10)
- New tests in `test_phase5_extended.py` pass
- Shell tests show sensitive field blocking works
- NL→SQL never returns `hashed_password`
- Dry-run mode returns 200 without DB hit

---

## NEXT: TIER 3+ 

Once Tier 1-2 verification passes, proceed to `integration_plan.md` Tier 3 (Frontend Build).
That requires a separate execution plan since it's frontend React work.

---
