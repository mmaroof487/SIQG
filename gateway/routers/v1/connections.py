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
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from middleware.security.auth import get_current_user
from middleware.security.encryption import encrypt_value, decrypt_value
from models.user_database import UserDatabase
from models.column_security import ColumnSecurity
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


import re as _re
_DSN_PATTERN = _re.compile(
    r"(?:postgresql|postgres|mysql|redis)(?:\+\w+)?://[^@\s]+@[^\s/]+",
    _re.IGNORECASE,
)


def _sanitize_db_error(err_msg: str, max_len: int = 120) -> str:
    """Strip any embedded DSNs from error messages before logging.

    asyncpg sometimes includes the full connection string (with password)
    in error messages.  This helper masks credential portions before they
    reach log files.
    """
    sanitized = _DSN_PATTERN.sub("[REDACTED_DSN]", str(err_msg))
    return sanitized[:max_len]


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class ConnectionCreateRequest(BaseModel):
    display_name: str
    db_type: str = "postgres"
    conn_str: str  # plain-text — will be encrypted before storage


class ColumnSecurityResponse(BaseModel):
    id: int
    connection_id: str
    schema_name: str
    table_name: str
    column_name: str
    classification_method: int
    is_encrypted: bool
    created_at: datetime


class ConnectionResponse(BaseModel):
    id: str
    display_name: str
    db_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    column_security_configs: Optional[List[ColumnSecurityResponse]] = None


class ConnectionTestResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class ColumnSecurityCreateRequest(BaseModel):
    schema_name: str = "public"
    table_name: str
    column_name: str
    classification_method: int = 3
    is_encrypted: bool = True


class ColumnSchema(BaseModel):
    name: str
    type: str
    pk: bool
    nullable: bool
    fk: Optional[str] = None
    is_encrypted: Optional[bool] = False
    config_id: Optional[int] = None


class TableSchema(BaseModel):
    name: str
    columns: List[ColumnSchema]


