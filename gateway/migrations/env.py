"""Alembic environment for async SQLAlchemy with Argus models."""
import asyncio
import sys
import os

# ── ensure gateway/ is importable ──────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Alembic Config object (gives access to .ini values)
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── import all models so their metadata is populated ──────────────────────────
from utils.db import Base  # noqa: F401
from models import (  # noqa: F401
    User, APIKey, IPRule, Role, QueryWhitelist,
    AuditLog, SlowQuery, SLASnapshot,
    ColumnSecurity,
    UserDatabase, ConnectionPermissions,
)
# Import newer models added after initial migration — required for autogenerate
from models.dek_history import DEKHistory  # noqa: F401
from models.encryption_audit import EncryptionAuditLog  # noqa: F401
from models.migration_job import MigrationJob  # noqa: F401

target_metadata = Base.metadata

# ── read DATABASE_URL from environment (docker-compose injects it) ─────────────
def get_url() -> str:
    """Prefer DB_PRIMARY_URL env var; fall back to alembic.ini sqlalchemy.url."""
    url = os.getenv("DB_PRIMARY_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "No database URL found. Set DB_PRIMARY_URL env var or "
            "sqlalchemy.url in alembic.ini."
        )
    # Alembic sync driver needs psycopg2, not asyncpg.
    # For offline mode we don't need a real URL.
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    """Run migrations without a DB connection (generates SQL script)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    raw_url = os.getenv("DB_PRIMARY_URL") or config.get_main_option("sqlalchemy.url")
    if not raw_url:
        raise RuntimeError("DB_PRIMARY_URL is required for online migrations.")

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = raw_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
