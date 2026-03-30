"""FastAPI application and lifespan management."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from config import settings
from utils.db import init_db, close_db
from routers.v1 import auth, query, admin, metrics
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    # Startup
    logger.info("🚀 Starting Queryx Gateway")

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize Redis
    redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client

    # Test Redis connection
    await redis_client.ping()
    logger.info("✅ Redis connected")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Queryx Gateway")
    await close_db()
    await redis_client.aclose()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Queryx - Secure Intelligent Query Gateway",
    description="A 4-layer database middleware for security, performance, intelligence, and observability.",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check(request: Request):
    """Basic health check querying DB and Redis."""
    status_data = {"status": "ok", "db": "ok", "redis": "ok"}
    try:
        await request.app.state.redis.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        status_data["redis"] = "unhealthy"
        status_data["status"] = "degraded"
        
    try:
        from utils.db import PrimarySession
        from sqlalchemy import text
        async with PrimarySession() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        status_data["db"] = "unhealthy"
        status_data["status"] = "degraded"
        
    return status_data


# Status endpoint
@app.get("/api/v1/status")
async def status(request: Request):
    """Gateway status with DB and Redis health."""
    try:
        # Test Redis
        await request.app.state.redis.ping()
        redis_ok = True
    except Exception as e:
        redis_ok = False
        logger.error(f"Redis health check failed: {e}")

    return {
        "status": "ok",
        "redis": "healthy" if redis_ok else "unhealthy",
    }


# Register routers
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(admin.router)
app.include_router(metrics.router)

logger.info("✅ Routers registered")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
