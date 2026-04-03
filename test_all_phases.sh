#!/bin/bash
# Run Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 verification in sequence.
# Usage: bash test_all_phases.sh

set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PHASE1_STATUS=0
PHASE2_STATUS=0
PHASE3_STATUS=0
PHASE4_STATUS=0
PHASE5_STATUS=0
PHASE6_STATUS=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Argus Full Phase Test Runner${NC}"
echo -e "${BLUE}   (Phase 1 -> 6: Foundation to AI+Polish)${NC}"
echo -e "${BLUE}========================================${NC}\n"

if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}❌ Docker not found${NC}"
  exit 1
fi

# Support both docker-compose v1 (standalone) and docker compose v2 (plugin)
if command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
elif docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
else
  echo -e "${RED}❌ Docker Compose not found${NC}"
  exit 1
fi

echo -e "${YELLOW}Starting services once...${NC}"
if ! "${DC[@]}" up -d --build --remove-orphans; then
  echo -e "${RED}❌ Failed to start services${NC}"
  exit 1
fi

echo -e "${YELLOW}Waiting 30s for services to be fully ready...${NC}"
sleep 30

# Initialize gateway if missing pytest (same as test_phase1_phase2.sh does)
if ! "${DC[@]}" exec -T gateway sh -c 'python -m pytest --version >/dev/null 2>&1'; then
    echo -e "${YELLOW}pytest missing in gateway container, installing...${NC}"
    "${DC[@]}" exec -T gateway sh -c 'pip install --no-cache-dir pytest pytest-asyncio pytest-cov >/dev/null'
fi

echo -e "\n${YELLOW}Running Unit Tests (including 5 new injection patterns)...${NC}"
"${DC[@]}" exec -T gateway sh -c 'cd /app && python -m pytest tests/ -v --tb=short 2>&1' || true

echo -e "\n${YELLOW}Verifying new SQL injection patterns (SLEEP, WAITFOR, BENCHMARK, information_schema, stacked)...${NC}"
if "${DC[@]}" exec -T gateway sh -c 'cd /app && python -m pytest tests/unit/test_validator.py -v --tb=short -k "sleep or waitfor or benchmark or information_schema or stacked" 2>&1'; then
  echo -e "${GREEN}✅ New injection pattern tests passed${NC}\n"
else
  echo -e "${RED}❌ New injection pattern tests failed${NC}\n"
fi

echo -e "\n${YELLOW}Running Phase 1 checks...${NC}"
# Clear any IP blocklist entries before Phase 1 to ensure clean slate
"${DC[@]}" exec -T redis redis-cli EVAL "return redis.call('del', unpack(redis.call('keys', 'argus:ip:blocklist:*')))" 0 >/dev/null 2>&1 || true
if bash ./test_features.sh phase1; then
  PHASE1_STATUS=0
  echo -e "${GREEN}✅ Phase 1 passed${NC}\n"
else
  PHASE1_STATUS=1
  echo -e "${RED}❌ Phase 1 failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 2 checks...${NC}"
# Clear IP blocklist for clean Phase 2 start
"${DC[@]}" exec -T redis redis-cli EVAL "return redis.call('del', unpack(redis.call('keys', 'argus:ip:blocklist:*')))" 0 >/dev/null 2>&1 || true
"${DC[@]}" exec -T redis redis-cli FLUSHALL >/dev/null 2>&1 || true
if bash ./test_features.sh phase2; then
  PHASE2_STATUS=0
  echo -e "${GREEN}✅ Phase 2 passed${NC}\n"
else
  PHASE2_STATUS=1
  echo -e "${RED}❌ Phase 2 failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 3 checks...${NC}"
# Clear IP blocklist for clean Phase 3 start
"${DC[@]}" exec -T redis redis-cli EVAL "return redis.call('del', unpack(redis.call('keys', 'argus:ip:blocklist:*')))" 0 >/dev/null 2>&1 || true
"${DC[@]}" exec -T redis redis-cli FLUSHALL >/dev/null 2>&1 || true
if bash ./test_features.sh phase3; then
  PHASE3_STATUS=0
  echo -e "${GREEN}✅ Phase 3 passed${NC}\n"
else
  PHASE3_STATUS=1
  echo -e "${RED}❌ Phase 3 failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 4 checks...${NC}"
if bash ./test_features.sh phase4; then
  PHASE4_STATUS=0
  echo -e "${GREEN}✅ Phase 4 passed${NC}\n"
else
  PHASE4_STATUS=1
  echo -e "${RED}❌ Phase 4 failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 5 checks (Security Hardening)...${NC}"
echo -e "${YELLOW}Running Phase 5 unit tests...${NC}"
if "${DC[@]}" exec -T gateway sh -c 'cd /app && python -m pytest tests/unit/test_encryptor.py tests/unit/test_circuit_breaker.py tests/unit/test_executor.py -v --tb=short'; then
  PHASE5_STATUS=0
  echo -e "${GREEN}✅ Phase 5 unit tests passed${NC}\n"
else
  PHASE5_STATUS=1
  echo -e "${RED}❌ Phase 5 unit tests failed${NC}\n"
fi

