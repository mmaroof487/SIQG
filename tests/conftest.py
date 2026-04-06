"""Test configuration and fixtures."""
import sys
import os
from pathlib import Path
import warnings

# Suppress passlib crypt deprecation warning (not used in our code, internal passlib)
warnings.filterwarnings("ignore", message=".*'crypt' is deprecated.*", category=DeprecationWarning)

# Set test environment variables before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-chars!!!!!")
os.environ.setdefault("DB_PRIMARY_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DB_REPLICA_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Add gateway directory to path
# In Docker: ./gateway:/app, so gateway files are at /app
# Locally: gateway files are at ./gateway
gateway_dir = Path(__file__).parent.parent / "gateway"
if not gateway_dir.exists():
    # Try current working directory (Docker container context)
    gateway_dir = Path.cwd()
sys.path.insert(0, str(gateway_dir))

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from main import app
from utils.db import Base
from unittest.mock import AsyncMock, patch
from middleware.security.auth import create_jwt


# Test database URL (SQLite in-memory)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield Session

    await engine.dispose()


@pytest.fixture
def client():
    """FastAPI test client (synchronous) with mocked Redis."""
    # Mock Redis client for testing
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.incrbyfloat = AsyncMock(return_value=1.0)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.sadd = AsyncMock(return_value=1)
    mock_redis.aclose = AsyncMock(return_value=None)
    
    # Patch Redis connection - make from_url an AsyncMock that returns the mock_redis
    mock_from_url = AsyncMock(return_value=mock_redis)
    
    with patch("redis.asyncio.from_url", mock_from_url):
        with TestClient(app) as client:
            client.app.state.redis = mock_redis
            yield client


@pytest.fixture
async def async_client():
    """FastAPI async test client for use in async tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def event_loop():
    """Event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def token():
    """Generic test token (valid JWT)."""
    return create_jwt("test-user-123", "user")


@pytest.fixture
def admin_token():
    """Admin user test token (valid JWT)."""
    return create_jwt("admin-user-123", "admin")


@pytest.fixture
def readonly_token():
    """Readonly user test token (valid JWT)."""
    return create_jwt("readonly-user-123", "readonly")


@pytest.fixture
def guest_token():
    """Guest user test token (valid JWT)."""
    return create_jwt("guest-user-123", "guest")


@pytest.fixture
async def redis_client():
    """Mock Redis client for testing."""
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.set = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.delete = AsyncMock(return_value=1)
    client.incrbyfloat = AsyncMock(return_value=1.0)
    client.expire = AsyncMock(return_value=True)
    client.sadd = AsyncMock(return_value=1)
    return client


@pytest.fixture
async def primary_session():
    """Primary database session."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield Session

    await engine.dispose()


@pytest.fixture
async def readonly_session():
    """Readonly database session."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield Session

    await engine.dispose()
