from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from utils.db import Base

class DEKHistory(Base):
    __tablename__ = "dek_history"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    database_id = Column(PGUUID(as_uuid=True), ForeignKey("user_databases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    key_version = Column(Integer, nullable=False)
    encrypted_dek = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=func.now())
    retired_at = Column(DateTime, nullable=True)
    
    database = relationship("UserDatabase", back_populates="dek_history")
