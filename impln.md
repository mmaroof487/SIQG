# SIQG — Phase-wise Implementation Plan

> Deep technical guide for building the Secure Intelligent Query Gateway from scratch.
> Every phase has exact files, exact code patterns, exact commands, and a clear done-condition.

---

## How to Use This Document

- Follow phases in order. Each phase builds on the previous.
- Every phase ends with a **Done Condition** — a specific thing you can run or show to confirm it works.
- Code snippets are patterns, not copy-paste finals. Adapt to your exact config.
- Time estimates assume 4–6 focused hours per day.

---

## Pre-Phase: Environment Setup (Day 0, ~2 hours)

Before writing a single line of gateway code, get your environment stable.

### 1. Install tools

```bash
# Python
python --version   # must be 3.11+
pip install pipenv  # or use venv directly

# Docker
docker --version
docker compose version  # must be v2 (compose, not compose-V1)

# VS Code extensions to install
# - Python (Microsoft)
# - Docker
# - REST Client (for .http files — better than Postman for quick testing)
# - SQLTools + SQLTools PostgreSQL driver
```

### 2. Create project scaffold

```bash
mkdir siqg && cd siqg

# Top-level structure
mkdir -p gateway/middleware/security
mkdir -p gateway/middleware/performance
mkdir -p gateway/middleware/execution
mkdir -p gateway/middleware/observability
mkdir -p gateway/routers/v1
mkdir -p gateway/routers/v2
mkdir -p gateway/models
mkdir -p gateway/utils
mkdir -p frontend/src/components
mkdir -p sdk/siqg
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/load
mkdir -p .github/workflows

touch docker-compose.yml
touch .env.example
touch Makefile
touch README.md
```

### 3. Base docker-compose.yml (grows with each phase)

```yaml
# docker-compose.yml
version: "3.9"

services:
 gateway:
  build: ./gateway
  ports:
   - "8000:8000"
  env_file: .env
  depends_on:
   postgres:
    condition: service_healthy
   redis:
    condition: service_healthy
  volumes:
   - ./gateway:/app
  command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

 postgres:
  image: postgres:15-alpine
  environment:
   POSTGRES_USER: siqg
   POSTGRES_PASSWORD: siqg
   POSTGRES_DB: siqg
  ports:
   - "5432:5432"
  volumes:
   - pg_data:/var/lib/postgresql/data
  healthcheck:
   test: ["CMD-SHELL", "pg_isready -U siqg"]
   interval: 5s
   timeout: 5s
   retries: 5

 postgres_replica:
  image: postgres:15-alpine
  environment:
   POSTGRES_USER: siqg
   POSTGRES_PASSWORD: siqg
   POSTGRES_DB: siqg
  ports:
   - "5433:5432"
  healthcheck:
   test: ["CMD-SHELL", "pg_isready -U siqg"]
   interval: 5s
   timeout: 5s
   retries: 5

 redis:
  image: redis:7-alpine
  ports:
   - "6379:6379"
  healthcheck:
   test: ["CMD", "redis-cli", "ping"]
   interval: 5s
   timeout: 5s
   retries: 5

 frontend:
  build: ./frontend
  ports:
   - "3001:3001"
  depends_on:
   - gateway

volumes:
 pg_data:
```

### 4. Makefile shortcuts

```makefile
# Makefile
dev:
	docker compose up --build

down:
	docker compose down -v

test:
	cd gateway && pytest tests/ -v --cov=. --cov-report=term-missing

load-test:
	cd tests/load && locust -f locustfile.py --headless -u 100 -r 10 -t 60s

shell-gateway:
	docker compose exec gateway bash

shell-db:
	docker compose exec postgres psql -U siqg -d siqg

logs:
	docker compose logs -f gateway

restart:
	docker compose restart gateway
```

### 5. Base .env.example

```env
SECRET_KEY=dev-secret-key-change-in-prod
JWT_EXPIRY_MINUTES=60

DB_PRIMARY_URL=postgresql+asyncpg://siqg:siqg@postgres:5432/siqg
DB_REPLICA_URL=postgresql+asyncpg://siqg:siqg@postgres_replica:5432/siqg
DB_POOL_MIN=5
DB_POOL_MAX=20

REDIS_URL=redis://redis:6379/0
CACHE_DEFAULT_TTL=60

RATE_LIMIT_PER_MINUTE=60
BRUTE_FORCE_MAX_ATTEMPTS=5
BRUTE_FORCE_LOCKOUT_MINUTES=15

ENCRYPTION_KEY=12345678901234567890123456789012
ENCRYPT_COLUMNS=ssn,credit_card

HONEYPOT_TABLES=secret_keys,admin_passwords

QUERY_TIMEOUT_SECONDS=5
AUTO_LIMIT_DEFAULT=1000
COST_THRESHOLD_WARN=1000
COST_THRESHOLD_BLOCK=10000
SLOW_QUERY_THRESHOLD_MS=200
DAILY_BUDGET_DEFAULT=50000

CIRCUIT_FAILURE_THRESHOLD=5
CIRCUIT_COOLDOWN_SECONDS=30

OPENAI_API_KEY=sk-your-key-here
AI_MODEL=gpt-4o-mini
AI_ENABLED=true

WEBHOOK_URL=https://discord.com/api/webhooks/your-url-here
```

### Done Condition

```bash
docker compose up
# Gateway logs: "Uvicorn running on http://0.0.0.0:8000"
curl http://localhost:8000/health
# {"status": "ok"}  ← doesn't exist yet, just check no crash
```

---

## Phase 1: Foundation — Auth + Security (Week 1–2)

**Goal:** A running gateway that authenticates users, validates queries, and safely executes SELECTs. Dangerous queries are blocked. Brute force is throttled.

---

### Step 1.1 — gateway/requirements.txt

```txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.0
pydantic-settings==2.2.1
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.29
alembic==1.13.1
redis[asyncio]==5.0.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.27.0
cryptography==42.0.5
```

### Step 1.2 — gateway/config.py

```python
# gateway/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    secret_key: str
    jwt_expiry_minutes: int = 60

    # Database
    db_primary_url: str
    db_replica_url: str
    db_pool_min: int = 5
    db_pool_max: int = 20

    # Redis
    redis_url: str
    cache_default_ttl: int = 60

    # Security
    rate_limit_per_minute: int = 60
    brute_force_max_attempts: int = 5
    brute_force_lockout_minutes: int = 15
    encrypt_columns: str = "ssn,credit_card"
    encryption_key: str
    honeypot_tables: str = "secret_keys,admin_passwords"

    # Query limits
    query_timeout_seconds: int = 5
    auto_limit_default: int = 1000
    cost_threshold_warn: int = 1000
    cost_threshold_block: int = 10000
    slow_query_threshold_ms: int = 200
    daily_budget_default: int = 50000

    # Circuit breaker
    circuit_failure_threshold: int = 5
    circuit_cooldown_seconds: int = 30

    # AI
    openai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_enabled: bool = False

    # Alerts
    webhook_url: str = ""

    @property
    def encrypt_columns_list(self) -> List[str]:
        return [c.strip() for c in self.encrypt_columns.split(",")]

    @property
    def honeypot_tables_list(self) -> List[str]:
        return [t.strip() for t in self.honeypot_tables.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 1.3 — Database models

```python
# gateway/models/user.py
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid, enum
from datetime import datetime

Base = declarative_base()

class Role(str, enum.Enum):
    admin = "admin"
    readonly = "readonly"
    guest = "guest"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SAEnum(Role), default=Role.readonly)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    key_hash = Column(String, nullable=False)   # store hash, not raw key
    label = Column(String)
    is_active = Column(Boolean, default=True)
    grace_until = Column(DateTime, nullable=True)  # for rotation grace period
    created_at = Column(DateTime, default=datetime.utcnow)

