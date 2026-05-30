"""
Connection manager utilities for the Multi-Database Workbench (Phase B).

Helpers:
- get_user_database()          - Load a UserDatabase by connection_id, enforcing ownership
- test_connection()            - Validate an external connection string by connecting to it
- get_connection_encrypted_columns() - Return encrypted column names for a given connection+table
- invalidate_connection_cache() - Purge all cache keys scoped to a connection_id
"""
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_user_database(
    session: AsyncSession,
    connection_id: str,
    user_id: str,
):
    """
    Load a UserDatabase row for the given connection_id, enforcing that it
    belongs to the requesting user.

    Returns:
        UserDatabase ORM object, or None if not found / not owned by user.
    """
    from models.user_database import UserDatabase
    import uuid

    try:
        conn_uuid = uuid.UUID(str(connection_id))
        user_uuid = uuid.UUID(str(user_id))
    except ValueError:
        return None

    stmt = select(UserDatabase).where(
        UserDatabase.id == conn_uuid,
        UserDatabase.user_id == user_uuid,
        UserDatabase.is_active == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def test_connection(conn_str: str, timeout: float = 10.0) -> dict:
    """
    Test an asyncpg connection string by opening and immediately closing a
    connection.

    Returns:
        {"ok": True} on success.
        {"ok": False, "error": "<message>"} on failure.
    """
    try:
        conn = await asyncio.wait_for(asyncpg.connect(conn_str), timeout=timeout)
        await conn.close()
        return {"ok": True}
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"Connection timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def get_connection_encrypted_columns(
    session: AsyncSession,
    connection_id: str,
    table_name: str,
) -> list[str]:
    """
    Return the list of column names that should be AES-encrypted for the
    given connection and table.

    Args:
        session:       Open SQLAlchemy async session.
        connection_id: UUID of the UserDatabase connection.
        table_name:    Name of the table being queried/written.

    Returns:
        List of column name strings (may be empty).
    """
    from models.user_database import ColumnEncryptionConfig
    import uuid

    if not table_name:
        return []

    try:
        conn_uuid = uuid.UUID(str(connection_id))
    except ValueError:
        return []

    stmt = select(ColumnEncryptionConfig.column_name).where(
        ColumnEncryptionConfig.connection_id == conn_uuid,
        ColumnEncryptionConfig.table_name == table_name,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def invalidate_connection_cache(redis, connection_id: str) -> int:
    """
    Purge all Redis cache keys scoped to a connection_id.

    Cache keys for external connections use the pattern:
        argus:cache:{connection_id}:*

    Returns:
        Number of keys deleted.
    """
    pattern = f"argus:cache:{connection_id}:*"
    deleted = 0
    cursor = b"0"
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
            deleted += len(keys)
        if cursor == b"0" or cursor == 0:
            break
    logger.debug(f"Invalidated {deleted} cache key(s) for connection {connection_id}")
    return deleted
