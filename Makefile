.PHONY: dev down test test-phase5 test-all load-test shell-gateway shell-db logs restart help

help:
	@echo "Available commands:"
	@echo "  make dev           - Start all services"
	@echo "  make down          - Stop all services and remove volumes"
	@echo "  make test          - Run pytest unit + integration tests"
	@echo "  make test-phase5   - Run Phase 5 security hardening tests"
	@echo "  make test-all      - Run test_all_phases.sh (full integration)"
	@echo "  make load-test     - Run Locust load tests"
	@echo "  make shell-gateway - Enter gateway container shell"
	@echo "  make shell-db      - Enter postgres psql shell"
	@echo "  make logs          - Follow gateway logs"
	@echo "  make restart       - Restart gateway service"

dev:
	docker compose up --build

down:
	docker compose down -v

test:
	cd gateway && pytest tests/ -v --cov=. --cov-report=term-missing

test-phase5:
	cd gateway && pytest tests/unit/test_encryptor.py tests/unit/test_circuit_breaker.py tests/unit/test_executor.py -v --cov=. --cov-report=term-missing

test-all:
	bash test_all_phases.sh

load-test:
	cd tests/load && locust -f locustfile.py --headless -u 100 -r 10 -t 60s

shell-gateway:
	docker compose exec gateway bash

shell-db:
	docker compose exec postgres psql -U argus -d argus

logs:
	docker compose logs -f gateway

restart:
	docker compose restart gateway