class IPRule(Base):
    __tablename__ = "ip_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(String, nullable=False)
    rule_type = Column(String)  # "allow" or "block"
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# gateway/models/audit_log.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from .user import Base
import uuid
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True))
    role = Column(String)
    query_fingerprint = Column(String)
    query_type = Column(String)      # SELECT, INSERT, etc.
    latency_ms = Column(Float)
    status = Column(String)          # success, error, blocked, cached
    cached = Column(Boolean, default=False)
    slow = Column(Boolean, default=False)
    anomaly_flag = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # No UPDATE or DELETE ever on this table — enforced in code, not just convention
```

### Step 1.4 — Database connection

```python
# gateway/utils/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings

primary_engine = create_async_engine(
    settings.db_primary_url,
    pool_size=settings.db_pool_min,
    max_overflow=settings.db_pool_max - settings.db_pool_min,
    echo=False,
)

replica_engine = create_async_engine(
    settings.db_replica_url,
    pool_size=settings.db_pool_min,
    max_overflow=settings.db_pool_max - settings.db_pool_min,
    echo=False,
)

PrimarySession = async_sessionmaker(primary_engine, expire_on_commit=False)
ReplicaSession = async_sessionmaker(replica_engine, expire_on_commit=False)

async def get_primary_db():
    async with PrimarySession() as session:
        yield session

async def get_replica_db():
    async with ReplicaSession() as session:
        yield session
```

### Step 1.5 — Auth middleware

```python
# gateway/middleware/security/auth.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from config import settings
import hashlib

security = HTTPBearer(auto_error=False)

def create_jwt(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    # Try JWT first
    if credentials:
        payload = decode_jwt(credentials.credentials)
        request.state.user_id = payload["sub"]
        request.state.role = payload["role"]
        return payload

    # Try API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_hash = hash_api_key(api_key)
        # Look up in Redis (fast path) then DB (fallback)
        redis = request.app.state.redis
        cached = await redis.get(f"apikey:{key_hash}")
        if cached:
            import json
            user_data = json.loads(cached)
            request.state.user_id = user_data["user_id"]
            request.state.role = user_data["role"]
            return user_data
        # DB lookup omitted for brevity — fetch APIKey record, validate is_active
        raise HTTPException(status_code=401, detail="Invalid API key")

    raise HTTPException(status_code=401, detail="No credentials provided")
```

### Step 1.6 — Brute force protection

```python
# gateway/middleware/security/brute_force.py
from fastapi import Request, HTTPException
from config import settings

async def check_brute_force(request: Request, username: str):
    redis = request.app.state.redis
    key = f"brute:{request.client.host}:{username}"

    count = await redis.get(key)
    count = int(count) if count else 0

    if count >= settings.brute_force_max_attempts:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=423,
            detail=f"Account locked. Try again in {ttl} seconds."
        )

async def record_failed_attempt(request: Request, username: str):
    redis = request.app.state.redis
    key = f"brute:{request.client.host}:{username}"
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.brute_force_lockout_minutes * 60)
    await pipe.execute()

async def clear_failed_attempts(request: Request, username: str):
    redis = request.app.state.redis
    key = f"brute:{request.client.host}:{username}"
    await redis.delete(key)
```

### Step 1.7 — IP filter

```python
# gateway/middleware/security/ip_filter.py
from fastapi import Request, HTTPException

async def check_ip(request: Request):
    client_ip = request.client.host
    redis = request.app.state.redis

    # Check blocklist first
    blocked = await redis.sismember("ip:blocklist", client_ip)
    if blocked:
        raise HTTPException(status_code=403, detail="IP address is blocked")

    # If allowlist exists and is non-empty, enforce it
    allowlist_size = await redis.scard("ip:allowlist")
    if allowlist_size > 0:
        allowed = await redis.sismember("ip:allowlist", client_ip)
        if not allowed:
            raise HTTPException(status_code=403, detail="IP not in allowlist")
```

### Step 1.8 — Rate limiter

```python
# gateway/middleware/security/rate_limiter.py
from fastapi import Request, HTTPException
from config import settings
import time

async def check_rate_limit(request: Request):
    user_id = getattr(request.state, "user_id", request.client.host)
    redis = request.app.state.redis

    window = 60  # 1 minute window
    now = int(time.time())
    window_key = now // window
    key = f"ratelimit:{user_id}:{window_key}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window * 2)

    if count > settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Anomaly detection — compare to rolling baseline
    await update_anomaly_baseline(redis, user_id, count)

async def update_anomaly_baseline(redis, user_id: str, current_count: int):
    baseline_key = f"anomaly:baseline:{user_id}"
    # Store last 12 window counts as a list
    await redis.lpush(baseline_key, current_count)
    await redis.ltrim(baseline_key, 0, 11)   # keep last 12 windows
    await redis.expire(baseline_key, 3600)

    values = await redis.lrange(baseline_key, 0, -1)
    if len(values) < 3:
        return   # not enough history yet

    avg = sum(int(v) for v in values) / len(values)
    if avg > 0 and current_count > avg * 3:
        # Flag anomaly — don't block, just mark
        await redis.setex(f"anomaly:flag:{user_id}", 300, "1")
```

### Step 1.9 — Query validator

```python
# gateway/middleware/security/validator.py
from fastapi import HTTPException
import re

BLOCKED_KEYWORDS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bGRANT\b',
    r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b',
]

INJECTION_PATTERNS = [
    r"'\s*(OR|AND)\s*'?\d",       # ' OR '1'='1
    r"--\s",                       # SQL comment --
    r";\s*--",                     # ; --
    r"UNION\s+SELECT",             # UNION SELECT
    r"1\s*=\s*1",                  # 1=1
    r"'\s*;\s*",                   # '; (stacked queries)
    r"/\*.*?\*/",                  # Block comments /* */
    r"xp_cmdshell",               # MSSQL exec
    r"INFORMATION_SCHEMA",         # Schema enumeration
    r"SLEEP\s*\(",                 # Time-based blind injection
    r"WAITFOR\s+DELAY",            # MSSQL time-based
    r"BENCHMARK\s*\(",             # MySQL time-based
]

ALLOWED_TYPES = {"SELECT", "INSERT"}

def validate_query(query: str) -> str:
    query = query.strip()
    first_word = query.split()[0].upper()

    # Block dangerous query types
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, query, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail=f"Query type not allowed: {first_word}"
            )

    # Detect injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Potential SQL injection detected"
            )

    if first_word not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Only SELECT and INSERT are permitted. Got: {first_word}"
        )

    return query
```

### Step 1.10 — RBAC

```python
# gateway/middleware/security/rbac.py
from fastapi import Request, HTTPException

# Role → tables allowed (empty list = all tables allowed)
ROLE_TABLE_ACCESS = {
    "admin": [],           # all tables
    "readonly": ["users", "orders", "products"],
    "guest": ["products"],
}

# Role → columns to strip from results (deny-list approach)
ROLE_COLUMN_DENY = {
    "admin": [],
    "readonly": ["hashed_password", "internal_notes"],
    "guest": ["hashed_password", "internal_notes", "email", "phone"],
}

def check_table_access(role: str, query: str):
    allowed = ROLE_TABLE_ACCESS.get(role, [])
    if not allowed:
        return  # admin — all tables allowed

    query_upper = query.upper()
    for table in allowed:
        # rough check — good enough for portfolio
        if table.upper() in query_upper:
            return

    raise HTTPException(
        status_code=403,
        detail=f"Role '{role}' does not have access to the queried table"
    )

def strip_denied_columns(role: str, rows: list[dict]) -> list[dict]:
    denied = ROLE_COLUMN_DENY.get(role, [])
    if not denied or not rows:
        return rows
    return [
        {k: v for k, v in row.items() if k not in denied}
        for row in rows
    ]
