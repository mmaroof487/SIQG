"""SQLAlchemy models for the Multi-Database Workbench (Phase B)."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    Text, Integer, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from utils.db import Base


class DatabaseType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class UserDatabase(Base):
    """
    Represents an external database connection registered by a user.

    The connection string is stored AES-256-GCM encrypted at rest using
    encrypt_value() / decrypt_value() from middleware.security.encryption.

    Columns:
        id              - UUID primary key
        user_id         - FK to users.id (owner)
        display_name    - Human-readable label (e.g. "Production Analytics")
        db_type         - Enum: postgres | mysql | sqlite
        conn_str_enc    - AES-256-GCM ciphertext of the raw connection string
        is_active       - Soft delete / disable flag
        created_at      - Creation timestamp (UTC)
        updated_at      - Last update timestamp (UTC)
    """
    __tablename__ = "user_databases"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(255), nullable=False)
    db_type = Column(String(32), nullable=False, default=DatabaseType.POSTGRES)
    conn_str_enc = Column(Text, nullable=False)  # AES-256-GCM ciphertext
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    column_encryption_configs = relationship(
        "ColumnEncryptionConfig",
        back_populates="user_database",
        cascade="all, delete-orphan",
    )
    connection_permissions = relationship(
        "ConnectionPermissions",
        back_populates="user_database",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<UserDatabase id={self.id} name={self.display_name} type={self.db_type}>"


class ColumnEncryptionConfig(Base):
    """
    Defines which columns on a specific table within a user's external
    database connection should be AES-256-GCM encrypted at rest via Argus.

    One row per (connection_id, table_name, column_name) triple.
    """
    __tablename__ = "column_encryption_configs"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "table_name", "column_name",
            name="uq_col_enc_conn_table_col",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user_databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_name = Column(String(255), nullable=False)
    column_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user_database = relationship(
        "UserDatabase",
        back_populates="column_encryption_configs",
    )

    def __repr__(self):
        return (
            f"<ColumnEncryptionConfig conn={self.connection_id} "
            f"table={self.table_name} col={self.column_name}>"
        )


class ConnectionPermissions(Base):
    """
    Per-user permission overrides for an external database connection.

    Allows restricting which tables/query types a specific sub-user
    (identified by user_id) can access on a shared external connection.

    Columns:
        id                  - Auto-increment PK
        connection_id       - FK to user_databases.id
        user_id             - UUID of the user these perms apply to
        allowed_tables      - Whitelist of table names (NULL = all)
        allowed_query_types - Whitelist of query keywords (NULL = all)
    """
    __tablename__ = "connection_permissions"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "user_id",
            name="uq_conn_perm_conn_user",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user_databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    # Stored as JSON text '["table1", "table2"]' for SQLite/PostgreSQL compatibility.
    # Application code must json.loads/json.dumps when reading/writing.
    allowed_tables = Column(Text, nullable=True)       # JSON list of table names
    allowed_query_types = Column(Text, nullable=True)  # JSON list of query type keywords
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user_database = relationship(
        "UserDatabase",
        back_populates="connection_permissions",
    )

    def __repr__(self):
        return (
            f"<ConnectionPermissions conn={self.connection_id} "
            f"user={self.user_id}>"
        )
