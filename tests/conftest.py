"""Test configuration and fixtures."""
import sys
import os
from pathlib import Path

# Set test environment variables before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-chars!!!!!")
os.environ.setdefault("DB_PRIMARY_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DB_REPLICA_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Add gateway directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "gateway"))

import pytest
from fastapi.testclient import TestClient
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from main import app
from utils.db import Base


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
    """FastAPI test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def event_loop():
    """Event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