```

### Step 1.11 — Auth router

```python
# gateway/routers/v1/auth.py
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from middleware.security.auth import create_jwt, hash_api_key
from middleware.security.brute_force import (
    check_brute_force, record_failed_attempt, clear_failed_attempts
)
from utils.db import get_primary_db
import secrets, uuid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(body: LoginRequest, request: Request, db=Depends(get_primary_db)):
    await check_brute_force(request, body.username)

    # Fetch user from DB (pseudo-code — use SQLAlchemy select)
    user = await db.execute(...)   # select User where username = body.username

    if not user or not pwd_ctx.verify(body.password, user.hashed_password):
        await record_failed_attempt(request, body.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await clear_failed_attempts(request, body.username)
    token = create_jwt(str(user.id), user.role)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/keys")
async def generate_api_key(request: Request):
    raw_key = f"siqg_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)
    # Store key_hash in DB (APIKey model)
    # Cache in Redis: apikey:{key_hash} → {user_id, role}
    return {"api_key": raw_key, "note": "Store this — it won't be shown again"}
```

### Step 1.12 — Main query router (Phase 1 version)

```python
# gateway/routers/v1/query.py
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from middleware.security.auth import get_current_user
from middleware.security.ip_filter import check_ip
from middleware.security.rate_limiter import check_rate_limit
from middleware.security.validator import validate_query
from middleware.security.rbac import check_table_access, strip_denied_columns
from utils.db import get_primary_db
import uuid, time

router = APIRouter(prefix="/api/v1", tags=["query"])

class QueryRequest(BaseModel):
    query: str
    encrypt_columns: list[str] = []
    decrypt_columns: list[str] = []
    dry_run: bool = False

@router.post("/query")
async def execute_query(
    body: QueryRequest,
    request: Request,
    user = Depends(get_current_user),
    db = Depends(get_primary_db),
):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    start = time.time()

    # Security layer
    await check_ip(request)
    await check_rate_limit(request)
    clean_query = validate_query(body.query)
    check_table_access(request.state.role, clean_query)

    # Execute (Phase 1 — direct, no cache/circuit breaker yet)
    result = await db.execute(clean_query)  # use asyncpg directly later
    rows = [dict(r) for r in result]

    # Strip denied columns
    rows = strip_denied_columns(request.state.role, rows)

    latency_ms = (time.time() - start) * 1000

    return {
        "trace_id": trace_id,
        "status": "success",
        "latency_ms": round(latency_ms, 2),
        "result": rows,
    }
```

### Step 1.13 — main.py

```python
# gateway/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from redis.asyncio import Redis
from config import settings
from models.user import Base
from utils.db import primary_engine
from routers.v1 import auth, query
from routers.v1.health import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    # Create tables (use Alembic in production)
    async with primary_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    await app.state.redis.aclose()
    await primary_engine.dispose()

app = FastAPI(
    title="Secure Intelligent Query Gateway",
    version="1.0.0",
    docs_url="/api/v1/docs",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(query.router)
app.include_router(health_router)
```

### Step 1.14 — Health check

```python
# gateway/routers/v1/health.py
from fastapi import APIRouter, Request
from utils.db import primary_engine

router = APIRouter(tags=["health"])

@router.get("/health")
async def health(request: Request):
    results = {"status": "ok", "db": "unknown", "redis": "unknown"}

    try:
        async with primary_engine.connect() as conn:
            await conn.execute("SELECT 1")
        results["db"] = "ok"
    except Exception as e:
        results["db"] = f"error: {str(e)}"
        results["status"] = "degraded"

    try:
        await request.app.state.redis.ping()
        results["redis"] = "ok"
    except Exception as e:
        results["redis"] = f"error: {str(e)}"
        results["status"] = "degraded"

    return results
```

### Done Condition — Phase 1

```bash
# 1. Start
docker compose up --build

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
# → {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Run a SELECT
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer eyJ..." \
  -d '{"query": "SELECT 1 as hello"}'
# → {"trace_id": "...", "status": "success", "result": [{"hello": 1}]}

# 4. Try a DROP — should be blocked
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer eyJ..." \
  -d '{"query": "DROP TABLE users"}'
# → 400 {"detail": "Query type not allowed: DROP"}

# 5. Fail login 5 times — 6th attempt returns 423
# 6. GET /health → {"status": "ok", "db": "ok", "redis": "ok"}
```

---

## Phase 2: Performance Layer (Week 3–4)

**Goal:** Repeated queries never hit the database twice. Unbounded SELECTs are auto-capped. Writes go to primary, reads go to replica.

---

### Step 2.1 — Query fingerprinter

```python
# gateway/middleware/performance/fingerprinter.py
import re
import hashlib

def normalize_query(query: str) -> str:
    """
    Replace literal values with placeholders.
    SELECT * FROM users WHERE id = 1 AND name = 'Alice'
    → SELECT * FROM users WHERE id = ? AND name = ?
    """
    # Replace integers
    query = re.sub(r'\b\d+\b', '?', query)
    # Replace string literals
    query = re.sub(r"'[^']*'", '?', query)
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query).strip().upper()
    return query

def get_cache_key(query: str, role: str) -> tuple[str, str]:
    """Returns (fingerprint, cache_key)"""
    fingerprint = normalize_query(query)

    # Extract table name (rough, covers most cases)
    table_match = re.search(
        r'\bFROM\s+(\w+)', query, re.IGNORECASE
    )
    table = table_match.group(1).lower() if table_match else "unknown"

    query_hash = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    cache_key = f"siqg:cache:{table}:{query_hash}:{role}"
    return fingerprint, cache_key, table
```

### Step 2.2 — Cache middleware

```python
# gateway/middleware/performance/cache.py
from fastapi import Request
from config import settings
import json

async def get_from_cache(request: Request, cache_key: str):
    redis = request.app.state.redis
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

async def set_in_cache(request: Request, cache_key: str, data: list):
    redis = request.app.state.redis
    await redis.setex(
        cache_key,
        settings.cache_default_ttl,
        json.dumps(data)
    )

async def invalidate_for_table(request: Request, table: str):
    """
    On any write to {table}, delete all cached SELECT results for that table.
    Pattern: siqg:cache:{table}:*
    """
    redis = request.app.state.redis
    pattern = f"siqg:cache:{table}:*"
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
            deleted += len(keys)
        if cursor == 0:
            break
    return deleted
```

### Step 2.3 — Auto-LIMIT injector

```python
# gateway/middleware/performance/auto_limit.py
import re
from config import settings

def inject_limit(query: str) -> tuple[str, bool]:
    """
    Returns (modified_query, was_limit_injected).
    """
    if not query.strip().upper().startswith("SELECT"):
        return query, False

    has_limit = bool(re.search(r'\bLIMIT\b', query, re.IGNORECASE))
    if has_limit:
        return query, False

    modified = f"{query.rstrip(';')} LIMIT {settings.auto_limit_default}"
    return modified, True
```

### Step 2.4 — Cost estimator

```python
# gateway/middleware/performance/cost_estimator.py
from fastapi import Request, HTTPException
from config import settings
import json

async def estimate_cost(request: Request, query: str, db_conn) -> float:
    """
    Run EXPLAIN (no ANALYZE) and extract total cost.
    """
    try:
        explain_query = f"EXPLAIN (FORMAT JSON) {query}"
        result = await db_conn.fetchval(explain_query)
        plan = json.loads(result)
        total_cost = plan[0]["Plan"]["Total Cost"]
        return total_cost
    except Exception:
        return 0.0   # don't block on explain failure

def check_cost_threshold(cost: float, role: str) -> dict:
    """
    Returns {"warning": bool, "blocked": bool, "cost": float}
    """
    blocked = cost > settings.cost_threshold_block and role != "admin"
    warning = cost > settings.cost_threshold_warn

    if blocked:
        raise HTTPException(
            status_code=403,
            detail=f"Query cost ({cost:.0f}) exceeds limit ({settings.cost_threshold_block}). "
                   f"Use a more specific query or contact admin."
        )
    return {"warning": warning, "blocked": False, "cost": cost}
```

### Step 2.5 — Budget tracker

```python
# gateway/middleware/performance/budget.py
from fastapi import Request, HTTPException
from config import settings
from datetime import datetime

async def check_and_deduct_budget(request: Request, cost: float):
    redis = request.app.state.redis
    user_id = request.state.user_id
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"budget:{user_id}:{today}"

    # Get current usage
    current = await redis.get(key)
    current = float(current) if current else 0.0

    daily_limit = settings.daily_budget_default
    # Admins get 10x budget
    if getattr(request.state, "role", "") == "admin":
        daily_limit *= 10

    if current + cost > daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily query budget exhausted. "
                   f"Used: {current:.0f}/{daily_limit:.0f}. Resets at midnight UTC."
        )

    # Deduct
    pipe = redis.pipeline()
    pipe.incrbyfloat(key, cost)
    # TTL = seconds until midnight
    now = datetime.utcnow()
    seconds_until_midnight = (24 - now.hour) * 3600 - now.minute * 60 - now.second
    pipe.expire(key, seconds_until_midnight)
    await pipe.execute()
