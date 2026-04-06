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
from unittest.mock import AsyncMock, patch, MagicMock
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
    # Create a real Redis mock class that properly handles all operations
    class MockRedis:
        def __init__(self):
            self.data = {}
            
        async def ping(self):
            return True
            
        async def get(self, key):
            return self.data.get(key)
            
        async def mget(self, *keys):
            """Get multiple keys."""
            return [self.data.get(k) for k in keys]
            
        async def set(self, key, value):
            self.data[key] = value
            return True
            
        async def delete(self, key):
            if key in self.data:
                del self.data[key]
            return 1
            
        async def exists(self, key):
            return 0  # Always return 0 (not in blocklist)
            
        async def sismember(self, key, member):
            return 0  # Always return 0 (not in allowlist)
            
        async def incr(self, key, amount=1):
            """Increment integer value"""
            val = int(self.data.get(key, 0)) + amount
            self.data[key] = val
            return val
            
        async def incrbyfloat(self, key, amount=1.0):
            """Increment float value"""
            val = float(self.data.get(key, 0)) + amount
            self.data[key] = val
            return val
            
        async def expire(self, key, seconds):
            return True
            
        async def ttl(self, key):
            """Return TTL in seconds (-1 if no expiry, -2 if key doesn't exist)."""
            return -1  # Pretend keys never expire
            
        async def sadd(self, key, member):
            return 1
            
        async def setex(self, key, seconds, value):
            self.data[key] = value
            return True
            
        def pipeline(self):
            """Return a chainable pipeline mock"""
            mock_pipe = MagicMock()
            mock_pipe.lpush = MagicMock(return_value=mock_pipe)
            mock_pipe.rpush = MagicMock(return_value=mock_pipe)
            mock_pipe.incr = MagicMock(return_value=mock_pipe)
            mock_pipe.incrby = MagicMock(return_value=mock_pipe)
            mock_pipe.expire = MagicMock(return_value=mock_pipe)
            mock_pipe.execute = AsyncMock(return_value=[1, 1, 1])
            return mock_pipe
            
        async def lpush(self, key, value):
            """Push to left of list."""
            if key not in self.data:
                self.data[key] = []
            self.data[key].insert(0, value)
            return len(self.data[key])
            
        async def lrange(self, key, start, end):
            """Get range from list."""
            if key not in self.data:
                return []
            lst = self.data.get(key, [])
            if end == -1:
                return lst[start:]
            return lst[start:end+1]
            
        async def aclose(self):
            return None
    
    mock_redis = MockRedis()
    
    # Patch IP filter at the call site to skip checks in tests
    # Also patch Redis for operations that aren't skipped
    with patch("redis.asyncio.from_url", new_callable=AsyncMock, return_value=mock_redis):
        with patch("gateway.routers.v1.query.check_ip_filter", new_callable=AsyncMock):
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
    """Generic test token (valid JWT) - use readonly role."""
    return create_jwt("test-user-123", "readonly")


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
