#!/bin/bash
# Run Phase 1 -> Phase 2 -> Phase 3 verification in sequence efficiently.
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

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   SIQG Full Phase Test Runner${NC}"
echo -e "${BLUE}   (Phase 1 -> Phase 2 -> Phase 3)${NC}"
echo -e "${BLUE}========================================${NC}\n"

if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}❌ Docker not found${NC}"
  exit 1
fi
if ! command -v docker-compose >/dev/null 2>&1; then
  echo -e "${RED}❌ Docker Compose not found${NC}"
  exit 1
fi

echo -e "${YELLOW}Starting services once...${NC}"
if ! docker-compose up -d --build --remove-orphans; then
  echo -e "${RED}❌ Failed to start services${NC}"
  exit 1
fi

echo -e "${YELLOW}Waiting 30s for services to be fully ready...${NC}"
sleep 30

# Initialize gateway if missing pytest (same as test_phase1_phase2.sh does)
if ! docker-compose exec -T gateway sh -c 'python -m pytest --version >/dev/null 2>&1'; then
    echo -e "${YELLOW}pytest missing in gateway container, installing...${NC}"
    docker-compose exec -T gateway sh -c 'pip install --no-cache-dir pytest pytest-asyncio pytest-cov >/dev/null'
fi

echo -e "\n${YELLOW}Running Unit Tests...${NC}"
docker-compose exec -T gateway sh -c 'cd /app && python -m pytest tests/ -v --tb=short 2>&1' || true

echo -e "\n${YELLOW}Running Phase 1 checks...${NC}"
if bash ./test_features.sh phase1; then
  PHASE1_STATUS=0
  echo -e "${GREEN}✅ Phase 1 passed${NC}\n"
else
  PHASE1_STATUS=1
  echo -e "${RED}❌ Phase 1 failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 2 checks...${NC}"
docker-compose exec -T redis redis-cli FLUSHALL >/dev/null 2>&1 || true
if bash ./test_features.sh phase2; then
  PHASE2_STATUS=0
  echo -e "${GREEN}✅ Phase 2 passed${NC}\n"
else
  PHASE2_STATUS=1
  echo -e "${RED}❌ Phase 2 failed${NC}\n"
fi

echo -e "${YELLOW}Running Phase 3 checks...${NC}"
docker-compose exec -T redis redis-cli FLUSHALL >/dev/null 2>&1 || true
if bash ./test_features.sh phase3; then
  PHASE3_STATUS=0
  echo -e "${GREEN}✅ Phase 3 passed${NC}\n"
else
  PHASE3_STATUS=1
  echo -e "${RED}❌ Phase 3 failed${NC}\n"
fi

echo -e "${YELLOW}Final cleanup...${NC}"
docker-compose down -v >/dev/null 2>&1 || true

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}              Final Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ $PHASE1_STATUS -eq 0 ]; then
  echo -e "Phase 1: ${GREEN}PASS${NC}"
else
  echo -e "Phase 1: ${RED}FAIL${NC}"
fi

if [ $PHASE2_STATUS -eq 0 ]; then
  echo -e "Phase 2: ${GREEN}PASS${NC}"
else
  echo -e "Phase 2: ${RED}FAIL${NC}"
fi

if [ $PHASE3_STATUS -eq 0 ]; then
  echo -e "Phase 3: ${GREEN}PASS${NC}"
else
  echo -e "Phase 3: ${RED}FAIL${NC}"
fi

TOTAL_FAILS=$((PHASE1_STATUS + PHASE2_STATUS + PHASE3_STATUS))
echo ""
if [ $TOTAL_FAILS -eq 0 ]; then
  echo -e "${GREEN}✅ All phases passed${NC}"
  exit 0
fi

echo -e "${RED}❌ ${TOTAL_FAILS} phase(s) failed${NC}"
exit 1