```

### Step 2.6 — Router (R/W split)

```python
# gateway/middleware/execution/router.py
from utils.db import PrimarySession, ReplicaSession
import re

def get_session_for_query(query: str):
    """
    SELECT → replica session
    Everything else → primary session
    """
    first_word = query.strip().split()[0].upper()
    if first_word == "SELECT":
        return ReplicaSession()
    return PrimarySession()
```

### Step 2.7 — Updated query router (Phase 2)

```python
# gateway/routers/v1/query.py  — updated for Phase 2

@router.post("/query")
async def execute_query(body: QueryRequest, request: Request, user=Depends(get_current_user)):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    start = time.time()

    # --- SECURITY LAYER ---
    await check_ip(request)
    await check_rate_limit(request)
    clean_query = validate_query(body.query)
    check_table_access(request.state.role, clean_query)

    # --- PERFORMANCE LAYER ---
    fingerprint, cache_key, table = get_cache_key(clean_query, request.state.role)

    # Cache check
    cached_result = await get_from_cache(request, cache_key)
    if cached_result is not None:
        return {
            "trace_id": trace_id,
            "status": "success",
            "cached": True,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "result": cached_result,
        }

    # Auto-LIMIT
    modified_query, limit_injected = inject_limit(clean_query)

    # R/W routing
    session = get_session_for_query(clean_query)

    async with session as db:
        # Cost estimation
        conn = await db.connection()
        raw_conn = await conn.get_raw_connection()
        cost_info = await estimate_cost(request, modified_query, raw_conn.driver_connection)
        await check_and_deduct_budget(request, cost_info["cost"])

        # Execute
        result = await raw_conn.driver_connection.fetch(modified_query)
        rows = [dict(r) for r in result]

    rows = strip_denied_columns(request.state.role, rows)

    # Cache write (only for SELECT)
    if clean_query.strip().upper().startswith("SELECT"):
        await set_in_cache(request, cache_key, rows)
    else:
        await invalidate_for_table(request, table)

    latency_ms = round((time.time() - start) * 1000, 2)

    return {
        "trace_id": trace_id,
        "status": "success",
        "cached": False,
        "cache_key": cache_key,
        "latency_ms": latency_ms,
        "query_diff": {
            "original": clean_query,
            "executed": modified_query,
            "limit_injected": limit_injected,
        },
        "cost_info": cost_info,
        "result": rows,
    }
```

### Done Condition — Phase 2

```bash
# 1. Run same SELECT twice
curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "SELECT * FROM users WHERE id = 1"}'
# First: cached=false, latency ~30ms

curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "SELECT * FROM users WHERE id = 1"}'
# Second: cached=true, latency ~2ms

# 2. Run without LIMIT
curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "SELECT * FROM orders"}'
# query_diff.limit_injected = true
# query_diff.executed = "SELECT * FROM orders LIMIT 1000"

# 3. Insert something, then SELECT — cache should miss again
```

---

## Phase 3: Intelligence Layer (Week 5–6)

**Goal:** Every query response includes its execution plan, timing, scan type, and index suggestions. Slow queries are logged and alerted.

---

### Step 3.1 — EXPLAIN ANALYZE parser

```python
# gateway/middleware/execution/analyzer.py
import json
import re

async def run_explain_analyze(conn, query: str) -> dict:
    """
    Runs EXPLAIN (ANALYZE, FORMAT JSON) after execution.
    Returns parsed insights.
    """
    try:
        explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS) {query}"
        result = await conn.fetchval(explain_query)
        plan_data = json.loads(result)
        plan = plan_data[0]["Plan"]

        scan_type = plan.get("Node Type", "Unknown")
        actual_time = plan.get("Actual Total Time", 0)
        actual_rows = plan.get("Actual Rows", 0)
        total_cost = plan.get("Total Cost", 0)

        # Recursive extraction for nested plans
        all_nodes = _extract_all_nodes(plan)
        seq_scans = [n for n in all_nodes if n.get("Node Type") == "Seq Scan"]

        return {
            "scan_type": scan_type,
            "execution_time_ms": round(actual_time, 3),
            "rows_processed": actual_rows,
            "total_cost": round(total_cost, 2),
            "seq_scans": seq_scans,
            "raw_plan": plan_data,
        }
    except Exception as e:
        return {"error": str(e)}

def _extract_all_nodes(plan: dict) -> list:
    nodes = [plan]
    for child in plan.get("Plans", []):
        nodes.extend(_extract_all_nodes(child))
    return nodes
```

### Step 3.2 — Index recommendation engine

```python
# gateway/middleware/execution/analyzer.py (continued)

def generate_index_suggestions(explain_result: dict, original_query: str) -> list:
    suggestions = []
    seq_scans = explain_result.get("seq_scans", [])

    # Extract WHERE clause columns from original query
    where_cols = _extract_where_columns(original_query)

    for scan in seq_scans:
        table = scan.get("Relation Name", "")
        if not table:
            continue

        for col in where_cols:
            suggestion = {
                "table": table,
                "column": col,
                "reason": f"Seq Scan detected on '{table}'. "
                          f"Column '{col}' appears in WHERE clause.",
                "ddl": f"CREATE INDEX idx_{table}_{col} ON {table}({col});",
                "estimated_improvement": "Seq Scan → Index Scan (typically 10-100x faster on large tables)",
            }
            suggestions.append(suggestion)

    return suggestions

def _extract_where_columns(query: str) -> list:
    # Rough extraction — covers common patterns
    where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
    if not where_match:
        return []

    where_clause = where_match.group(1)
    # Extract column names (word before = < > LIKE IN)
    cols = re.findall(r'\b(\w+)\s*(?:=|<|>|LIKE|IN\s*\()', where_clause, re.IGNORECASE)
    return list(set(cols))
```

### Step 3.3 — Complexity scorer

```python
# gateway/middleware/performance/complexity.py

def score_complexity(query: str) -> dict:
    score = 0
    reasons = []
    query_upper = query.upper()

    join_count = query_upper.count(" JOIN ")
    if join_count > 0:
        score += join_count * 2
        reasons.append(f"{join_count} JOIN(s) (+{join_count * 2})")

    subquery_count = query_upper.count("SELECT", 1)  # skip first SELECT
    if subquery_count > 0:
        score += subquery_count * 3
        reasons.append(f"{subquery_count} subquery(s) (+{subquery_count * 3})")

    if "SELECT *" in query_upper:
        score += 1
        reasons.append("SELECT * used (+1)")

    has_where = "WHERE" in query_upper
    if not has_where and "FROM" in query_upper:
        score += 2
        reasons.append("No WHERE clause — full table scan risk (+2)")

    level = "low" if score <= 2 else "medium" if score <= 6 else "high"

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
    }
```

### Step 3.4 — Slow query model + logger

```python
# gateway/models/slow_query.py
from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from .user import Base
import uuid
from datetime import datetime

class SlowQuery(Base):
    __tablename__ = "slow_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True))
    query_fingerprint = Column(String)
    execution_time_ms = Column(Float)
    scan_type = Column(String)
    cost = Column(Float)
    suggestions = Column(Text)   # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# gateway/middleware/execution/analyzer.py (continued)
import json

async def log_slow_query(db_session, trace_id: str, user_id: str,
                          fingerprint: str, analysis: dict):
    from models.slow_query import SlowQuery
    record = SlowQuery(
        trace_id=trace_id,
        user_id=user_id,
        query_fingerprint=fingerprint,
        execution_time_ms=analysis.get("execution_time_ms", 0),
        scan_type=analysis.get("scan_type", ""),
        cost=analysis.get("total_cost", 0),
        suggestions=json.dumps(analysis.get("index_suggestions", [])),
    )
    db_session.add(record)
    await db_session.commit()
