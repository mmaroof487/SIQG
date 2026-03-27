"""Database connection and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

# Declarative base for all models
Base = declarative_base()

# Primary (write) engine
primary_engine = create_async_engine(
    settings.db_primary_url,
    pool_size=settings.db_pool_min,
    max_overflow=settings.db_pool_max - settings.db_pool_min,
    pool_timeout=settings.db_pool_timeout_seconds,
    echo=False,
    pool_pre_ping=True,
)

# Replica (read) engine
replica_engine = create_async_engine(
    settings.db_replica_url,
    pool_size=settings.db_pool_min,
    max_overflow=settings.db_pool_max - settings.db_pool_min,
    pool_timeout=settings.db_pool_timeout_seconds,
    echo=False,
    pool_pre_ping=True,
)

# Session makers
PrimarySession = async_sessionmaker(
    primary_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

ReplicaSession = async_sessionmaker(
    replica_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_primary_db():
    """Dependency for write operations."""
    async with PrimarySession() as session:
        yield session


async def get_replica_db():
    """Dependency for read operations."""
    async with ReplicaSession() as session:
        yield session


async def init_db():
    """Create all tables."""
    async with primary_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close all connections."""
    await primary_engine.dispose()
    await replica_engine.dispose()
