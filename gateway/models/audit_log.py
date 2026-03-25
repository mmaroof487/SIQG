"""Audit log models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from utils.db import Base


class AuditLog(Base):
    """Immutable audit log for all queries."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    role = Column(String(20), nullable=True)
    query_type = Column(String(20), nullable=True, index=True)  # SELECT, INSERT, etc.
    query_fingerprint = Column(String(64), nullable=True, index=True)  # SHA-256 hash
    latency_ms = Column(Float, nullable=True)
    status = Column(String(20), nullable=True, index=True)  # success, error, blocked, cached
    cached = Column(Boolean, default=False, nullable=False)
    slow = Column(Boolean, default=False, nullable=False, index=True)
    anomaly_flag = Column(Boolean, default=False, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    execution_plan = Column(JSON, nullable=True)  # EXPLAIN ANALYZE output
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog {self.trace_id} {self.status}>"


class SlowQuery(Base):
    """Slow query log (>threshold_ms)."""
    __tablename__ = "slow_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(36), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    query_fingerprint = Column(String(64), nullable=True, index=True)
    latency_ms = Column(Float, nullable=False)
    scan_type = Column(String(50), nullable=True)  # Seq Scan, Index Scan, etc.
    rows_scanned = Column(Integer, nullable=True)
    rows_returned = Column(Integer, nullable=True)
    recommended_index = Column(Text, nullable=True)  # CREATE INDEX DDL
    execution_plan = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<SlowQuery {self.trace_id} {self.latency_ms}ms>"


class SLASnapshot(Base):
    """Hourly SLA metrics snapshot."""
    __tablename__ = "sla_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hour = Column(DateTime, nullable=False, index=True)
    uptime_percent = Column(Float, nullable=False)  # 0-100
    p50_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    p99_latency_ms = Column(Float, nullable=False)
    total_requests = Column(Integer, nullable=False)
    failed_requests = Column(Integer, nullable=False)
    cache_hit_ratio = Column(Float, nullable=False)  # 0-1
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SLASnapshot {self.hour} {self.uptime_percent}%>"