```

### Step 3.5 — Updated query route with analysis

Add to the execute_query handler after execution:

```python
# After rows are fetched...

# EXPLAIN ANALYZE
async with get_session_for_query(clean_query) as analysis_db:
    analysis_conn = await analysis_db.connection()
    raw = await analysis_conn.get_raw_connection()
    explain_result = await run_explain_analyze(raw.driver_connection, modified_query)

suggestions = generate_index_suggestions(explain_result, clean_query)
explain_result["index_suggestions"] = suggestions
complexity = score_complexity(clean_query)

# Slow query detection
is_slow = explain_result.get("execution_time_ms", 0) > settings.slow_query_threshold_ms
if is_slow:
    await log_slow_query(primary_db, trace_id, user_id, fingerprint, explain_result)
    # Webhook alert in Phase 4

# Final response — add to return dict:
"analysis": {
    "scan_type": explain_result.get("scan_type"),
    "execution_time_ms": explain_result.get("execution_time_ms"),
    "rows_processed": explain_result.get("rows_processed"),
    "total_cost": explain_result.get("total_cost"),
    "slow_query": is_slow,
    "index_suggestions": suggestions,
    "complexity": complexity,
},
```

### Done Condition — Phase 3

```bash
# Run a query on a table without indexes
curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "SELECT * FROM orders WHERE customer_id = 42"}'

# Response should include:
# analysis.scan_type = "Seq Scan"
# analysis.index_suggestions[0].ddl = "CREATE INDEX idx_orders_customer_id ON orders(customer_id);"
# analysis.slow_query = true (if over threshold)
# complexity.level = "medium" or "high"

# Check slow queries endpoint
curl http://localhost:8000/api/v1/admin/slow-queries
# Should show the above query
```

---

## Phase 4: Observability Layer (Week 7–8)

**Goal:** Full audit trail. Live metrics served to React. Webhook alerts. Health + status page.

---

### Step 4.1 — Structured JSON logger

```python
# gateway/utils/logger.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        # Attach extra fields if present
        for field in ["trace_id", "user_id", "latency_ms", "query_fingerprint"]:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        return json.dumps(log_entry)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger("siqg")
```

### Step 4.2 — Audit log writer

```python
# gateway/middleware/observability/audit.py
from models.audit_log import AuditLog
from utils.db import PrimarySession

async def write_audit_log(
    trace_id: str,
    user_id: str,
    role: str,
    fingerprint: str,
    query_type: str,
    latency_ms: float,
    status: str,
    cached: bool,
    slow: bool,
    anomaly_flag: bool,
    error_message: str = None,
):
    async with PrimarySession() as db:
        log = AuditLog(
            trace_id=trace_id,
            user_id=user_id,
            role=role,
            query_fingerprint=fingerprint,
            query_type=query_type,
            latency_ms=latency_ms,
            status=status,
            cached=cached,
            slow=slow,
            anomaly_flag=anomaly_flag,
            error_message=error_message,
        )
        db.add(log)
        await db.commit()
    # This is fire-and-forget — don't await in the critical path
    # Use asyncio.create_task() to avoid blocking the response
```

### Step 4.3 — Metrics counters (Redis-based)

```python
# gateway/middleware/observability/metrics.py
from fastapi import Request
import time

async def increment(request: Request, key: str, amount: float = 1):
    redis = request.app.state.redis
    await redis.incrbyfloat(f"siqg:metrics:{key}", amount)

async def record_latency(request: Request, latency_ms: float):
    redis = request.app.state.redis
    # Keep last 1000 latency values for percentile calculation
    pipe = redis.pipeline()
    pipe.lpush("siqg:metrics:latency_samples", latency_ms)
    pipe.ltrim("siqg:metrics:latency_samples", 0, 999)
    await pipe.execute()

async def get_live_metrics(redis) -> dict:
    keys = [
        "siqg:metrics:requests_total",
        "siqg:metrics:cache_hits",
        "siqg:metrics:cache_misses",
        "siqg:metrics:rate_limit_hits",
        "siqg:metrics:slow_queries",
        "siqg:metrics:errors",
    ]
    values = await redis.mget(*keys)
    metrics = {k.split(":")[-1]: float(v or 0) for k, v in zip(keys, values)}

    # Latency percentiles
    samples = await redis.lrange("siqg:metrics:latency_samples", 0, -1)
    if samples:
        sorted_samples = sorted(float(s) for s in samples)
        n = len(sorted_samples)
        metrics["latency_p50"] = sorted_samples[int(n * 0.5)]
        metrics["latency_p95"] = sorted_samples[int(n * 0.95)]
        metrics["latency_p99"] = sorted_samples[int(n * 0.99)]

    # Cache hit ratio
    hits = metrics.get("cache_hits", 0)
    misses = metrics.get("cache_misses", 0)
    total = hits + misses
    metrics["cache_hit_ratio"] = round(hits / total * 100, 1) if total > 0 else 0

    return metrics
```

### Step 4.4 — Metrics API route

```python
# gateway/routers/v1/metrics.py
from fastapi import APIRouter, Request
from middleware.observability.metrics import get_live_metrics

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("/live")
async def live_metrics(request: Request):
    return await get_live_metrics(request.app.state.redis)
```

### Step 4.5 — Webhook alerts

```python
# gateway/middleware/observability/webhooks.py
import httpx
from config import settings
from datetime import datetime

async def send_alert(event_type: str, trace_id: str, user_id: str, message: str, extra: dict = None):
    if not settings.webhook_url:
        return

    payload = {
        "embeds": [{
            "title": f"SIQG Alert: {event_type}",
            "description": message,
            "color": _color_for_event(event_type),
            "fields": [
                {"name": "Trace ID", "value": trace_id, "inline": True},
                {"name": "User", "value": str(user_id), "inline": True},
                {"name": "Time", "value": datetime.utcnow().isoformat(), "inline": True},
            ] + ([{"name": k, "value": str(v), "inline": True} for k, v in extra.items()] if extra else []),
        }]
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(settings.webhook_url, json=payload, timeout=5)
    except Exception:
        pass   # Alerts should never crash the main flow

def _color_for_event(event_type: str) -> int:
    colors = {
        "slow_query": 0xFFA500,    # orange
        "anomaly": 0xFF0000,       # red
        "honeypot_hit": 0x8B0000,  # dark red
        "rate_limit": 0xFFFF00,    # yellow
        "circuit_open": 0xFF4500,  # red-orange
    }
    return colors.get(event_type, 0x808080)
```

### Step 4.6 — Table heat map

```python
# gateway/middleware/observability/heatmap.py
from fastapi import Request

async def record_table_access(request: Request, table: str):
    redis = request.app.state.redis
    await redis.zincrby("siqg:heatmap:tables", 1, table)

async def get_heatmap(redis) -> list:
    entries = await redis.zrevrange("siqg:heatmap:tables", 0, -1, withscores=True)
    return [{"table": name, "query_count": int(score)} for name, score in entries]
```

### Step 4.7 — Admin router

```python
# gateway/routers/v1/admin.py
from fastapi import APIRouter, Request, Depends
from middleware.security.auth import get_current_user
from middleware.observability.heatmap import get_heatmap
from middleware.observability.metrics import get_live_metrics
from fastapi.responses import StreamingResponse
import csv, io

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/heatmap")
async def table_heatmap(request: Request, user=Depends(get_current_user)):
    return await get_heatmap(request.app.state.redis)

@router.get("/audit")
async def audit_log(
    request: Request,
    user=Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    status: str = None,
):
    # SELECT from audit_logs with filters
    ...

@router.get("/audit/export")
async def export_audit(request: Request, user=Depends(get_current_user)):
    # Fetch all audit logs, stream as CSV
    records = [...]  # fetch from DB

    def generate():
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys() if records else [])
        writer.writeheader()
        for row in records:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"}
    )

