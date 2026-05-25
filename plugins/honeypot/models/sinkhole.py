"""Sinkhole Domain Models.

Database models for tracking sinkholed domains and their activity.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SinkholeStatus(str, Enum):
    """Status of a sinkholed domain."""

    ACTIVE = "active"  # Actively redirecting traffic
    PAUSED = "paused"  # Temporarily disabled
    TERMINATED = "terminated"  # Permanently disabled


class SinkholedDomain(Base):
    """Represents a domain that has been sinkholed to a honeypot."""

    __tablename__ = "sinkholed_domains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, unique=True, index=True)

    # Detection metadata
    anomaly_id = Column(
        String(100), nullable=True, index=True
    )  # Link to NetworkAnomaly
    detection_method = Column(
        String(50), nullable=False, default="dga"
    )  # dga, manual, etc.
    entropy = Column(Integer, nullable=True)  # Shannon entropy * 100 for storage
    confidence = Column(Integer, nullable=False)  # Confidence * 100

    # Sinkhole configuration
    status = Column(
        SQLEnum(SinkholeStatus), nullable=False, default=SinkholeStatus.PAUSED
    )
    redirect_target = Column(
        String(255), nullable=True
    )  # Honeypot IP/domain to redirect to

    # Activity tracking
    request_count = Column(Integer, nullable=False, default=0)
    unique_ips = Column(JSON, nullable=False, default=list)  # List of unique IPs
    first_seen = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_activity = Column(DateTime, nullable=True)

    # Association
    associated_cluster_id = Column(String(100), nullable=True, index=True)

    # Metadata
    tags = Column(
        JSON, nullable=False, default=list
    )  # ["dga_entropy", "fast_flux", etc.]
    notes = Column(Text, nullable=True)  # Admin notes

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    activated_at = Column(DateTime, nullable=True)  # When it was first activated
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SinkholedDomain(domain='{self.domain}', status='{self.status}', requests={self.request_count})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "domain": self.domain,
            "anomaly_id": self.anomaly_id,
            "detection_method": self.detection_method,
            "entropy": self.entropy / 100 if self.entropy else None,
            "confidence": self.confidence / 100,
            "status": self.status.value,
            "redirect_target": self.redirect_target,
            "request_count": self.request_count,
            "unique_ips_count": len(self.unique_ips) if self.unique_ips else 0,
            "unique_ips": self.unique_ips[:10]
            if self.unique_ips
            else [],  # Limit to 10 for API
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
            "associated_cluster_id": self.associated_cluster_id,
            "tags": self.tags or [],
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat()
            if self.activated_at
            else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SinkholeActivityLog(Base):
    """Log of individual requests to sinkholed domains."""

    __tablename__ = "sinkhole_activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sinkholed_domain_id = Column(Integer, nullable=False, index=True)

    # Request details
    source_ip = Column(String(45), nullable=False, index=True)  # Support IPv6
    timestamp = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Request metadata
    request_type = Column(String(50), nullable=True)  # DNS, HTTP, etc.
    payload = Column(Text, nullable=True)  # Request payload/query
    user_agent = Column(String(500), nullable=True)

    # Honeypot handling
    honeypot_id = Column(String(100), nullable=True)  # Which honeypot handled it
    response_type = Column(String(50), nullable=True)  # How we responded

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<SinkholeActivityLog(domain_id={self.sinkholed_domain_id}, ip='{self.source_ip}', timestamp='{self.timestamp}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "sinkholed_domain_id": self.sinkholed_domain_id,
            "source_ip": self.source_ip,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "request_type": self.request_type,
            "payload": self.payload[:200] if self.payload else None,  # Truncate for API
            "user_agent": self.user_agent,
            "honeypot_id": self.honeypot_id,
            "response_type": self.response_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
