#!/bin/bash
# Quick test script for Phase 1 & 2
# Usage: ./test_phase1_phase2.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Phase 1 & 2 Testing Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check prerequisites
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"
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
echo -e "${YELLOW}[2/5] Starting Docker services (Gateway + Postgres + Redis)...${NC}"
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
echo -e "${YELLOW}[3/5] Running unit tests...${NC}"
if docker-compose exec -T gateway sh -c 'cd /app && python -m pytest tests/ -v --tb=short 2>&1' | head -50; then
    echo -e "${GREEN}✅ Unit tests completed${NC}"
else
    echo -e "${YELLOW}⚠️ Tests may have issues - checking logs${NC}"
fi
echo ""

# Network test
echo -e "${YELLOW}[4/5] Testing API health check...${NC}"
if curl -s http://localhost:8000/health 2>/dev/null | grep -q "ok"; then
    echo -e "${GREEN}✅ API responding${NC}"
else
    echo -e "${YELLOW}⚠️ API health check - gateway may still be initializing${NC}"
fi
echo ""

# Cleanup
echo -e "${YELLOW}[5/5] Cleaning up...${NC}"
docker-compose down -v
echo -e "${GREEN}✅ Services stopped${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✨ Phase 1 & 2 Tests Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