@router.get("/slow-queries")
async def slow_queries(request: Request, user=Depends(get_current_user), limit: int = 20):
    # SELECT from slow_queries ORDER BY created_at DESC LIMIT {limit}
    ...

@router.get("/budget")
async def budget_usage(request: Request, user=Depends(get_current_user)):
    # Scan Redis for budget:{user_id}:{today} keys
    ...
```

### Done Condition — Phase 4

```bash
# 1. Run 10 queries of different kinds
# 2. Check audit log
curl http://localhost:8000/api/v1/admin/audit
# Should show all 10 with trace_id, latency, status, cached

# 3. Check live metrics
curl http://localhost:8000/api/v1/metrics/live
# {"requests_total": 10, "cache_hits": 4, "cache_hit_ratio": 40.0,
#  "latency_p50": 28.3, "latency_p95": 145.2, ...}

# 4. Run a slow query (full table scan on large table)
# → Discord/Slack should receive a webhook message within 2 seconds

# 5. Check heatmap
curl http://localhost:8000/api/v1/admin/heatmap
# [{"table": "orders", "query_count": 7}, {"table": "users", "query_count": 3}]
```

---

## Phase 5: Security Hardening (Week 8–9)

**Goal:** Column encryption, PII masking, circuit breaker, honeypot, anomaly detection fully wired.

---

### Step 5.1 — AES-256-GCM encryptor

```python
# gateway/middleware/execution/encryptor.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import settings
import os, base64

def _get_key() -> bytes:
    key = settings.encryption_key.encode()
    # Ensure 32 bytes
    return key[:32].ljust(32, b'0')

def encrypt_value(plaintext: str) -> str:
    aesgcm = AESGCM(_get_key())
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    # Store nonce + ciphertext, base64 encoded
    return base64.b64encode(nonce + ct).decode()

def decrypt_value(encoded: str) -> str:
    aesgcm = AESGCM(_get_key())
    data = base64.b64decode(encoded.encode())
    nonce = data[:12]
    ct = data[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()

def encrypt_query_params(query: str, params: dict, encrypt_cols: list) -> dict:
    """Encrypt values for specified columns before INSERT."""
    encrypted = {}
    for col, val in params.items():
        if col in encrypt_cols and val is not None:
            encrypted[col] = encrypt_value(str(val))
        else:
            encrypted[col] = val
    return encrypted

def decrypt_rows(rows: list[dict], decrypt_cols: list) -> list[dict]:
    """Decrypt specified columns in SELECT results."""
    decrypted = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            if k in decrypt_cols and v is not None:
                try:
                    new_row[k] = decrypt_value(v)
                except Exception:
                    new_row[k] = v  # return as-is if decryption fails
            else:
                new_row[k] = v
        decrypted.append(new_row)
    return decrypted
```

### Step 5.2 — PII masker

```python
# gateway/middleware/execution/masker.py
import re

MASK_PATTERNS = {
    "ssn":         (r"(\d{3})-(\d{2})-(\d{4})", r"***-**-\3"),
    "credit_card": (r"(\d{4})-(\d{4})-(\d{4})-(\d{4})", r"****-****-****-\4"),
    "email":       (r"(.)(.*)(@.*)", lambda m: m.group(1) + "***" + m.group(3)),
    "phone":       (r"(\d{2})(\d+)(\d{2})", r"\1*****\3"),
}

ROLE_MASK_COLUMNS = {
    "admin": [],          # no masking
    "readonly": ["ssn", "credit_card", "email", "phone"],
    "guest": ["ssn", "credit_card", "email", "phone"],
}

def mask_value(column: str, value: str) -> str:
    pattern_info = MASK_PATTERNS.get(column)
    if not pattern_info:
        return value
    pattern, replacement = pattern_info
    if callable(replacement):
        match = re.search(pattern, value)
        return replacement(match) if match else value
    return re.sub(pattern, replacement, value)

def mask_rows(role: str, rows: list[dict]) -> list[dict]:
    cols_to_mask = ROLE_MASK_COLUMNS.get(role, [])
    if not cols_to_mask:
        return rows

    masked = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            if k in cols_to_mask and v is not None:
                new_row[k] = mask_value(k, str(v))
            else:
                new_row[k] = v
        masked.append(new_row)
    return masked
```

### Step 5.3 — Circuit breaker

```python
# gateway/middleware/execution/circuit_breaker.py
from fastapi import Request, HTTPException
from config import settings
from datetime import datetime, timedelta
import json

class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

CB_KEY = "siqg:circuit_breaker"

async def get_state(redis) -> dict:
    data = await redis.get(CB_KEY)
    if not data:
        return {"state": CircuitBreakerState.CLOSED, "failures": 0, "opened_at": None}
    return json.loads(data)

async def set_state(redis, state: dict):
    await redis.set(CB_KEY, json.dumps(state))

async def check_circuit(request: Request):
    redis = request.app.state.redis
    cb = await get_state(redis)

    if cb["state"] == CircuitBreakerState.CLOSED:
        return   # All good

    if cb["state"] == CircuitBreakerState.OPEN:
        opened_at = datetime.fromisoformat(cb["opened_at"])
        cooldown_end = opened_at + timedelta(seconds=settings.circuit_cooldown_seconds)

        if datetime.utcnow() < cooldown_end:
            raise HTTPException(
                status_code=503,
                detail="Database unavailable. Circuit breaker is open. Try again shortly."
            )
        # Cooldown expired — move to half-open
        cb["state"] = CircuitBreakerState.HALF_OPEN
        await set_state(redis, cb)

    # HALF_OPEN: allow this one request through as a probe

async def record_success(redis):
    cb = await get_state(redis)
    if cb["state"] in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED):
        await set_state(redis, {"state": CircuitBreakerState.CLOSED, "failures": 0, "opened_at": None})

async def record_failure(redis):
    cb = await get_state(redis)

    if cb["state"] == CircuitBreakerState.HALF_OPEN:
        # Probe failed — reopen
        cb["state"] = CircuitBreakerState.OPEN
        cb["opened_at"] = datetime.utcnow().isoformat()
        await set_state(redis, cb)
        return

    failures = cb.get("failures", 0) + 1
    if failures >= settings.circuit_failure_threshold:
        cb["state"] = CircuitBreakerState.OPEN
        cb["opened_at"] = datetime.utcnow().isoformat()
        cb["failures"] = failures
        # Fire webhook alert
    else:
        cb["failures"] = failures

    await set_state(redis, cb)
```

### Step 5.4 — Honeypot checker

```python
# gateway/utils/honeypot.py
from fastapi import Request, HTTPException
from config import settings
from middleware.observability.webhooks import send_alert
import asyncio

async def check_honeypot(request: Request, query: str):
    honeypots = settings.honeypot_tables_list
    query_upper = query.upper()

    for table in honeypots:
        if table.upper() in query_upper:
            user_id = getattr(request.state, "user_id", "unknown")
            trace_id = getattr(request.state, "trace_id", "unknown")

            # Fire alert (non-blocking)
            asyncio.create_task(send_alert(
                event_type="honeypot_hit",
                trace_id=trace_id,
                user_id=user_id,
                message=f"Honeypot table '{table}' accessed! Potential attacker.",
                extra={"ip": request.client.host, "table": table},
            ))

            # Auto-block IP
            redis = request.app.state.redis
            await redis.sadd("ip:blocklist", request.client.host)

            raise HTTPException(
                status_code=403,
                detail="Access denied"   # Deliberately vague
            )
```

### Step 5.5 — Retry with exponential backoff

```python
# gateway/middleware/execution/executor.py
import asyncio
from fastapi import HTTPException

async def execute_with_retry(conn, query: str, max_retries: int = 3) -> list:
    last_error = None
    for attempt in range(max_retries):
        try:
            result = await conn.fetch(query)
            return [dict(r) for r in result]
        except Exception as e:
            error_msg = str(e).lower()
            # Only retry on transient errors
            transient = any(k in error_msg for k in [
                "too many connections",
                "connection reset",
                "server closed the connection",
                "timeout",
            ])
            if not transient:
                raise
            last_error = e
            wait_ms = (100 * (2 ** attempt))  # 100ms, 200ms, 400ms
            await asyncio.sleep(wait_ms / 1000)

    raise HTTPException(status_code=503, detail=f"Query failed after {max_retries} retries: {last_error}")
