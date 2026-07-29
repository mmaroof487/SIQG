"""FastAPI application and lifespan management."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import redis.asyncio as aioredis
from config import settings
from utils.db import init_db, close_db
# IMPORTANT: Import models BEFORE init_db() so SQLAlchemy registers them with Base
from models import User, APIKey, IPRule, Role, AuditLog, SlowQuery, SLASnapshot, QueryWhitelist
from models.user_database import UserDatabase, ConnectionPermissions
from models.column_security import ColumnSecurity
from routers.v1 import auth, query, admin, metrics, ai
from routers.v1.connections import router as connections_router
from middleware.security.auth import get_current_user
from middleware.security.rate_limiter import check_rate_limit
from utils.logger import get_logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

# Configure logging
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    # Startup
    logger.info("🚀 Starting Argus Gateway")

    # 1. Configuration Validation
    _KNOWN_DUMMY_KEYS = {
        "dummy_development_master_key_123",
        "12345678901234567890123456789012",
        "",
    }
    if settings.key_provider == "env" and settings.encryption_key in _KNOWN_DUMMY_KEYS:
        logger.error("❌ CRITICAL: ENCRYPTION_KEY is not set to a real value. Refusing to start.")
        raise RuntimeError("ENCRYPTION_KEY is not set to a real value. Refusing to start.")
    
    if settings.ai_enabled and settings.ai_provider != "mock":
        if settings.ai_provider == "openai" and not settings.openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY")
        if settings.ai_provider == "gemini" and not settings.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")
        if settings.ai_provider == "groq" and not settings.groq_api_key:
            raise RuntimeError("Missing GROQ_API_KEY")
    
    logger.info("✅ Configuration validated")

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize Redis
    try:
        redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
        app.state.redis = redis_client
        # Test Redis connection
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ CRITICAL: Redis connection failed: {e}")
        raise RuntimeError("Redis unreachable")

    # Initialize Key Manager
    from middleware.security.key_manager import key_manager
    try:
        await key_manager.initialize()
        logger.info("✅ KeyManager initialized")
    except Exception as e:
        logger.error(f"❌ CRITICAL: KeyManager initialization failed: {e}")
        raise RuntimeError("Master key provider unavailable")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Argus Gateway")
    await close_db()
    await redis_client.aclose()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Argus - Secure Intelligent Query Gateway",
    description="A 6-layer database middleware for security, performance, execution, observability, hardening, and AI intelligence.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Instrument the FastAPI app with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
import sqlalchemy.exc

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Ensure raw DB exceptions aren't leaked to client."""
    detail_str = str(exc.detail)
    if "sqlalchemy." in detail_str or "asyncpg." in detail_str or "UndefinedTable" in detail_str:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Query execution failed due to syntax or database error.",
                    "details": "Verify table and column names or SQL syntax."
                }
            }
        )
        
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
        
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware

async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Global Rate Limiting by IP (100 req/min)
    redis = getattr(request.app.state, "redis", None)
    if redis:
        client_ip = request.client.host if request.client else "unknown"
        # Only rate limit if IP is known
        if client_ip != "unknown":
            import time
            current_bucket = int(time.time()) // 60
            limit_key = f"argus:global_rl:{client_ip}:{current_bucket}"
            try:
                count = await redis.incr(limit_key)
                if count == 1:
                    await redis.expire(limit_key, 120)
                if count > 100:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please slow down."},
                    )
            except Exception as e:
                logger.error(f"Global rate limit Redis error: {e}")

    # 2. Process request
    response = await call_next(request)

    # 3. Add Security Headers
    if settings.environment != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "connect-src 'self' https://cdn.jsdelivr.net; "
        "frame-ancestors 'none'"
    )

    return response

# 1. Security and rate limit (Innermost of these three)
app.add_middleware(BaseHTTPMiddleware, dispatch=security_and_rate_limit_middleware)

# 2. Trust proxy headers — restrict to internal networks only (Docker bridge + localhost)
# NEVER use "*" in production: it allows X-Forwarded-For spoofing by any client.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1", "::1", "172.16.0.0/12", "10.0.0.0/8", "192.168.0.0/16"])

# 3. Add CORS middleware (Outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"],
)


import time
import json
from datetime import datetime, timezone
START_TIME = time.time()

# Health check endpoints
@app.get("/health/live")
async def liveness_check():
    """Liveness probe - indicates if the container is running."""
    return {"status": "alive", "uptime_seconds": int(time.time() - START_TIME)}

@app.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness probe - indicates if the system can accept traffic."""
    status_data = {
        "status": "ready", 
        "database": True,
        "redis": True,
        "llm": settings.ai_enabled,
        "key_manager": True,
        "uptime_seconds": int(time.time() - START_TIME),
        "last_check": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }
    
    try:
        await request.app.state.redis.ping()
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        status_data["redis"] = False
        status_data["status"] = "not_ready"

    try:
        from utils.db import PrimarySession
        from sqlalchemy import text
        async with PrimarySession() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"DB readiness check failed: {e}")
        status_data["database"] = False
        status_data["status"] = "not_ready"

    if status_data["status"] == "not_ready":
        from fastapi import Response
        return Response(content=json.dumps(status_data), status_code=503, media_type="application/json")
        
    return status_data

@app.get("/version")
async def version_info():
    """Version and build information."""
    return {
        "version": "1.0.0",
        "build": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "git_commit": "unknown"  # This could be populated via env vars in a real CI setup
    }


# Register routers
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(admin.router)
app.include_router(metrics.router)
app.include_router(ai.router)
app.include_router(connections_router)

logger.info("✅ Routers registered")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

