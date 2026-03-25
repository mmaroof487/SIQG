"""SLA tracking model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class SLASnapshot(Base):
    """Hourly SLA metrics snapshot."""
    __tablename__ = "sla_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_hour = Column(DateTime, nullable=False, index=True)
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    p50_latency_ms = Column(Float, nullable=True)  # Median
    p95_latency_ms = Column(Float, nullable=True)
    p99_latency_ms = Column(Float, nullable=True)
    cache_hit_ratio = Column(Float, nullable=True)
    uptime_percentage = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SLASnapshot {self.snapshot_hour} p95={self.p95_latency_ms}ms>"
