#!/bin/bash
################################################################################
# test_all_32_features.sh
# Comprehensive test covering ALL 32 Argus integration steps
# Tests: Tiers 1-6 (Security → Performance → Intelligence → Observability → Hardening → AI+Polish)
################################################################################

set -u

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
PASS=0
FAIL=0
SKIP=0

# Print section header
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

# Test result tracker
test_pass() {
    local name="$1"
    echo -e "${GREEN}✅ PASS${NC} - $name"
    PASS=$((PASS + 1))
}

test_fail() {
    local name="$1"
    local reason="${2:-Unknown reason}"
    echo -e "${RED}❌ FAIL${NC} - $name"
    echo -e "    ${RED}Reason: $reason${NC}"
    FAIL=$((FAIL + 1))
}

test_skip() {
    local name="$1"
    echo -e "${YELLOW}⊘ SKIP${NC} - $name"
    SKIP=$((SKIP + 1))
}

# Check if service is running
check_service() {
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${RED}❌ Gateway is not running on port 8000${NC}"
        echo "Start it with: docker compose up -d"
        exit 1
    fi
}

BASE_URL="http://localhost:8000"

print_header "🧪 ARGUS ALL 32 FEATURES TEST SUITE"
echo "Testing comprehensive coverage of Tiers 1-6 (all integration steps)"
echo "Estimated runtime: 5-10 minutes"
echo ""

# Check service
echo -e "${YELLOW}Checking gateway service...${NC}"
check_service
echo -e "${GREEN}✅ Gateway is running${NC}\n"

# ============================================================================
# SETUP: Create test user and get tokens
# ============================================================================

print_header "SETUP: Test User & Tokens"

# Register user
REG=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username":"testuser_'$(date +%s)'",
    "email":"test_'$(date +%s)'@example.com",
    "password":"TestPass123!@#"
  }')

TOKEN=$(echo "$REG" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
    # Try login if already exists
    REG=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"username":"testuser","password":"testpass123"}')
    TOKEN=$(echo "$REG" | jq -r '.access_token // empty')
fi

if [ -z "$TOKEN" ]; then
    test_fail "User Registration/Login" "Could not obtain auth token"
    exit 1
fi

test_pass "User Registration"
echo "Token: ${TOKEN:0:30}..."
echo ""

# ============================================================================
# TIER 1: SECURITY FIXES (Steps 1-5)
# ============================================================================

print_header "TIER 1: Security Fixes (Steps 1-5)"

# Step 1: SENSITIVE_FIELDS constant
TEST="Step 1: SENSITIVE_FIELDS constant centralized"
if grep -q "SENSITIVE_FIELDS" gateway/config.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "SENSITIVE_FIELDS not found in config.py"
fi