class SchemaResponse(BaseModel):
    database_schema: str
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
    if conn.column_security_configs:
        for c in conn.column_security_configs:
            configs.append(ColumnSecurityResponse(
                id=c.id,
                connection_id=str(c.connection_id),
                schema_name=c.schema_name,
                table_name=c.table_name,
                column_name=c.column_name,
                classification_method=c.classification_method,
                is_encrypted=c.is_encrypted,
                created_at=c.created_at
            ))
    return ConnectionResponse(
        id=str(conn.id),
        display_name=conn.display_name,
        db_type=conn.db_type,
        is_active=conn.is_active,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
        column_security_configs=configs,
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

    stmt = select(UserDatabase).options(
        selectinload(UserDatabase.column_security_configs)
    ).where(
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

    # Test connection before allowing creation
    logger.info("Testing new connection string during registration: [MASKED]")
    test_res = await test_connection(payload.conn_str, timeout=5.0)
    if not test_res.get("ok"):
        logger.error(
            f"Connection test failed during registration: {_sanitize_db_error(test_res.get('error', 'unknown'))}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to database: {test_res.get('error')}"
        )

    # Generate DEK for this specific connection
    import os
    from middleware.security.key_manager import key_manager
    dek = os.urandom(32)
    
    # Encrypt DEK with the master wrapping key
    wrapping_key = key_manager.get_dek_wrapping_key()
    encrypted_dek = encrypt_value(dek.hex(), wrapping_key)

    # Encrypt the connection string using the DEK
    conn_str_enc = encrypt_value(payload.conn_str, dek)

    async with PrimarySession() as session:
        new_conn = UserDatabase(
            id=uuid.uuid4(),
            user_id=_safe_user_uuid(user_id),
            display_name=payload.display_name.strip(),
            db_type=payload.db_type,
            conn_str_enc=conn_str_enc,
            encrypted_dek=encrypted_dek,
            key_version=1,
            is_active=True,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(new_conn)
        await session.commit()
        
        # Reload with relationships
        stmt = select(UserDatabase).options(
            selectinload(UserDatabase.column_security_configs)
        ).where(UserDatabase.id == new_conn.id)
        result = await session.execute(stmt)
        new_conn_loaded = result.scalars().first()
        
        logger.info(f"Connection registered: {new_conn_loaded.id} by user {user_id}")
        return _conn_to_response(new_conn_loaded)


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
        stmt = select(UserDatabase).options(
            selectinload(UserDatabase.column_security_configs)
        ).where(
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
        conn.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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

@router.put("/{connection_id}/restore", response_model=ConnectionResponse)
async def restore_connection(
    connection_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Restore (activate) a soft-deleted connection.
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        conn = await _get_own_connection(session, connection_id, str(user_id))
        if conn.is_active:
            raise HTTPException(status_code=400, detail="Connection is already active")
            
        conn.is_active = True
        conn.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        await session.refresh(conn)
        logger.info(f"Connection {connection_id} restored by user {user_id}")
        
        return _conn_to_response(conn)

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
            from middleware.security.key_manager import key_manager
            
            # If it's an old connection before DEKs, this will fallback gracefully or fail.
            # But we added `encrypted_dek` and `key_version` so we expect them.
            if getattr(conn, "encrypted_dek", None):
                dek = await key_manager.get_dek(str(conn.id), conn.key_version, conn.encrypted_dek)
                plain_conn_str = decrypt_value(conn.conn_str_enc, dek)
            else:
                # Fallback for existing connections (dev mode only)
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
        f"{'OK' if result['ok'] else _sanitize_db_error(result.get('error', 'FAIL'))}"
    )
    return ConnectionTestResponse(**result)


@router.post(
    "/{connection_id}/encryption",
    response_model=ColumnSecurityResponse,
    status_code=201,
)
async def add_column_encryption(
    connection_id: str,
    payload: ColumnSecurityCreateRequest,
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

        dup_stmt = select(ColumnSecurity).where(
            ColumnSecurity.connection_id == conn_uuid,
            ColumnSecurity.schema_name == payload.schema_name,
            ColumnSecurity.table_name == payload.table_name,
            ColumnSecurity.column_name == payload.column_name,
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

        new_config = ColumnSecurity(
            connection_id=conn_uuid,
            schema_name=payload.schema_name.strip(),
            table_name=payload.table_name.strip(),
            column_name=payload.column_name.strip(),
            classification_method=payload.classification_method,
            is_encrypted=payload.is_encrypted,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)

        await request.app.state.redis.delete(f"schema:{connection_id}")

        logger.info(
            f"Column encryption added: {connection_id}/"
            f"{payload.schema_name}.{payload.table_name}.{payload.column_name} by user {user_id}"
        )
        return ColumnSecurityResponse(
            id=new_config.id,
            connection_id=str(new_config.connection_id),
            schema_name=new_config.schema_name,
            table_name=new_config.table_name,
            column_name=new_config.column_name,
            classification_method=new_config.classification_method,
            is_encrypted=new_config.is_encrypted,
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

        stmt = select(ColumnSecurity).where(
            ColumnSecurity.id == config_id,
            ColumnSecurity.connection_id == conn_uuid,
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
        
        await request.app.state.redis.delete(f"schema:{connection_id}")
        
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
            from middleware.security.key_manager import key_manager
            if getattr(conn, "encrypted_dek", None):
                dek = await key_manager.get_dek(str(conn.id), conn.key_version, conn.encrypted_dek)
                plain_conn_str = decrypt_value(conn.conn_str_enc, dek)
            else:
                plain_conn_str = decrypt_value(conn.conn_str_enc)
        except Exception as dec_err:
            logger.error(f"Connection string decryption failed for {connection_id}: {dec_err}")
            raise HTTPException(status_code=500, detail="Failed to decrypt connection credentials")

    try:
        # Establish transient connection to target database
        import asyncio
        asyncpg_conn = await asyncio.wait_for(asyncpg.connect(plain_conn_str), timeout=10.0)
    except Exception as conn_err:
        logger.error(f"Failed to connect to target database {connection_id} for schema")
        raise HTTPException(
            status_code=400, 
            detail="Could not connect to database. Please verify credentials and network access."
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
                ) as is_pk,
                (
                    SELECT ccu.table_name || '.' || ccu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu 
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND kcu.table_schema = c.table_schema
                      AND kcu.table_name = c.table_name
                      AND kcu.column_name = c.column_name
                    LIMIT 1
                ) as fk_reference
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

    # Fetch existing encryption configs for this connection
    async with PrimarySession() as session:
        from models.column_security import ColumnSecurity
        sec_stmt = select(ColumnSecurity).where(ColumnSecurity.connection_id == conn_uuid)
        sec_res = await session.execute(sec_stmt)
        sec_configs = sec_res.scalars().all()
        
    sec_lookup = {
        f"{c.schema_name}.{c.table_name}.{c.column_name}": c
        for c in sec_configs
    }

    # Process and group results by schema and table
    schema_map = {}
    for r in rows:
        sch_name = r["table_schema"]
        tbl_name = r["table_name"]
        col_name = r["column_name"]
        col_type = r["data_type"]
        nullable = r["is_nullable"] == "YES"
        is_pk = r["is_pk"]
        fk_ref = r["fk_reference"]

        sec = sec_lookup.get(f"{sch_name}.{tbl_name}.{col_name}")

        if sch_name not in schema_map:
            schema_map[sch_name] = {}
        if tbl_name not in schema_map[sch_name]:
            schema_map[sch_name][tbl_name] = []

        schema_map[sch_name][tbl_name].append({
            "name": col_name,
            "type": col_type,
            "pk": is_pk,
            "nullable": nullable,
            "fk": fk_ref,
            "is_encrypted": sec.is_encrypted if sec else False,
            "config_id": sec.id if sec else None
        })

    # Collect all tables across all schemas for inference
    all_tables = set()
    for sch, tables_dict in schema_map.items():
        for t_name in tables_dict.keys():
            all_tables.add(t_name)
            
    # Heuristic inference pass
    for sch_name, tables in schema_map.items():
        for tbl_name, columns in tables.items():
            for col in columns:
                if col.get("fk") is not None:
                    col["fk_inferred"] = False
                    col["fk_confidence"] = 1.0
                else:
                    c_name = col["name"]
                    inferred_fk = None
                    confidence = 0.0
                    
                    # Strong Match: {table_singular}_id -> {table}.id
                    if c_name.endswith("_id"):
                        base = c_name[:-3]
                        if base + "s" in all_tables:
                            inferred_fk = f"{base}s.id"
                            confidence = 0.95
                        elif base in all_tables:
                            inferred_fk = f"{base}.id"
                            confidence = 0.95
                    
                    # Medium Match: common alias to users table
                    if not inferred_fk and c_name in ["owner_id", "creator_id", "author_id", "owner", "creator"]:
                        if "users" in all_tables:
                            inferred_fk = "users.id"
                            confidence = 0.80
                            
                    # Weak Match: {base}_code -> {base}s.code
                    if not inferred_fk and c_name.endswith("_code"):
                        base = c_name[:-5]
                        if base + "s" in all_tables:
                            inferred_fk = f"{base}s.code"
                            confidence = 0.60
                        elif base + "es" in all_tables:
                            inferred_fk = f"{base}es.code"
                            confidence = 0.60
                            
                    if inferred_fk:
                        col["fk"] = inferred_fk
                        col["fk_inferred"] = True
                        col["fk_confidence"] = confidence
                    else:
                        col["fk_inferred"] = False
                        col["fk_confidence"] = 1.0

    response_data = []
    for sch_name, tables in schema_map.items():
        tbl_list = []
        for tbl_name, columns in tables.items():
            tbl_list.append({
                "name": tbl_name,
                "columns": columns
            })
        response_data.append({
            "database_schema": sch_name,
            "tables": tbl_list
        })

    # Cache in Redis with 5-minute TTL (300 seconds)
    try:
        await redis_client.setex(cache_key, 300, json.dumps(response_data))
    except Exception as cache_err:
        logger.warning(f"Failed to cache schema for connection {connection_id}: {cache_err}")

    return response_data

class IntelligenceRequest(BaseModel):
    schema_metadata: str

@router.post("/{connection_id}/intelligence")
async def get_connection_intelligence(
    connection_id: str,
    payload: IntelligenceRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Generate or retrieve AI intelligence for a given schema.
    Uses schema_hash to cache the results so we don't call the LLM repeatedly
    unless the schema actually changes.
    """
    import json
    import hashlib
    from routers.v1.ai import call_llm, SYSTEM_PROMPT_SCHEMA_INTELLIGENCE

    # Verify ownership
    async with PrimarySession() as session:
        await _get_own_connection(session, connection_id, str(request.state.user_id))

    redis_client = request.app.state.redis
    schema_hash = hashlib.sha256(payload.schema_metadata.encode('utf-8')).hexdigest()
    cache_key = f"argus:intelligence:{connection_id}:{schema_hash}"

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"Intelligence cache hit for {connection_id}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Intelligence cache read failed: {e}")

    logger.info(f"Intelligence cache miss for {connection_id}. Calling LLM...")
    prompt = f"Analyze this schema:\n{payload.schema_metadata}"
    result = await call_llm(SYSTEM_PROMPT_SCHEMA_INTELLIGENCE, prompt)
    
    if result.startswith("ERROR:"):
        raise HTTPException(status_code=500, detail=result)

    cleaned_result = result.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned_result)
        # Cache for 24 hours
        await redis_client.setex(cache_key, 86400, json.dumps(parsed))
        return parsed
    except json.JSONDecodeError:
        logger.error(f"Failed to parse intelligence JSON: {result}")
        raise HTTPException(status_code=500, detail="Failed to generate schema intelligence JSON")

@router.delete("/{connection_id}/hard", status_code=204)
async def hard_delete_connection(
    connection_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Hard-delete a connection.
    Removes the row from the database completely.
    """
    user_id = request.state.user_id

    async with PrimarySession() as session:
        conn = await _get_own_connection(session, connection_id, str(user_id))
        await session.delete(conn)
        await session.commit()
        logger.info(f"Connection {connection_id} hard-deleted by user {user_id}")

    # Purge connection-scoped cache entries
    try:
        from utils.connection_manager import invalidate_connection_cache
        await invalidate_connection_cache(request.app.state.redis, connection_id)
        await request.app.state.redis.delete(f"schema:{connection_id}")
    except Exception as cache_err:
        logger.warning(f"Cache purge failed for deleted connection {connection_id}: {cache_err}")


# ── Sensitivity Scan ──────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    """Options for the sensitivity scan."""
    auto_apply: bool = False   # If True, persist detected columns as ColumnSecurity rows
    run_ai: bool = False       # If True, run AI tier (Tier 3) in addition to regex/dict


class ScanColumnResult(BaseModel):
    schema_name: str
    table_name: str
    column_name: str
    classification_method: int
    label: str
    confidence: float


class ScanResponse(BaseModel):
    connection_id: str
    scanned_columns: int
    candidates: List[ScanColumnResult]
    auto_applied: bool
    applied_count: int


@router.post("/{connection_id}/scan", response_model=ScanResponse)
async def scan_connection_for_pii(
    connection_id: str,
    payload: ScanRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Scan an external database's schema for PII / sensitive columns.

    Runs a three-tier detector:
      Tier 1 — Column name regex patterns  (e.g. ssn, email, credit_card)
      Tier 2 — Dictionary keyword match    (e.g. token, api_key, salary)
      Tier 3 — AI heuristics               (optional, requires run_ai=True)

    If auto_apply=True, detected columns are persisted as ColumnSecurity rows
    with is_encrypted=False (user must explicitly enable encryption per column).
    """
    import json
    import asyncio
    import asyncpg as _asyncpg

    from middleware.security.sensitivity_scanner import scan_columns
    from models.column_security import ColumnSecurity

    user_id = request.state.user_id
    redis_client = request.app.state.redis

    # ── Load and verify connection ownership ──────────────────────────────────
    async with PrimarySession() as session:
        conn = await _get_own_connection(session, connection_id, str(user_id))
        if not conn.is_active:
            raise HTTPException(status_code=400, detail="Connection is inactive")

        try:
            from middleware.security.key_manager import key_manager
            if getattr(conn, "encrypted_dek", None):
                dek = await key_manager.get_dek(str(conn.id), conn.key_version, conn.encrypted_dek)
                plain_conn_str = decrypt_value(conn.conn_str_enc, dek)
            else:
                plain_conn_str = decrypt_value(conn.conn_str_enc)
        except Exception as dec_err:
            logger.error(f"Scan: decryption failed for {connection_id}: {dec_err}")
            raise HTTPException(status_code=500, detail="Failed to decrypt connection credentials")

    # ── Fetch schema from target database ─────────────────────────────────────
    try:
        schema_cache_key = f"schema:{connection_id}"
        cached = await redis_client.get(schema_cache_key)
        if cached:
            cached_schemas = json.loads(cached)
            schema_rows = []
            for sch in cached_schemas:
                sch_name = sch.get("database_schema") or "public"
                for tbl in sch.get("tables", []):
                    tbl_name = tbl.get("name")
                    for col in tbl.get("columns", []):
                        schema_rows.append({
                            "schema_name": sch_name,
                            "table_name": tbl_name,
                            "column_name": col.get("name"),
                            "data_type": col.get("type")
                        })
        else:
            asyncpg_conn = await asyncio.wait_for(_asyncpg.connect(plain_conn_str), timeout=10.0)
            try:
                raw = await asyncpg_conn.fetch("""
                    SELECT
                        table_schema  AS schema_name,
                        table_name,
                        column_name,
                        data_type
                    FROM information_schema.columns
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY table_schema, table_name, ordinal_position
                """)
                schema_rows = [dict(r) for r in raw]
            finally:
                await asyncpg_conn.close()
    except Exception as fetch_err:
        logger.error(f"Scan: schema fetch failed for {connection_id}: {_sanitize_db_error(str(fetch_err))}")
        raise HTTPException(status_code=400, detail="Could not connect to database for scan")

    # ── Run sensitivity scanner ───────────────────────────────────────────────
    results = await scan_columns(schema_rows, run_ai=payload.run_ai)

    # ── Optionally persist as ColumnSecurity rows ─────────────────────────────
    applied_count = 0
    if payload.auto_apply and results:
        import uuid as _uuid
        conn_uuid = _uuid.UUID(connection_id)
        local_seen = set()
        
        async with PrimarySession() as session:
            for r in results:
                col_key = (r.schema_name, r.table_name, r.column_name)
                if col_key in local_seen:
                    continue
                local_seen.add(col_key)
                
                # Upsert: insert if not exists using ON CONFLICT DO NOTHING
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                stmt = pg_insert(ColumnSecurity).values(
                    connection_id=conn_uuid,
                    schema_name=r.schema_name,
                    table_name=r.table_name,
                    column_name=r.column_name,
                    classification_method=int(r.classification_method),
                    is_encrypted=False,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None)
                ).on_conflict_do_nothing(
                    index_elements=['connection_id', 'schema_name', 'table_name', 'column_name']
                )
                res = await session.execute(stmt)
                if res.rowcount > 0:
                    applied_count += 1
            
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to commit scan results: {e}")
            
        await request.app.state.redis.delete(f"schema:{connection_id}")

    logger.info(
        f"Scan complete: connection={connection_id} "
        f"scanned={len(schema_rows)} candidates={len(results)} applied={applied_count}"
    )

    return ScanResponse(
        connection_id=connection_id,
        scanned_columns=len(schema_rows),
        candidates=[ScanColumnResult(**r.to_dict()) for r in results],
        auto_applied=payload.auto_apply,
        applied_count=applied_count,
    )


class RotateKeyResponse(BaseModel):
    connection_id: str
    old_version: int
    new_version: int
    message: str


@router.post("/{connection_id}/rotate-key", response_model=RotateKeyResponse)
async def rotate_key(
    connection_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Rotate the Data Encryption Key (DEK) for a connection.
    This generates a new DEK, stores the old one in dek_history, and triggers a background migration.
    """
    user_uuid = _safe_user_uuid(current_user["sub"])
    conn_uuid = _safe_user_uuid(connection_id)

    async with PrimarySession() as session:
        stmt = select(UserDatabase).where(UserDatabase.id == conn_uuid)
        result = await session.execute(stmt)
        conn = result.scalars().first()

        if not conn:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Basic ownership check
        if conn.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Not authorized to rotate this connection's key")

        old_version = conn.key_version
        old_encrypted_dek = conn.encrypted_dek

        # 1. Store old DEK in history
        from models.dek_history import DEKHistory
        history_entry = DEKHistory(
            database_id=str(conn.id),
            key_version=old_version,
            encrypted_dek=old_encrypted_dek,
        )
        session.add(history_entry)

        # 2. Rotate DEK in KeyManager
        from middleware.security.key_manager import key_manager
        old_dek = await key_manager.get_dek(str(conn.id), old_version, old_encrypted_dek)
        new_version, new_encrypted_dek = await key_manager.rotate_dek(str(conn.id), old_version)
        new_dek = await key_manager.get_dek(str(conn.id), new_version, new_encrypted_dek)

        # 3. Update UserDatabase
        from middleware.security.encryption import decrypt_value, encrypt_value
        plain_conn_str = decrypt_value(conn.conn_str_enc, old_dek)
        conn.conn_str_enc = encrypt_value(plain_conn_str, new_dek)
        
        conn.key_version = new_version
        conn.encrypted_dek = new_encrypted_dek

        # 4. Log the rotation event
        from models.encryption_audit import EncryptionAuditLog
        audit_log = EncryptionAuditLog(
            database_id=str(conn.id),
            user_id=str(user_uuid),
            event_type="key_rotation",
            details={
                "old_version": old_version,
                "new_version": new_version,
            }
        )
        session.add(audit_log)

        await session.commit()

        logger.info(f"Key rotated for connection {connection_id}. Version {old_version} -> {new_version}")

        # Trigger background re-encryption job if migration_worker is available.
        # The key rotation DB record is already committed above, so failure here
        # does not roll back the rotation — existing encrypted data stays accessible
        # at the old key version until the migration job runs.
        try:
            from workers.migration_worker import trigger_reencryption_job
            await trigger_reencryption_job(str(conn.id), old_version, new_version)
            migration_msg = "Background re-encryption migration scheduled."
        except ImportError:
            logger.warning(
                f"[rotate-key] workers.migration_worker not available — "
                f"re-encryption migration NOT scheduled for connection {connection_id}. "
                f"Existing data encrypted under key v{old_version} will remain until "
                f"migration is implemented."
            )
            migration_msg = "Key rotated. Re-encryption migration worker not yet available — data at old key version remains readable."
        except Exception as mig_err:
            logger.error(f"[rotate-key] Migration scheduling failed: {mig_err}")
            migration_msg = "Key rotated. Migration scheduling failed — check server logs."
        
        return RotateKeyResponse(
            connection_id=connection_id,
            old_version=old_version,
            new_version=new_version,
            message=migration_msg,
        )


class EncryptionAuditLogResponse(BaseModel):
    id: str
    database_id: str
    user_id: str
    event_type: str
    details: dict | None
    created_at: datetime


@router.get("/{connection_id}/encryption-audit", response_model=list[EncryptionAuditLogResponse])
async def get_encryption_audit_logs(
    connection_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
):
    """
    Fetch encryption audit logs for a connection.
    """
    user_uuid = _safe_user_uuid(current_user["sub"])
    conn_uuid = _safe_user_uuid(connection_id)

    async with PrimarySession() as session:
        # Check ownership
        stmt = select(UserDatabase).where(UserDatabase.id == conn_uuid)
        result = await session.execute(stmt)
        conn = result.scalars().first()

        if not conn or conn.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Not authorized to access this connection's logs")

        from models.encryption_audit import EncryptionAuditLog
        log_stmt = (
            select(EncryptionAuditLog)
            .where(EncryptionAuditLog.database_id == str(conn.id))
            .order_by(EncryptionAuditLog.created_at.desc())
            .limit(limit)
        )
        logs = await session.execute(log_stmt)
        
        return [
            EncryptionAuditLogResponse(
                id=log.id,
                database_id=log.database_id,
                user_id=log.user_id,
                event_type=log.event_type,
                details=log.details,
                created_at=log.created_at,
            )
            for log in logs.scalars().all()
        ]

@router.get("/{connection_id}/migration-status")
async def get_migration_status(
    connection_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Get the latest key rotation migration status for this connection.
    """
    user_uuid = _safe_user_uuid(current_user["sub"])
    conn_uuid = _safe_user_uuid(connection_id)

    async with PrimarySession() as session:
        # Check ownership
        stmt = select(UserDatabase).where(UserDatabase.id == conn_uuid)
        result = await session.execute(stmt)
        conn = result.scalars().first()

        if not conn or conn.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Not authorized to access this connection")

        from models.migration_job import MigrationJob
        job_stmt = (
            select(MigrationJob)
            .where(MigrationJob.database_id == str(conn.id))
            .order_by(MigrationJob.created_at.desc())
            .limit(1)
        )
        job_res = await session.execute(job_stmt)
        latest_job = job_res.scalars().first()

        if not latest_job:
            return {"status": "none", "message": "No migrations found for this connection."}

        return {
            "job_id": latest_job.id,
            "status": latest_job.status,
            "old_key_version": latest_job.old_key_version,
            "new_key_version": latest_job.new_key_version,
            "processed_records": latest_job.processed_records,
            "error_message": latest_job.error_message,
            "created_at": latest_job.created_at.isoformat(),
            "updated_at": latest_job.updated_at.isoformat() if latest_job.updated_at else None,
        }

