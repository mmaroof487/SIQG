"""
Multi-Database Workbench — Connections Router (Phase B)

Endpoints:
    POST   /api/v1/connections                       Register a new external database
    GET    /api/v1/connections                       List all connections for current user
    GET    /api/v1/connections/{connection_id}       Get one connection (masked conn string)
    DELETE /api/v1/connections/{connection_id}       Soft-delete a connection
    POST   /api/v1/connections/{connection_id}/test  Test connectivity to external DB
    POST   /api/v1/connections/{connection_id}/encryption  Add per-column encryption rule
    DELETE /api/v1/connections/{connection_id}/encryption/{config_id}  Remove encryption rule

Security:
    - All endpoints require JWT or API key authentication.
    - Ownership is enforced: users can only manage their own connections.
    - Connection strings are encrypted at rest using AES-256-GCM before storage.
    - Connections are decrypted only in memory for connectivity tests.

Constraints:
    - Existing pipeline (queries without connection_id) is completely unchanged.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, delete

from middleware.security.auth import get_current_user
from middleware.security.encryption import encrypt_value, decrypt_value
from models.user_database import UserDatabase, ColumnEncryptionConfig
from utils.db import PrimarySession
from utils.logger import get_logger
from utils.connection_manager import test_connection

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


def _safe_user_uuid(user_id: str) -> uuid.UUID:
    """Convert user_id to UUID, falling back to deterministic uuid5 if not parseable."""
    try:
        return uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        # JWT test fixtures use string IDs like 'admin-user-123'
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id))


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class ConnectionCreateRequest(BaseModel):
    display_name: str
    db_type: str = "postgres"
    conn_str: str  # plain-text — will be encrypted before storage


class ConnectionResponse(BaseModel):
    id: str
    display_name: str
    db_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # conn_str intentionally omitted — never returned to client


class ConnectionTestResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class ColumnEncryptionCreateRequest(BaseModel):
    table_name: str
    column_name: str


class ColumnEncryptionResponse(BaseModel):
    id: int
    connection_id: str
    table_name: str
    column_name: str
    created_at: datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _check_db_type(db_type: str):
    allowed = {"postgres", "mysql", "sqlite"}
    if db_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported db_type '{db_type}'. Must be one of: {sorted(allowed)}"
        )


def _conn_to_response(conn: UserDatabase) -> ConnectionResponse:
    return ConnectionResponse(
        id=str(conn.id),
        display_name=conn.display_name,
        db_type=conn.db_type,
        is_active=conn.is_active,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


async def _get_own_connection(
    session,
    connection_id: str,
    user_id: str,
) -> UserDatabase:
    """
    Load a UserDatabase row and verify ownership.
    Raises 404 if missing or not owned by the requesting user.
    """
    try:
        conn_uuid = uuid.UUID(connection_id)
        user_uuid = _safe_user_uuid(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection_id format")

    stmt = select(UserDatabase).where(
        UserDatabase.id == conn_uuid,
        UserDatabase.user_id == user_uuid,
    )
    result = await session.execute(stmt)
    row = result.scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return row


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ConnectionResponse, status_code=201)
async def register_connection(
    request: Request,
    payload: ConnectionCreateRequest,
    user=Depends(get_current_user),
):
    """
    Register a new external database connection for the authenticated user.

    The connection string is encrypted with AES-256-GCM before being persisted.
    The plaintext connection string is never stored or logged.
    """
    _check_db_type(payload.db_type)

    user_id = request.state.user_id

    # Encrypt the connection string before storage
    conn_str_enc = encrypt_value(payload.conn_str)

    async with PrimarySession() as session:
        new_conn = UserDatabase(
            id=uuid.uuid4(),
            user_id=_safe_user_uuid(user_id),
            display_name=payload.display_name.strip(),
            db_type=payload.db_type,
            conn_str_enc=conn_str_enc,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(new_conn)
        await session.commit()
        await session.refresh(new_conn)
        logger.info(f"Connection registered: {new_conn.id} by user {user_id}")
        return _conn_to_response(new_conn)


@router.get("", response_model=List[ConnectionResponse])
async def list_connections(
    request: Request,
    user=Depends(get_current_user),
):
    """
    List all database connections owned by the authenticated user.

    Connection strings are never returned; only metadata is exposed.
    """
    user_id = request.state.user_id
    try:
        user_uuid = _safe_user_uuid(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    async with PrimarySession() as session:
        stmt = select(UserDatabase).where(
            UserDatabase.user_id == user_uuid,
        ).order_by(UserDatabase.created_at.desc())
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [_conn_to_response(r) for r in rows]


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Get metadata for a single connection owned by the authenticated user.

    Connection strings are never returned in API responses.
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        conn = await _get_own_connection(session, connection_id, str(user_id))
        return _conn_to_response(conn)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Soft-delete (deactivate) a connection.

    Sets is_active=False and removes the cached connection from Redis.
    The row is kept for audit purposes but will no longer be routable.

    To hard-delete, use the admin endpoint (not implemented in this phase).
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        conn = await _get_own_connection(session, connection_id, str(user_id))
        conn.is_active = False
        conn.updated_at = datetime.utcnow()
        await session.commit()
        logger.info(f"Connection {connection_id} soft-deleted by user {user_id}")

    # Purge connection-scoped cache entries
    try:
        from utils.connection_manager import invalidate_connection_cache
        await invalidate_connection_cache(request.app.state.redis, connection_id)
    except Exception as cache_err:
        logger.warning(f"Cache purge failed for deleted connection {connection_id}: {cache_err}")


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_connection_endpoint(
    connection_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Test connectivity to an external database.

    Decrypts the stored connection string in memory, opens a transient
    asyncpg connection, immediately closes it, and returns the result.
    The plaintext connection string is never logged.
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        conn = await _get_own_connection(session, connection_id, str(user_id))
        if not conn.is_active:
            raise HTTPException(status_code=400, detail="Connection is inactive")

        # Decrypt conn string in memory only — never logged or persisted
        try:
            plain_conn_str = decrypt_value(conn.conn_str_enc)
        except Exception as dec_err:
            logger.error(f"Connection string decryption failed for {connection_id}: {dec_err}")
            return ConnectionTestResponse(
                ok=False,
                error="Failed to decrypt connection string. Contact support."
            )

    result = await test_connection(plain_conn_str, timeout=10.0)
    logger.info(
        f"Connection test for {connection_id} by user {user_id}: "
        f"{'OK' if result['ok'] else result.get('error', 'FAIL')}"
    )
    return ConnectionTestResponse(**result)


@router.post(
    "/{connection_id}/encryption",
    response_model=ColumnEncryptionResponse,
    status_code=201,
)
async def add_column_encryption(
    connection_id: str,
    payload: ColumnEncryptionCreateRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Add a per-column encryption rule for an external database table.

    When a column is registered here, any INSERT or UPDATE through Argus
    using this connection will transparently encrypt the value with AES-256-GCM
    before it reaches the database, and decrypt it on SELECT.

    Duplicate (connection, table, column) combinations return 409 Conflict.
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        # Verify ownership first
        await _get_own_connection(session, connection_id, str(user_id))

        # Check for duplicate
        try:
            conn_uuid = uuid.UUID(connection_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid connection_id format")

        dup_stmt = select(ColumnEncryptionConfig).where(
            ColumnEncryptionConfig.connection_id == conn_uuid,
            ColumnEncryptionConfig.table_name == payload.table_name,
            ColumnEncryptionConfig.column_name == payload.column_name,
        )
        dup_result = await session.execute(dup_stmt)
        if dup_result.scalars().first():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Encryption config already exists for "
                    f"{payload.table_name}.{payload.column_name}"
                ),
            )

        new_config = ColumnEncryptionConfig(
            connection_id=conn_uuid,
            table_name=payload.table_name.strip(),
            column_name=payload.column_name.strip(),
            created_at=datetime.utcnow(),
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)

        logger.info(
            f"Column encryption added: {connection_id}/"
            f"{payload.table_name}.{payload.column_name} by user {user_id}"
        )
        return ColumnEncryptionResponse(
            id=new_config.id,
            connection_id=str(new_config.connection_id),
            table_name=new_config.table_name,
            column_name=new_config.column_name,
            created_at=new_config.created_at,
        )


@router.delete("/{connection_id}/encryption/{config_id}", status_code=204)
async def remove_column_encryption(
    connection_id: str,
    config_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Remove a per-column encryption rule.

    Only the owner of the connection can remove encryption rules.
    After removal, new writes to that column will be stored in plaintext;
    existing encrypted values are NOT automatically re-decrypted.
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        # Verify ownership
        await _get_own_connection(session, connection_id, str(user_id))

        try:
            conn_uuid = uuid.UUID(connection_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid connection_id format")

        stmt = select(ColumnEncryptionConfig).where(
            ColumnEncryptionConfig.id == config_id,
            ColumnEncryptionConfig.connection_id == conn_uuid,
        )
        result = await session.execute(stmt)
        config = result.scalars().first()
        if config is None:
            raise HTTPException(
                status_code=404,
                detail=f"Encryption config {config_id} not found for connection {connection_id}"
            )

        await session.delete(config)
        await session.commit()
        logger.info(
            f"Column encryption removed: config {config_id} from "
            f"{connection_id} by user {user_id}"
        )
