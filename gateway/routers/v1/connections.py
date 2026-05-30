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


class ColumnEncryptionResponse(BaseModel):
    id: int
    connection_id: str
    table_name: str
    column_name: str
    created_at: datetime


class ConnectionResponse(BaseModel):
    id: str
    display_name: str
    db_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    column_encryption_configs: Optional[List[ColumnEncryptionResponse]] = None


class ConnectionTestResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class ColumnEncryptionCreateRequest(BaseModel):
    table_name: str
    column_name: str


class ColumnSchema(BaseModel):
    name: str
    type: str
    pk: bool
    nullable: bool


class TableSchema(BaseModel):
    name: str
    columns: List[ColumnSchema]


class SchemaResponse(BaseModel):
    schema: str
    tables: List[TableSchema]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _check_db_type(db_type: str):
    allowed = {"postgres", "mysql", "sqlite"}
    if db_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported db_type '{db_type}'. Must be one of: {sorted(allowed)}"
        )


def _conn_to_response(conn: UserDatabase) -> ConnectionResponse:
    configs = []
    if conn.column_encryption_configs:
        for c in conn.column_encryption_configs:
            configs.append(ColumnEncryptionResponse(
                id=c.id,
                connection_id=str(c.connection_id),
                table_name=c.table_name,
                column_name=c.column_name,
                created_at=c.created_at
            ))
    return ConnectionResponse(
        id=str(conn.id),
        display_name=conn.display_name,
        db_type=conn.db_type,
        is_active=conn.is_active,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
        column_encryption_configs=configs,
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
        # Also invalidate schema cache
        await request.app.state.redis.delete(f"schema:{connection_id}")
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


@router.get("/{connection_id}/schema", response_model=List[SchemaResponse])
async def get_connection_schema(
    connection_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Get the dynamic schema (tables and columns) of an external database connection.
    Includes caching in Redis for 5 minutes (300 seconds).
    """
    import json
    import asyncpg

    user_id = request.state.user_id
    redis_client = request.app.state.redis
    cache_key = f"schema:{connection_id}"

    # Check cache first
    try:
        cached_schema = await redis_client.get(cache_key)
        if cached_schema:
            logger.info(f"Schema cache hit for connection {connection_id}")
            return json.loads(cached_schema)
    except Exception as cache_read_err:
        logger.warning(f"Failed to read schema cache for {connection_id}: {cache_read_err}")

    # Cache miss - retrieve connection info and fetch schema
    import uuid
    async with PrimarySession() as session:
        try:
            conn_uuid = uuid.UUID(connection_id)
            user_uuid = _safe_user_uuid(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid connection_id format")

        exist_stmt = select(UserDatabase).where(UserDatabase.id == conn_uuid)
        exist_res = await session.execute(exist_stmt)
        conn = exist_res.scalars().first()
        if conn is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        if conn.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Not owner of connection")

        if not conn.is_active:
            raise HTTPException(status_code=400, detail="Connection is inactive")

        try:
            plain_conn_str = decrypt_value(conn.conn_str_enc)
        except Exception as dec_err:
            logger.error(f"Connection string decryption failed for {connection_id}: {dec_err}")
            raise HTTPException(status_code=500, detail="Failed to decrypt connection credentials")

    try:
        # Establish transient connection to target database
        import asyncio
        asyncpg_conn = await asyncio.wait_for(asyncpg.connect(plain_conn_str), timeout=10.0)
    except Exception as conn_err:
        logger.error(f"Failed to connect to target database {connection_id} for schema: {conn_err}")
        raise HTTPException(
            status_code=400, 
            detail=f"Could not connect to database: {str(conn_err)[:200]}"
        )

    try:
        # Query column metadata and primary key constraints
        query = """
            SELECT 
                c.table_schema, 
                c.table_name, 
                c.column_name, 
                c.data_type,
                c.is_nullable,
                EXISTS (
                    SELECT 1 
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                      AND kcu.table_schema = c.table_schema
                      AND kcu.table_name = c.table_name
                      AND kcu.column_name = c.column_name
                ) as is_pk
            FROM information_schema.columns c
            WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY c.table_schema, c.table_name, c.ordinal_position;
        """
        rows = await asyncpg_conn.fetch(query)
    except Exception as query_err:
        logger.error(f"Failed to query schema on target database {connection_id}: {query_err}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to query database schema: {str(query_err)[:200]}"
        )
    finally:
        await asyncpg_conn.close()

    # Process and group results by schema and table
    schema_map = {}
    for r in rows:
        sch_name = r["table_schema"]
        tbl_name = r["table_name"]
        col_name = r["column_name"]
        col_type = r["data_type"]
        nullable = r["is_nullable"] == "YES"
        is_pk = r["is_pk"]

        if sch_name not in schema_map:
            schema_map[sch_name] = {}
        if tbl_name not in schema_map[sch_name]:
            schema_map[sch_name][tbl_name] = []

        schema_map[sch_name][tbl_name].append({
            "name": col_name,
            "type": col_type,
            "pk": is_pk,
            "nullable": nullable
        })

    response_data = []
    for sch_name, tables in schema_map.items():
        tbl_list = []
        for tbl_name, columns in tables.items():
            tbl_list.append({
                "name": tbl_name,
                "columns": columns
            })
        response_data.append({
            "schema": sch_name,
            "tables": tbl_list
        })

    # Cache in Redis with 5-minute TTL (300 seconds)
    try:
        await redis_client.setex(cache_key, 300, json.dumps(response_data))
    except Exception as cache_err:
        logger.warning(f"Failed to cache schema for connection {connection_id}: {cache_err}")

    return response_data
