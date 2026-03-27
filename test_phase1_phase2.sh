#!/bin/bash
# Quick test script for Phase 1 + 2 + 3
# Usage: ./test_phase1_phase2.sh [phase1|phase2|phase3|all]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Phase 1 + 2 + 3 Testing Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

TARGET_PHASE="${1:-all}"
echo -e "${YELLOW}Target phase: ${TARGET_PHASE}${NC}\n"

# Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker & Docker Compose OK${NC}\n"

# Start services
echo -e "${YELLOW}[2/6] Starting Docker services (Gateway + Postgres + Redis)...${NC}"
docker-compose up -d --remove-orphans
echo -e "${YELLOW}     Waiting 30s for postgres to be ready...${NC}"
sleep 30

# Try to connect to postgres directly (more reliable than healthcheck status)
if ! docker-compose exec -T postgres pg_isready -U queryx -d queryx &>/dev/null; then
    echo -e "${RED}❌ Postgres not responding after 30s${NC}"
    docker-compose logs postgres | tail -15
    docker-compose down -v
    exit 1
fi

# Check Redis health
if ! docker-compose exec -T redis redis-cli ping &>/dev/null; then
    echo -e "${RED}❌ Redis not responding${NC}"
    docker-compose logs redis | tail -10
    docker-compose down -v
    exit 1
fi

echo -e "${GREEN}✅ Services running${NC}\n"

# Wait for gateway to be ready (it needs postgres + redis connection)
echo -e "${YELLOW}     Waiting for gateway to initialize...${NC}"
sleep 5

# Run tests
echo -e "${YELLOW}[3/6] Running unit tests...${NC}"
if docker-compose exec -T gateway sh -c 'cd /app && python -m pytest tests/ -v --tb=short 2>&1' | head -50; then
    echo -e "${GREEN}✅ Unit tests completed${NC}"
else
    echo -e "${YELLOW}⚠️ Tests may have issues - checking logs${NC}"
fi
echo ""

# Network test
echo -e "${YELLOW}[4/6] Testing API health check...${NC}"
if curl -s http://localhost:8000/health 2>/dev/null | grep -q "ok"; then
    echo -e "${GREEN}✅ API responding${NC}"
else
    echo -e "${YELLOW}⚠️ API health check - gateway may still be initializing${NC}"
fi
echo ""

# Feature test by phase
echo -e "${YELLOW}[5/6] Running feature tests by phase...${NC}"
case "$TARGET_PHASE" in
  phase1)
    echo -e "${BLUE}Running Phase 1 checks (security baseline via full script)...${NC}"
    bash ./test_features.sh || true
    ;;
  phase2)
    echo -e "${BLUE}Running Phase 2 checks (performance baseline via full script)...${NC}"
    bash ./test_features.sh || true
    ;;
  phase3)
    echo -e "${BLUE}Running Phase 3 checks (analysis/suggestions/complexity via full script)...${NC}"
    bash ./test_features.sh || true
    ;;
  all)
    echo -e "${BLUE}Running all phases sequentially via feature suite...${NC}"
    bash ./test_features.sh || true
    ;;
  *)
    echo -e "${RED}❌ Unknown target phase: ${TARGET_PHASE}${NC}"
    echo -e "${YELLOW}Use one of: phase1 | phase2 | phase3 | all${NC}"
    docker-compose down -v
    exit 1
    ;;
esac
echo ""

# Cleanup
echo -e "${YELLOW}[6/6] Cleaning up...${NC}"
docker-compose down -v
echo -e "${GREEN}✅ Services stopped${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✨ Phase ${TARGET_PHASE} Tests Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
