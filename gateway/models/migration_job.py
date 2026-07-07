from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from datetime import datetime

from utils.db import Base

class MigrationJob(Base):
    __tablename__ = "migration_jobs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    database_id = Column(PGUUID(as_uuid=True), ForeignKey("user_databases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(String(50), nullable=False, default="pending")  # pending, in_progress, completed, failed
    
    old_key_version = Column(Integer, nullable=True)
    new_key_version = Column(Integer, nullable=False)
    
    target_table = Column(String, nullable=True)
    target_column = Column(String, nullable=True)
    
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