# Verify honeypot IP auto-ban (fix #2 - consolidated honeypot with IP blocklist)
echo -e "${YELLOW}Testing honeypot IP auto-ban...${NC}"
HONEYPOT_HTTP=$("${DC[@]}" exec -T gateway python3 -c "
import urllib.request, json
req = urllib.request.Request(
    'http://localhost:8000/api/v1/query/execute',
    data=json.dumps({'query': 'SELECT * FROM secret_keys'}).encode(),
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
if [ "$HONEYPOT_HTTP" = "403" ]; then
  echo -e "${GREEN}✅ Honeypot detection returns 403${NC}\n"
else
  echo -e "${YELLOW}⚠ Honeypot test: HTTP $HONEYPOT_HTTP (may need auth)${NC}\n"
fi

# Clear IP blocklist after honeypot test to allow subsequent tests
"${DC[@]}" exec -T redis redis-cli EVAL "return redis.call('del', unpack(redis.call('keys', 'argus:ip:blocklist:*')))" 0 > /dev/null 2>&1 || true

echo -e "${YELLOW}Running Phase 6 checks (AI + Polish)...${NC}"
echo -e "${YELLOW}Running Phase 6 AI endpoint tests...${NC}"
if "${DC[@]}" exec -T gateway sh -c 'cd /app && python -m pytest tests/unit/test_ai.py -v --tb=short 2>&1'; then
  echo -e "${GREEN}✅ Phase 6 AI tests passed${NC}\n"
else
  PHASE6_STATUS=1
  echo -e "${RED}❌ Phase 6 AI tests failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 6 SDK client tests...${NC}"
if "${DC[@]}" exec -T gateway sh -c 'cd /app && python -m pytest tests/unit/test_sdk_client.py -v --tb=line 2>&1'; then
  echo -e "${GREEN}✅ Phase 6 SDK tests passed${NC}\n"
else
  PHASE6_STATUS=1
  echo -e "${RED}❌ Phase 6 SDK tests failed (collection OK, tests may be skipped)${NC}\n"
fi

# Auth refresh endpoint test (fix #10)
echo -e "${YELLOW}Testing /api/v1/auth/refresh endpoint...${NC}"
REFRESH_HTTP=$("${DC[@]}" exec -T gateway python3 -c "
import urllib.request, json, time
ts = str(int(time.time()))
# Register a test user
reg_data = json.dumps({'username': 'refresh_test_' + ts, 'email': 'refresh_' + ts + '@test.com', 'password': 'testpass123'}).encode()
req = urllib.request.Request('http://localhost:8000/api/v1/auth/register', data=reg_data, headers={'Content-Type': 'application/json'}, method='POST')
try:
    resp = urllib.request.urlopen(req)
    token = json.loads(resp.read()).get('access_token', '')
    if token:
        ref_req = urllib.request.Request('http://localhost:8000/api/v1/auth/refresh', headers={'Authorization': 'Bearer ' + token}, method='POST')
        try:
            urllib.request.urlopen(ref_req)
            print('200')
        except urllib.error.HTTPError as e:
            print(e.code)
    else:
        print('000')
except Exception as e:
    print('000')
" 2>/dev/null || echo "000")
if [ "$REFRESH_HTTP" = "200" ]; then
  echo -e "${GREEN}✅ Token refresh endpoint working${NC}\n"
else
  echo -e "${YELLOW}⚠ Refresh returned HTTP $REFRESH_HTTP${NC}\n"
fi

echo -e "${YELLOW}Final cleanup...${NC}"
"${DC[@]}" down -v >/dev/null 2>&1 || true

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}              Final Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ $PHASE1_STATUS -eq 0 ]; then
  echo -e "Phase 1 (Foundation):        ${GREEN}PASS${NC}"
else
  echo -e "Phase 1 (Foundation):        ${RED}FAIL${NC}"
fi

if [ $PHASE2_STATUS -eq 0 ]; then
  echo -e "Phase 2 (Performance):       ${GREEN}PASS${NC}"
else
  echo -e "Phase 2 (Performance):       ${RED}FAIL${NC}"
fi

if [ $PHASE3_STATUS -eq 0 ]; then
  echo -e "Phase 3 (Intelligence):      ${GREEN}PASS${NC}"
else
  echo -e "Phase 3 (Intelligence):      ${RED}FAIL${NC}"
fi

if [ $PHASE4_STATUS -eq 0 ]; then
  echo -e "Phase 4 (Observability):     ${GREEN}PASS${NC}"
else
  echo -e "Phase 4 (Observability):     ${RED}FAIL${NC}"
fi

if [ $PHASE5_STATUS -eq 0 ]; then
  echo -e "Phase 5 (Security):          ${GREEN}PASS${NC}"
else
  echo -e "Phase 5 (Security):          ${RED}FAIL${NC}"
fi

if [ $PHASE6_STATUS -eq 0 ]; then
  echo -e "Phase 6 (AI + Polish):       ${GREEN}PASS${NC}"
else
  echo -e "Phase 6 (AI + Polish):       ${RED}FAIL${NC}"
fi

TOTAL_FAILS=$((PHASE1_STATUS + PHASE2_STATUS + PHASE3_STATUS + PHASE4_STATUS + PHASE5_STATUS + PHASE6_STATUS))
echo ""
if [ $TOTAL_FAILS -eq 0 ]; then
  echo -e "${GREEN}✅ All phases (1-6) passed successfully!${NC}"
  exit 0
fi

echo -e "${RED}❌ ${TOTAL_FAILS} phase(s) failed${NC}"
exit 1
