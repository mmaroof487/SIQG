# Argus API Guide

## Base URL
All API requests should be directed to `/api/v1`

## Authentication
Argus uses JWT Bearer tokens for authentication.
Include the token in the Authorization header:
`Authorization: Bearer <token>`

## Core Endpoints

### 1. `POST /auth/login`
Authenticate and retrieve a JWT token.
**Payload:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

### 2. `POST /query/execute`
Execute a SQL query against a registered database connection.
**Payload:**
```json
{
  "connection_id": "uuid-here",
  "query": "SELECT * FROM users",
  "limit": 100
}
```

### 3. `POST /ai/nl-to-sql`
Translate natural language into SQL.
**Payload:**
```json
{
  "connection_id": "uuid-here",
  "question": "Show me the top 5 users created this week"
}
```

## Admin Endpoints
Require the `admin` role.
- `GET /admin/cache/stats` - Redis cache hit/miss statistics.
- `GET /connections/{connection_id}/migration-status` - Check background re-encryption status.

## Health Probes
- `GET /health/live` - Application is running.
- `GET /health/ready` - Application is connected to Redis and PostgreSQL.
- `GET /version` - Returns current API version.
