# Deployment Guide

This guide outlines how to deploy the Argus Gateway in a production-like environment using Docker and Docker Compose.

## Prerequisites
- Docker Engine 24.0+
- Docker Compose v2
- PostgreSQL client tools (optional, for manual DB inspection)

## Local / Development Startup
The easiest way to boot the entire stack (Gateway, Frontend, DB Primary, DB Replica, Redis) is via the unified compose file.

```bash
docker compose up --build -d
```

### Health Checks
Docker Compose is configured with internal health checks. The `gateway` container will not accept traffic until both PostgreSQL and Redis report as healthy.

## Environment Variables
The `.env` file (or environment variables passed via CI/CD) configures the runtime behavior.

```env
# Core API
ENVIRONMENT=production
JWT_SECRET=your_super_secret_key_change_me
LOG_LEVEL=INFO

# Databases
DATABASE_URL=postgresql://argus:argus@postgres:5432/argus
REPLICA_URL=postgresql://argus:argus@postgres_replica:5432/argus

# Redis
REDIS_URL=redis://redis:6379/0

# Encryption
MASTER_KEY_PROVIDER=env
MASTER_KEY_ENV_VAR=siqg_master_key_12345678901234567890123456789012

# LLM
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...
```

## Alembic Migrations
When the `gateway` container boots, it runs `entrypoint.sh`. This script automatically applies any pending Alembic migrations before starting the Uvicorn ASGI server.

```bash
alembic upgrade head
```

## Production Recommendations

1. **Reverse Proxy (HTTPS)**: Do not expose Uvicorn directly to the internet. Deploy Argus behind Nginx, HAProxy, or an API Gateway (like AWS API Gateway) to handle TLS termination and HTTPS.
2. **Redis Persistence**: Configure Redis with AOF (Append Only File) to ensure rate limit and circuit breaker states survive container restarts.
3. **Database Credentials**: Replace the default `argus:argus` credentials immediately.
4. **JWT Secrets**: Generate a cryptographically secure 32+ byte key for `JWT_SECRET`.
5. **Horizontal Scaling**: The Argus Gateway is stateless (all state is in Redis/Postgres). You can run multiple instances of the gateway container behind a load balancer.