```

### Done Condition — Phase 5

```bash
# 1. Encryption test
# INSERT with ssn column → stored encrypted in DB
# SELECT same row → ssn returned as "***-**-6789" for readonly role
# SELECT as admin → ssn returned decrypted

# 2. Circuit breaker test
docker compose stop postgres
# First few requests → normal timeout
# After 5 failures → instant 503
docker compose start postgres
# After 30s → half-open probe → 200 → circuit closed

# 3. Honeypot test
curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "SELECT * FROM secret_keys"}'
# → 403 Access denied
# → Discord webhook fires
# → IP added to blocklist
# → Next request from same IP → 403 Forbidden (IP blocked)
```

---

## Phase 6: AI + Polish (Week 9–12)

**Goal:** NL→SQL wired through the full pipeline. Query explainer inline. Clean frontend. SDK. CI passing.

---

### Step 6.1 — NL→SQL endpoint

```python
# gateway/routers/v1/ai.py
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from middleware.security.auth import get_current_user
from config import settings
import httpx

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

class NLRequest(BaseModel):
    question: str
    schema_hint: str = ""   # optional: "table users(id, name, email)"

class ExplainRequest(BaseModel):
    query: str

SYSTEM_PROMPT_NL_TO_SQL = """
You are a SQL query generator. Convert the user's question to a SQL query.
Rules:
- Return ONLY the SQL query, nothing else. No explanation, no markdown, no backticks.
- Only use SELECT or INSERT statements.
- If the question is ambiguous or unsafe, return: ERROR: <reason>
- Always include a LIMIT clause for SELECT queries.
"""

SYSTEM_PROMPT_EXPLAIN = """
You are a SQL expert. Explain what the given SQL query does in plain English.
- Be concise (2-4 sentences maximum).
- Use simple language — assume the reader is non-technical.
- Describe what data is being retrieved or modified and any filters applied.
"""

async def call_llm(system: str, user_message: str) -> str:
    if not settings.ai_enabled or not settings.openai_api_key:
        return "AI features are disabled."

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 500,
                "temperature": 0.1,   # low temp for deterministic SQL
            },
            timeout=10,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

@router.post("/nl-to-sql")
async def nl_to_sql(body: NLRequest, request: Request, user=Depends(get_current_user)):
    prompt = f"Question: {body.question}"
    if body.schema_hint:
        prompt += f"\nDatabase schema: {body.schema_hint}"

    generated_sql = await call_llm(SYSTEM_PROMPT_NL_TO_SQL, prompt)

    if generated_sql.startswith("ERROR:"):
        return {"status": "error", "message": generated_sql, "sql": None}

    # Run the generated SQL through the FULL gateway pipeline
    # by calling the internal query logic (not HTTP — direct function call)
    from routers.v1.query import run_pipeline
    result = await run_pipeline(
        query=generated_sql,
        request=request,
        dry_run=False,
    )

    return {
        "original_question": body.question,
        "generated_sql": generated_sql,
        "result": result,
    }

@router.post("/explain")
async def explain_query(body: ExplainRequest, user=Depends(get_current_user)):
    explanation = await call_llm(SYSTEM_PROMPT_EXPLAIN, f"SQL: {body.query}")
    return {
        "query": body.query,
        "explanation": explanation,
    }
```

### Step 6.2 — Dry-run mode

```python
# In query.py — check at top of execute_query:

if body.dry_run:
    # Run all checks but don't execute on DB
    await check_ip(request)
    await check_rate_limit(request)
    clean_query = validate_query(body.query)
    check_table_access(request.state.role, clean_query)
    _, _, _ = get_cache_key(clean_query, request.state.role)
    modified_query, limit_injected = inject_limit(clean_query)

    # Cost estimate only (no ANALYZE)
    async with get_session_for_query(clean_query) as db:
        conn = await db.connection()
        raw = await conn.get_raw_connection()
        cost = await estimate_cost(request, modified_query, raw.driver_connection)

    complexity = score_complexity(clean_query)

    return {
        "trace_id": trace_id,
        "mode": "dry_run",
        "status": "would_execute",
        "pipeline_checks": {
            "auth": "pass",
            "ip_filter": "pass",
            "rate_limit": "pass",
            "injection_check": "pass",
            "rbac": "pass",
        },
        "query_diff": {"original": clean_query, "would_execute": modified_query},
        "cost_estimate": cost,
        "complexity": complexity,
        "message": "No query was executed. All pipeline checks passed."
    }
```

### Step 6.3 — Python SDK structure

```python
# sdk/siqg/client.py
import httpx
from typing import Optional

class Gateway:
    def __init__(self, base_url: str, api_key: str = None, jwt_token: str = None):
        self.base_url = base_url.rstrip("/")
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["X-API-Key"] = api_key
        if jwt_token:
            self._headers["Authorization"] = f"Bearer {jwt_token}"

    def login(self, username: str, password: str) -> "Gateway":
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password}
            )
            resp.raise_for_status()
            token = resp.json()["access_token"]
            self._headers["Authorization"] = f"Bearer {token}"
        return self

    def query(self, sql: str, encrypt_columns: list = None, dry_run: bool = False) -> dict:
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/query",
                headers=self._headers,
                json={
                    "query": sql,
                    "encrypt_columns": encrypt_columns or [],
                    "dry_run": dry_run,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def explain(self, sql: str) -> str:
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/ai/explain",
                headers=self._headers,
                json={"query": sql},
            )
            resp.raise_for_status()
            return resp.json()["explanation"]

    def status(self) -> dict:
        with httpx.Client() as client:
            return client.get(f"{self.base_url}/health").json()
```

```python
# sdk/siqg/cli.py
import typer
from .client import Gateway

app = typer.Typer()
_gw: Gateway = None

@app.command()
def login(url: str, username: str, password: str):
    """Log in and save token to ~/.siqg_token"""
    gw = Gateway(url).login(username, password)
    token = gw._headers.get("Authorization", "").split(" ")[-1]
    from pathlib import Path
    Path("~/.siqg_token").expanduser().write_text(f"{url}\n{token}")
    typer.echo("Logged in successfully")

@app.command()
def query(sql: str):
    """Execute a SQL query through the gateway"""
    gw = _load_gateway()
    result = gw.query(sql)
    import json
    typer.echo(json.dumps(result, indent=2))

@app.command()
def status():
    """Check gateway health"""
    gw = _load_gateway()
    typer.echo(str(gw.status()))

def _load_gateway() -> Gateway:
    from pathlib import Path
    token_file = Path("~/.siqg_token").expanduser()
    if not token_file.exists():
        typer.echo("Not logged in. Run: siqg login <url> <username> <password>")
        raise typer.Exit(1)
    url, token = token_file.read_text().strip().split("\n")
    return Gateway(url, jwt_token=token)

if __name__ == "__main__":
    app()
```

### Step 6.4 — GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
 push:
  branches: [main, develop]
 pull_request:
  branches: [main]

jobs:
 test:
  runs-on: ubuntu-latest

  services:
   postgres:
    image: postgres:15-alpine
    env:
     POSTGRES_USER: siqg
     POSTGRES_PASSWORD: siqg
     POSTGRES_DB: siqg
    options: >-
     --health-cmd pg_isready
     --health-interval 10s
     --health-timeout 5s
     --health-retries 5
    ports:
     - 5432:5432

   redis:
    image: redis:7-alpine
    options: >-
     --health-cmd "redis-cli ping"
     --health-interval 10s
     --health-timeout 5s
     --health-retries 5
    ports:
     - 6379:6379

  steps:
   - uses: actions/checkout@v4

   - name: Set up Python
     uses: actions/setup-python@v5
     with:
      python-version: "3.11"

   - name: Install dependencies
     run: |
      cd gateway
      pip install -r requirements.txt
      pip install pytest pytest-asyncio pytest-cov

   - name: Run tests with coverage
     env:
      DB_PRIMARY_URL: postgresql+asyncpg://siqg:siqg@localhost:5432/siqg
      DB_REPLICA_URL: postgresql+asyncpg://siqg:siqg@localhost:5432/siqg
      REDIS_URL: redis://localhost:6379/0
      SECRET_KEY: test-secret-key
      ENCRYPTION_KEY: 12345678901234567890123456789012
     run: |
      cd gateway
      pytest tests/ -v --cov=. --cov-report=xml --cov-report=term-missing

   - name: Upload coverage
     uses: codecov/codecov-action@v4
     with:
      file: gateway/coverage.xml
```

