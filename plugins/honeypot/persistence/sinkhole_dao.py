"""Sinkhole DAO - Data Access Object for sinkholed domains.

Handles database operations for sinkhole management.
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_honeypot_config
from ..models.sinkhole import Base, SinkholedDomain, SinkholeActivityLog, SinkholeStatus

logger = get_logger(__name__)


class SinkholeDAO:
    """Data Access Object for sinkhole operations."""

    def __init__(self):
        """Initialize DAO with database connection."""
        config = get_honeypot_config()
        self.engine = create_engine(config.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        logger.info("SinkholeDAO initialized with database")

    def _get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    # ========================================================================
    # SINKHOLED DOMAIN CRUD
    # ========================================================================

    def create_sinkholed_domain(
        self,
        domain: str,
        anomaly_id: Optional[str] = None,
        detection_method: str = "dga",
        entropy: Optional[float] = None,
        confidence: float = 0.0,
        status: SinkholeStatus = SinkholeStatus.PAUSED,
        redirect_target: Optional[str] = None,
        associated_cluster_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> SinkholedDomain:
        """Create a new sinkholed domain entry.

        Args:
            domain: The domain name to sinkhole
            anomaly_id: ID of the NetworkAnomaly that detected this
            detection_method: How it was detected (dga, manual, etc.)
            entropy: Shannon entropy score (0-5 range)
            confidence: Detection confidence (0-1 range)
            status: Initial status
            redirect_target: Honeypot IP/domain to redirect to
            associated_cluster_id: Botnet cluster ID if known
            tags: Detection tags
            notes: Admin notes

        Returns:
            Created SinkholedDomain instance
        """
        with self._get_session() as session:
            # Check if domain already exists
            existing = session.query(SinkholedDomain).filter_by(domain=domain).first()
            if existing:
                logger.warning(f"Domain {domain} already sinkholed (ID: {existing.id})")
                return existing

            # Create new entry
            sinkholed = SinkholedDomain(
                domain=domain,
                anomaly_id=anomaly_id,
                detection_method=detection_method,
                entropy=int(entropy * 100) if entropy else None,
                confidence=int(confidence * 100),
                status=status,
                redirect_target=redirect_target,
                associated_cluster_id=associated_cluster_id,
                tags=tags or [],
                notes=notes,
            )

            session.add(sinkholed)
            session.commit()
            session.refresh(sinkholed)

            logger.info(f"Created sinkholed domain: {domain} (ID: {sinkholed.id})")
            return sinkholed

    def get_sinkholed_domain(self, domain_id: int) -> Optional[SinkholedDomain]:
        """Get sinkholed domain by ID."""
        with self._get_session() as session:
            return session.query(SinkholedDomain).filter_by(id=domain_id).first()

    def get_sinkholed_domain_by_name(self, domain: str) -> Optional[SinkholedDomain]:
        """Get sinkholed domain by domain name."""
        with self._get_session() as session:
            return session.query(SinkholedDomain).filter_by(domain=domain).first()

    def list_sinkholed_domains(
        self,
        status: Optional[SinkholeStatus] = None,
        cluster_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SinkholedDomain]:
        """List sinkholed domains with optional filters.

        Args:
            status: Filter by status
            cluster_id: Filter by cluster
            limit: Max results
            offset: Pagination offset

        Returns:
            List of SinkholedDomain instances
        """
        with self._get_session() as session:
            query = session.query(SinkholedDomain)

            if status:
                query = query.filter_by(status=status)
            if cluster_id:
                query = query.filter_by(associated_cluster_id=cluster_id)

            query = query.order_by(desc(SinkholedDomain.updated_at))
            query = query.limit(limit).offset(offset)

            return query.all()

    def update_sinkhole_status(
        self, domain_id: int, status: SinkholeStatus
    ) -> Optional[SinkholedDomain]:
        """Update sinkhole status (activate/pause/terminate).

        Args:
            domain_id: Sinkholed domain ID
            status: New status

        Returns:
            Updated SinkholedDomain or None if not found
        """
        with self._get_session() as session:
            sinkholed = session.query(SinkholedDomain).filter_by(id=domain_id).first()
            if not sinkholed:
                logger.warning(f"Sinkholed domain ID {domain_id} not found")
                return None

            old_status = sinkholed.status
            sinkholed.status = status

            # Track activation time
            if status == SinkholeStatus.ACTIVE and old_status != SinkholeStatus.ACTIVE:
                sinkholed.activated_at = datetime.now(timezone.utc)
                logger.info(f"Activated sinkhole for domain: {sinkholed.domain}")

            session.commit()
            session.refresh(sinkholed)

            logger.info(
                f"Updated sinkhole status for {sinkholed.domain}: {old_status} -> {status}"
            )
            return sinkholed

    def increment_request_count(
        self, domain_id: int, source_ip: str
    ) -> Optional[SinkholedDomain]:
        """Increment request count and track unique IP.

        Args:
            domain_id: Sinkholed domain ID
            source_ip: Requesting IP address

        Returns:
            Updated SinkholedDomain or None
        """
        with self._get_session() as session:
            sinkholed = session.query(SinkholedDomain).filter_by(id=domain_id).first()
            if not sinkholed:
                return None

            # Increment count
            sinkholed.request_count += 1

            # Add unique IP if not already tracked
            unique_ips = sinkholed.unique_ips or []
            if source_ip not in unique_ips:
                unique_ips.append(source_ip)
                sinkholed.unique_ips = unique_ips

            # Update last activity
            sinkholed.last_activity = datetime.now(timezone.utc)

            session.commit()
            session.refresh(sinkholed)

            return sinkholed

    def delete_sinkholed_domain(self, domain_id: int) -> bool:
        """Delete a sinkholed domain entry.

        Args:
            domain_id: Sinkholed domain ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            sinkholed = session.query(SinkholedDomain).filter_by(id=domain_id).first()
            if not sinkholed:
                return False

            # Also delete activity logs
            session.query(SinkholeActivityLog).filter_by(
                sinkholed_domain_id=domain_id
            ).delete()

            session.delete(sinkholed)
            session.commit()

            logger.info(f"Deleted sinkholed domain: {sinkholed.domain}")
            return True

    # ========================================================================
    # ACTIVITY LOG CRUD
    # ========================================================================

    def log_sinkhole_activity(
        self,
        domain_id: int,
        source_ip: str,
        request_type: Optional[str] = None,
        payload: Optional[str] = None,
        user_agent: Optional[str] = None,
        honeypot_id: Optional[str] = None,
        response_type: Optional[str] = None,
    ) -> SinkholeActivityLog:
        """Log a request to a sinkholed domain.

        Args:
            domain_id: Sinkholed domain ID
            source_ip: Requesting IP
            request_type: Type of request (DNS, HTTP, etc.)
            payload: Request payload
            user_agent: User-Agent header
            honeypot_id: Honeypot that handled the request
            response_type: How we responded

        Returns:
            Created SinkholeActivityLog
        """
        with self._get_session() as session:
            activity = SinkholeActivityLog(
                sinkholed_domain_id=domain_id,
                source_ip=source_ip,
                request_type=request_type,
                payload=payload,
                user_agent=user_agent,
                honeypot_id=honeypot_id,
                response_type=response_type,
            )

            session.add(activity)
            session.commit()
            session.refresh(activity)

            # Also increment request count
            self.increment_request_count(domain_id, source_ip)

            return activity

    def get_activity_logs(
        self,
        domain_id: Optional[int] = None,
        source_ip: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SinkholeActivityLog]:
        """Get activity logs with optional filters.

        Args:
            domain_id: Filter by domain
            source_ip: Filter by source IP
            limit: Max results
            offset: Pagination offset

        Returns:
            List of SinkholeActivityLog instances
        """
        with self._get_session() as session:
            query = session.query(SinkholeActivityLog)

            if domain_id:
                query = query.filter_by(sinkholed_domain_id=domain_id)
            if source_ip:
                query = query.filter_by(source_ip=source_ip)

            query = query.order_by(desc(SinkholeActivityLog.timestamp))
            query = query.limit(limit).offset(offset)

            return query.all()

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_sinkhole_stats(self) -> dict:
        """Get overall sinkhole statistics.

        Returns:
            Dictionary with statistics
        """
        with self._get_session() as session:
            total = session.query(func.count(SinkholedDomain.id)).scalar() or 0
            active = (
                session.query(func.count(SinkholedDomain.id))
                .filter_by(status=SinkholeStatus.ACTIVE)
                .scalar()
                or 0
            )
            paused = (
                session.query(func.count(SinkholedDomain.id))
                .filter_by(status=SinkholeStatus.PAUSED)
                .scalar()
                or 0
            )
            terminated = (
                session.query(func.count(SinkholedDomain.id))
                .filter_by(status=SinkholeStatus.TERMINATED)
                .scalar()
                or 0
            )

            total_requests = (
                session.query(func.sum(SinkholedDomain.request_count)).scalar() or 0
            )

            return {
                "total_domains": total,
                "active": active,
                "paused": paused,
                "terminated": terminated,
                "total_requests": total_requests,
            }