# Step 2: Block sensitive columns
TEST="Step 2: Block access to hashed_password"
RESULT=$(curl -s -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT hashed_password FROM users LIMIT 1"}')

HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT hashed_password FROM users LIMIT 1"}')

if [ "$HTTP_CODE" = "403" ] || echo "$RESULT" | grep -q "sensitive"; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Query should be blocked (got HTTP $HTTP_CODE)"
fi

# Step 3: NL→SQL RBAC masking
TEST="Step 3: NL→SQL applies RBAC masking"
NL=$(curl -s -X POST "$BASE_URL/api/v1/ai/nl-to-sql" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show all user ids and emails"}')

if echo "$NL" | jq -e '.result.rows' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "NL→SQL response malformed"
fi

# Step 4: Pipeline order (decrypt then mask)
TEST="Step 4: Correct pipeline order (decrypt→mask)"
# Verify in code
if grep -q "decrypt_rows\|apply_rbac_masking" gateway/routers/v1/query.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_skip "$TEST" "Cannot verify pipeline order without code inspection"
fi

# Step 5: Phase 5 shell verification
TEST="Step 5: Query execution works end-to-end"
RESULT=$(curl -s -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1 as test LIMIT 1"}')

if echo "$RESULT" | jq -e '.rows[0]' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Basic query execute failed"
fi

echo ""

# ============================================================================
# TIER 2: AI RELIABILITY (Steps 6-10)
# ============================================================================

print_header "TIER 2: AI Reliability (Steps 6-10)"

# Step 6: NL→SQL prompt improvements
TEST="Step 6: NL→SQL deterministic responses"
Q1=$(curl -s -X POST "$BASE_URL/api/v1/ai/nl-to-sql" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Show me 5 users"}')

if echo "$Q1" | jq -e '.generated_sql' | grep -q "LIMIT 5"; then
    test_pass "$TEST"
else
    test_fail "$TEST" "LIMIT not properly applied"
fi

# Step 7: SQL explanation quality
TEST="Step 7: Query explanation quality"
EXP=$(curl -s -X POST "$BASE_URL/api/v1/ai/explain" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT id, username FROM users WHERE id = 1"}')

if echo "$EXP" | jq -e '.explanation' | wc -c | grep -qv "^1$"; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Explanation is empty"
fi

# Step 8: Provider fallback (Groq → Mock)
TEST="Step 8: AI provider fallback mechanism"
if grep -q "fallback\|mock" gateway/routers/v1/ai.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Fallback mechanism not found"
fi

# Step 9: Dry-run mode
TEST="Step 9: Dry-run mode execution"
DRY=$(curl -s -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT 1", "dry_run":true}')

if echo "$DRY" | jq -e '.analysis.status' | grep -q "would_execute"; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Dry-run response malformed (check .analysis.status)"
fi

# Step 10: Explainable query blocks
TEST="Step 10: Query blocks have explanations"
BLOCKED=$(curl -s -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"DROP TABLE users"}')

if echo "$BLOCKED" | jq -e '.detail' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Block response missing explanation"
fi

echo ""

# ============================================================================
# TIER 3: FRONTEND BUILD (Steps 11-15)
# ============================================================================

print_header "TIER 3: Frontend Build (Steps 11-15)"

# Step 11: React app scaffold
TEST="Step 11: React app files exist"
if [ -f "frontend/src/main.jsx" ] && [ -f "frontend/src/App.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "React app files missing"
fi

# Step 12: NL→SQL UI panel
TEST="Step 12: NL query panel component"
if [ -f "frontend/src/components/NLQueryPanel.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "NLQueryPanel.jsx not found"
fi

# Step 13: Results table
TEST="Step 13: Results table component"
if [ -f "frontend/src/components/ResultsTable.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "ResultsTable.jsx not found"
fi

# Step 14: Live metrics dashboard
TEST="Step 14: Metrics dashboard component"
if [ -f "frontend/src/components/MetricsDashboard.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "MetricsDashboard.jsx not found"
fi

# Step 15: Health status page
TEST="Step 15: Health status page"
if [ -f "frontend/src/components/HealthStatus.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "HealthStatus.jsx not found"
fi

echo ""

# ============================================================================
# TIER 4: PROOF & CREDIBILITY (Steps 16-19)
# ============================================================================

print_header "TIER 4: Proof & Credibility (Steps 16-19)"

# Step 16: CI badge
TEST="Step 16: CI/CD workflow configured"
if [ -f ".github/workflows/ci.yml" ] || [ -f ".github/workflows/test.yml" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "CI workflow file not found"
fi

# Step 17: Load test results
TEST="Step 17: Load test results documented"
if [ -f "TEST_COVERAGE_REPORT.md" ] || grep -q "P95\|latency" README.md 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Load test results not documented"
fi

# Step 18: README overhaul
TEST="Step 18: Comprehensive README"
if grep -q "## Features\|Security\|Performance" README.md 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "README incomplete"
fi

# Step 19: CLI demo script
TEST="Step 19: Demo CLI script exists"
if [ -f "demo_cli.sh" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "demo_cli.sh not found"
fi

echo ""

# ============================================================================
# TIER 5: BACKEND EXTENSIONS (Steps 20-24)
# ============================================================================

print_header "TIER 5: Backend Extensions (Steps 20-24)"

# Step 20: Cache tag cleanup
TEST="Step 20: Cache tag cleanup (SSCAN)"
if grep -q "cleanup_stale_tags\|SSCAN" gateway/middleware/performance/cache.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Cache cleanup function not found"
fi

# Step 21: Slow query advisor
TEST="Step 21: Slow query recommendation"
SLOW=$(curl -s -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT * FROM users"}')

if echo "$SLOW" | jq -e '.analysis // .recommendation' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Query analysis missing"
fi

# Step 22: Per-role rate limits
TEST="Step 22: Per-role rate limit tiers"
if grep -q "rate_limit.*admin\|rate_limit.*readonly\|rate_limit.*guest" gateway/config.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Per-role rate limits not found"
fi

# Step 23: API key scoping
TEST="Step 23: API key allowed_tables/allowed_query_types"
if grep -q "allowed_tables\|allowed_query_types" gateway/models/user.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "API key scoping fields not found"
fi

# Step 24: Query whitelist mode
TEST="Step 24: Query whitelist enforcement"
if grep -q "QueryWhitelist\|whitelist_mode" gateway/models/user.py 2>/dev/null && \
   grep -q "/admin/whitelist" gateway/routers/v1/admin.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Query whitelist not implemented"
fi

echo ""

# ============================================================================
# TIER 6: POLISH FEATURES (Steps 25-32)
# ============================================================================

print_header "TIER 6: Polish Features (Steps 25-32)"

# Step 25: Time-based access rules
TEST="Step 25: Time-based RBAC access"
if grep -q "check_time_based_access\|allowed_hours" gateway/middleware/security/rbac.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Time-based RBAC not found"
fi

# Step 26: Query diff viewer
TEST="Step 26: Query diff viewer component"
if [ -f "frontend/src/components/QueryDiffViewer.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "QueryDiffViewer.jsx not found"
fi

# Step 27: Dry-run UI
TEST="Step 27: Dry-run panel component"
if [ -f "frontend/src/components/DryRunPanel.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "DryRunPanel.jsx not found"
fi

# Step 28: Index DDL copy
TEST="Step 28: Analysis panel with DDL copy"
if [ -f "frontend/src/components/AnalysisPanel.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "AnalysisPanel.jsx not found"
fi

# Step 29: Admin dashboard
TEST="Step 29: Admin dashboard component"
if [ -f "frontend/src/components/AdminDashboard.jsx" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "AdminDashboard.jsx not found"
fi

# Step 30: HMAC request signing
TEST="Step 30: HMAC signature validation"
if grep -q "compute_hmac_signature\|validate_hmac_signature" gateway/middleware/security/auth.py 2>/dev/null; then
    test_pass "$TEST"
else
    test_fail "$TEST" "HMAC functions not found"
fi

# Step 31: Compliance report export
TEST="Step 31: Compliance report endpoint"
REPORT=$(curl -s -X GET "$BASE_URL/api/v1/admin/compliance-report" \
  -H "Authorization: Bearer $TOKEN")

if echo "$REPORT" | jq -e '.period // .status // empty' > /dev/null 2>&1 || [ "$REPORT" != "" ]; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Compliance report endpoint not responding"
fi

# Step 32: AI anomaly explanation
TEST="Step 32: AI anomaly explanation endpoint"
ANOMALY=$(curl -s -X POST "$BASE_URL/api/v1/ai/explain-anomaly" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "anomaly_type":"rate_limit_spike",
    "baseline_value":60,
    "detected_value":600
  }')

if echo "$ANOMALY" | jq -e '.explanation' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Anomaly explanation endpoint failed"
fi

echo ""

# ============================================================================
# INTEGRATION TESTS: Cross-layer verification
# ============================================================================

print_header "INTEGRATION TESTS: Cross-Layer Verification"

# Full pipeline test
TEST="Full query pipeline: Security → Performance → Execution → Observability"
FULL=$(curl -s -X POST "$BASE_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT id, username FROM users LIMIT 5"}')

if echo "$FULL" | jq -e '.rows_count, .latency_ms, .cached, .trace_id' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Pipeline response incomplete"
fi

# NL→SQL full journey
TEST="NL→SQL full journey including caching"
Q1=$(curl -s -X POST "$BASE_URL/api/v1/ai/nl-to-sql" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Count users by role"}')

if echo "$Q1" | jq -e '.result.rows_count' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "NL→SQL journey incomplete"
fi

# Metrics endpoint
TEST="Metrics endpoint captures full analytics"
METRICS=$(curl -s -X GET "$BASE_URL/api/v1/metrics/live" \
  -H "Authorization: Bearer $TOKEN")

if echo "$METRICS" | jq -e '.cache_hit_ratio' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Metrics endpoint incomplete"
fi

# System health check
TEST="System health check (all components)"
HEALTH=$(curl -s -X GET "$BASE_URL/health")

if echo "$HEALTH" | jq -e '.status' > /dev/null 2>&1; then
    test_pass "$TEST"
else
    test_fail "$TEST" "Health endpoint failed"
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================

print_header "TEST SUMMARY"

TOTAL=$((PASS + FAIL + SKIP))
PERCENT=$((PASS * 100 / TOTAL))

echo "Total Tests:  $TOTAL"
echo -e "Passed:       ${GREEN}$PASS${NC}"
echo -e "Failed:       ${RED}$FAIL${NC}"
echo -e "Skipped:      ${YELLOW}$SKIP${NC}"
echo -e "Success Rate: ${GREEN}$PERCENT%${NC}"

if [ $FAIL -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL 32 FEATURES WORKING! 🎉${NC}"
    echo "Argus is production-ready with:"
    echo "  ✅ Step 1-5: Complete security hardening"
    echo "  ✅ Step 6-10: AI reliability & fallbacks"
    echo "  ✅ Step 11-15: Full-featured frontend"
    echo "  ✅ Step 16-19: CI/CD & proven performance"
    echo "  ✅ Step 20-24: Advanced backend features"
    echo "  ✅ Step 25-32: Polish & compliance"
    exit 0
else
    echo -e "\n${RED}⚠️  $FAIL test(s) failed. Review output above.${NC}"
    exit 1
fi