### Step 6.5 — Sample unit tests

```python
# tests/unit/test_validator.py
import pytest
from middleware.security.validator import validate_query
from fastapi import HTTPException

def test_select_allowed():
    result = validate_query("SELECT * FROM users")
    assert result == "SELECT * FROM users"

def test_drop_blocked():
    with pytest.raises(HTTPException) as exc:
        validate_query("DROP TABLE users")
    assert exc.value.status_code == 400

def test_injection_or_1_1():
    with pytest.raises(HTTPException):
        validate_query("SELECT * FROM users WHERE id = '1' OR '1'='1'")

def test_injection_union_select():
    with pytest.raises(HTTPException):
        validate_query("SELECT name FROM users UNION SELECT password FROM admins")

def test_injection_comment():
    with pytest.raises(HTTPException):
        validate_query("SELECT * FROM users -- bypass")
```

```python
# tests/unit/test_encryptor.py
from middleware.execution.encryptor import encrypt_value, decrypt_value

def test_encrypt_decrypt_roundtrip():
    original = "123-45-6789"
    encrypted = encrypt_value(original)
    assert encrypted != original
    assert decrypt_value(encrypted) == original

def test_different_encryptions_same_value():
    # AES-GCM uses random nonce — same value encrypts differently each time
    v1 = encrypt_value("test")
    v2 = encrypt_value("test")
    assert v1 != v2
    assert decrypt_value(v1) == decrypt_value(v2) == "test"
```

```python
# tests/unit/test_cache.py
import pytest
from middleware.performance.fingerprinter import normalize_query, get_cache_key

def test_normalize_integers():
    q = "SELECT * FROM users WHERE id = 42"
    result = normalize_query(q)
    assert "?" in result
    assert "42" not in result

def test_normalize_strings():
    q = "SELECT * FROM users WHERE name = 'Alice'"
    result = normalize_query(q)
    assert "?" in result
    assert "Alice" not in result

def test_different_values_same_fingerprint():
    q1 = "SELECT * FROM users WHERE id = 1"
    q2 = "SELECT * FROM users WHERE id = 999"
    assert normalize_query(q1) == normalize_query(q2)

def test_same_query_same_cache_key():
    _, key1, _ = get_cache_key("SELECT * FROM users WHERE id = 1", "admin")
    _, key2, _ = get_cache_key("SELECT * FROM users WHERE id = 1", "admin")
    assert key1 == key2

def test_different_roles_different_cache_keys():
    _, key1, _ = get_cache_key("SELECT * FROM users WHERE id = 1", "admin")
    _, key2, _ = get_cache_key("SELECT * FROM users WHERE id = 1", "readonly")
    assert key1 != key2
```

### Step 6.6 — Locust load test

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between
import random

QUERIES = [
    "SELECT * FROM users LIMIT 10",
    "SELECT * FROM orders WHERE user_id = {}".format(random.randint(1, 100)),
    "SELECT COUNT(*) FROM products",
    "SELECT id, name FROM users WHERE id = {}".format(random.randint(1, 50)),
]

class GatewayUser(HttpUser):
    wait_time = between(0.1, 0.5)
    token = None

    def on_start(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "username": "loadtest_user",
            "password": "loadtest123",
        })
        self.token = resp.json().get("access_token", "")

    @task(3)
    def run_cached_query(self):
        # Same query every time → should hit cache after first run
        self.client.post(
            "/api/v1/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": "SELECT * FROM products LIMIT 20"},
            name="cached_query",
        )

    @task(2)
    def run_varied_query(self):
        query = random.choice(QUERIES)
        self.client.post(
            "/api/v1/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": query},
            name="varied_query",
        )

    @task(1)
    def check_health(self):
        self.client.get("/health", name="health_check")
```

```bash
# Run load test
locust -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  --headless \
  -u 100 \         # 100 concurrent users
  -r 10 \          # 10 users spawned per second
  -t 60s \         # run for 60 seconds
  --html load_report.html

# Key numbers to screenshot for README:
# - Requests/sec
# - P50/P95/P99 latency
# - Cache hit ratio (check /api/v1/metrics/live before and after)
# - Failure rate (should be 0%)
```

### Done Condition — Phase 6

```bash
# 1. NL→SQL
curl -X POST http://localhost:8000/api/v1/ai/nl-to-sql \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "How many users signed up in the last 7 days?"}'
# → generated_sql: "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '7 days' LIMIT 1000"
# → result: [{"count": 42}]

# 2. Explain
curl -X POST http://localhost:8000/api/v1/ai/explain \
  -d '{"query": "SELECT COUNT(*) FROM orders WHERE status = 'pending'"}'
# → explanation: "This query counts the number of orders that are currently in pending status."

# 3. Dry run
curl -X POST http://localhost:8000/api/v1/query \
  -d '{"query": "SELECT * FROM users", "dry_run": true}'
# → mode: "dry_run", pipeline_checks all "pass", cost_estimate: ..., NO result field

# 4. SDK
pip install -e ./sdk
siqg login http://localhost:8000 admin admin123
siqg query "SELECT COUNT(*) FROM users"
siqg status

# 5. CI
git push origin main
# → GitHub Actions runs → green check → coverage badge updates

# 6. Load test
make load-test
# → Screenshot: 100 users, P95 < 50ms for cached queries
```

---

## Final Checklist Before Demo / Placement

```
BACKEND
 ✓ All 4 layers of middleware wired together in order
 ✓ /health returns ok for DB + Redis
 ✓ /api/v1/docs (Swagger) shows all endpoints
 ✓ JWT login works
 ✓ SELECT blocked without auth
 ✓ DROP TABLE returns 400
 ✓ Injection attempt returns 400
 ✓ Same query twice → second is cached=true with lower latency
 ✓ Auto-LIMIT shows in query_diff.executed
 ✓ Slow query fires Discord webhook
 ✓ Honeypot access fires Discord webhook + blocks IP
 ✓ DB stopped → circuit breaker opens → instant 503
 ✓ DB restarted → half-open → probe succeeds → circuit closes
 ✓ NL→SQL generates valid SQL and executes it
 ✓ Explain returns readable English

FRONTEND
 ✓ Monaco editor loads with SQL syntax highlighting
 ✓ Results display correctly
 ✓ Analysis panel shows scan type + suggestions
 ✓ Dashboard charts update every 5 seconds
 ✓ Query history shows last 50 entries
 ✓ /health status page shows green indicators

TESTING
 ✓ pytest passes with 70%+ coverage
 ✓ Coverage badge visible on README
 ✓ GitHub Actions CI green on main
 ✓ Locust report saved (screenshot for README)

DEMO SEQUENCE (practice this until under 3 minutes)
 1. Open Swagger at /api/v1/docs → show the API is self-documenting
 2. Login → get token
 3. Run SELECT on users → show full response with analysis + suggestions
 4. Run same query again → show cached=true, 2ms latency
 5. Try DROP TABLE → show 400
 6. Try injection → show 400
 7. Run slow query → show Discord ping within 2 seconds
 8. Type English question → NL→SQL → show result
 9. Switch to frontend → show live dashboard updating
10. Stop DB container → show instant 503 → restart → show recovery
```

---

_Total estimated time: 10–12 weeks at 4–6 hours/day. Phases 1–4 are the non-negotiable core. Phases 5–6 are what push it from good to exceptional._
