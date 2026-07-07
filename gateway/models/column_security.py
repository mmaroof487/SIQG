import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from utils.db import Base

class ColumnSecurity(Base):
    """
    Tracks column-level security policies and discovery metadata.
    Replaces the old ColumnEncryptionConfig.
    
    classification_method represents how the column was identified as sensitive:
    0 = Regex Pattern
    1 = Dictionary Match
    2 = AI Discovery
    3 = Manual (User specified)
    """
    __tablename__ = "column_security"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "schema_name", "table_name", "column_name",
            name="uq_col_sec_conn_sch_tab_col",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user_databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_name = Column(String(255), nullable=False, default="public")
    table_name = Column(String(255), nullable=False)
    column_name = Column(String(255), nullable=False)
    
    classification_method = Column(Integer, nullable=False, default=3)
    is_encrypted = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationship
    user_database = relationship(
        "UserDatabase",
        back_populates="column_security_configs",
    )

    def __repr__(self):
        return (
            f"<ColumnSecurity conn={self.connection_id} "
            f"table={self.table_name} col={self.column_name} "
            f"enc={self.is_encrypted}>"
        )
