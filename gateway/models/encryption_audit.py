from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

from utils.db import Base

class EncryptionAuditLog(Base):
    __tablename__ = "encryption_audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    database_id = Column(PGUUID(as_uuid=True), ForeignKey("user_databases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    event_type = Column(String, nullable=False)  # "key_rotation", "encryption_enabled", "access_denied"
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), index=True)
