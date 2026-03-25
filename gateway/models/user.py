"""User and authentication models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
import enum
from utils.db import Base


class Role(str, enum.Enum):
    """User roles."""
    admin = "admin"
    readonly = "readonly"
    guest = "guest"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(Role), default=Role.readonly, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


class APIKey(Base):
    """API Key for programmatic access."""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    label = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    grace_until = Column(DateTime, nullable=True)  # for rotation grace period
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<APIKey {self.label or self.id}>"


class IPRule(Base):
    """IP whitelist/blacklist rules."""
    __tablename__ = "ip_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 max length
    rule_type = Column(String(10), nullable=False)  # "allow" or "block"
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    description = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<IPRule {self.ip_address} {self.rule_type}>"
