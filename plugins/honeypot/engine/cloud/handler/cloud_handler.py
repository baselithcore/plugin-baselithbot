"""Cloud Management Honeypot - Main Handler.

High-interaction honeypot simulating AWS-like cloud management APIs.
"""

import asyncio
import hashlib
from core.observability.logging import get_logger
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web

from ....config import HoneypotConfig
from ....events import HoneypotEvents, emit_honeypot_event
from ....models import AttackEvent, AttackSeverity, HoneypotProtocol
from ...base import BaseHandler
from ..heuristics import get_heuristic_engine
from ..models import (
    APICallSeverity,
    CloudAPICall,
    CloudAttackCategory,
    CloudProvider,
    CloudSession,
    SessionState,
    TLSFingerprint,
)
from ..patterns import get_cloud_pattern_detector
from ..protocols import (
    CloudPatternDetectorProtocol,
    GeoIPServiceProtocol,
    HeuristicEngineProtocol,
    TLSFingerprintingServiceProtocol,
)
from ..responses import CloudResponseGenerator
from ..services import get_fingerprinting_service, get_geoip_service
from .helpers import (
    calculate_timing,
    create_attack_event,
    determine_trigger,
    extract_credentials,
)
from .parsers import parse_aws_request
from .session_manager import CloudSessionManager

logger = get_logger(__name__)


class CloudManagementHandler(BaseHandler):
    """High-interaction cloud management API honeypot.

    Supports dependency injection for testability. Services can be injected
    via constructor or will use default singleton instances.
    """

    def __init__(
        self,
        config: HoneypotConfig,
        definition=None,
        provider: CloudProvider = CloudProvider.AWS,
        *,
        pattern_detector: Optional[CloudPatternDetectorProtocol] = None,
        heuristic_engine: Optional[HeuristicEngineProtocol] = None,
        geoip_service: Optional[GeoIPServiceProtocol] = None,
        fingerprinting_service: Optional[TLSFingerprintingServiceProtocol] = None,
        response_generator: Optional[CloudResponseGenerator] = None,
    ):
        """Initialize cloud management handler.

        Args:
            config: Honeypot configuration
            definition: Optional honeypot definition
            provider: Cloud provider type (default: AWS)
            pattern_detector: Optional injected pattern detector (for testing)
            heuristic_engine: Optional injected heuristic engine (for testing)
            geoip_service: Optional injected GeoIP service (for testing)
            fingerprinting_service: Optional injected TLS fingerprinting service (for testing)
            response_generator: Optional injected response generator (for testing)
        """
        super().__init__(config, definition)

        self.provider = provider
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

        # Dependency injection: use provided services or fall back to singletons
        self._pattern_detector = pattern_detector or get_cloud_pattern_detector()
        self._heuristic_engine = heuristic_engine or get_heuristic_engine()
        self._geoip_service = geoip_service or get_geoip_service()
        self._fingerprinting_service = (
            fingerprinting_service or get_fingerprinting_service()
        )
        self._response_generator = response_generator or CloudResponseGenerator(
            region=config.cluster.region if hasattr(config, "cluster") else "eu-south-1"
        )

        # Session management (delegated, with GeoIP injection)
        honeypot_id = (
            config.cluster.node_id if hasattr(config, "cluster") else "cloud-mgmt"
        )
        self._session_manager = CloudSessionManager(
            honeypot_id=honeypot_id,
            provider=provider,
            max_auth_attempts=config.ssh_max_auth_attempts,
            session_timeout_minutes=config.max_session_duration_seconds // 60,
            on_state_change=self._on_state_change,
            geoip_service=self._geoip_service,
        )

        # Request timing tracking
        self._request_counts: Dict[str, List[float]] = {}

        # Callbacks
        self._on_high_severity_event: Optional[Callable] = None
        self._on_session_end: Optional[Callable] = None

    async def start(self, port: Optional[int] = None) -> None:
        """Start the cloud management honeypot server."""
        if self._running:
            return

        listen_port = port or getattr(self.config, "cloud_api_port", 8443)

        self._app = web.Application()
        self._setup_routes()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(
            self._runner,
            "0.0.0.0",  # nosec B104
            listen_port,
        )

        try:
            await self._site.start()
            self._running = True
            logger.info(
                f"Cloud Management Honeypot started on port {listen_port} "
                f"(provider: {self.provider.value})"
            )
        except OSError as e:
            logger.error(f"Failed to start Cloud Management Honeypot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the honeypot server."""
        if not self._running:
            return

        # End all active sessions
        await self._session_manager.end_all_sessions(
            reason="server_shutdown",
            callback=self._on_session_end,
        )

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        self._running = False
        logger.info("Cloud Management Honeypot stopped")

    def _setup_routes(self) -> None:
        """Configure HTTP routes."""
        self._app.router.add_route("*", "/", self._handle_request)
        self._app.router.add_route("*", "/{service}/{path:.*}", self._handle_request)
        # IMDSv2 token endpoint (must be before metadata catch-all)
        self._app.router.add_route("PUT", "/latest/api/token", self._handle_imds_token)
        self._app.router.add_route(
            "GET", "/latest/{path:.*}", self._handle_metadata_request
        )
        self._app.router.add_route("GET", "/health", self._handle_health)

    async def _handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming API request."""
        source_ip = self._extract_source_ip(request)
        source_port = 0
        now = time.time()

        # Rate limiting
        if not self.check_rate_limit(source_ip):
            logger.warning(f"Rate limit exceeded for {source_ip}")
            return web.json_response(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
                status=429,
            )

        await self.apply_stealth_delay()

        # Flow control
        session = self._session_manager.get_session_by_ip(source_ip)
        session_id = session.session_id if session else ""
        if not self.check_flow_allowed(source_ip, session_id):
            return web.Response(status=403)

        # Parse request
        headers = dict(request.headers)
        body = ""
        try:
            body = await request.text()
        except Exception:
            pass

        service, action, parameters = parse_aws_request(request, headers, body)

        # Handle root requests (GET /) explicitly for console bait
        if request.path == "/" and request.method == "GET" and service == "unknown":
            html, status = self._response_generator.get_console_login_page()
            return web.Response(
                text=html,
                status=status,
                content_type="text/html",
                headers={
                    "Server": "Server",  # Mimic AWS CloudFront/ELB
                    "x-amz-request-id": uuid.uuid4().hex,
                },
            )

        # Get or create session
        session = self._session_manager.get_or_create_session(
            source_ip, source_port, request
        )
        state_machine = self._session_manager.get_state_machine(session.session_id)

        # TLS/JA4 Fingerprinting
        ja4_hash = self._fingerprinting_service.extract_ja4_from_headers(
            headers, source_ip
        )
        tls_fingerprint = None
        if ja4_hash:
            classification = self._fingerprinting_service.classify_client(ja4_hash)
            tls_fingerprint = TLSFingerprint(
                ja4=ja4_hash,
                client_guess=classification.get("client_type"),
                confidence=1.0 if classification.get("confidence") == "high" else 0.5,
            )

        # Timing and credential analysis
        timing = calculate_timing(source_ip, now, self._request_counts)
        credentials = extract_credentials(headers, body)
        if credentials:
            session.credentials_captured.append(credentials)

        # Pattern detection
        detections = self._pattern_detector.detect(
            payload=body, action=action, headers=headers
        )
        category, severity, pattern_names = self._pattern_detector.detect_api_action(
            service, action
        )

        # Create API call record
        call = CloudAPICall(
            call_id=f"call-{uuid.uuid4().hex[:12]}",
            session_id=session.session_id,
            timestamp=datetime.now(timezone.utc),
            service=service,
            action=action,
            parameters=parameters,
            headers=headers,
            body_hash=hashlib.sha256(body.encode()).hexdigest() if body else None,
            category=category or CloudAttackCategory.UNKNOWN,
            severity=severity,
            detected_patterns=pattern_names,
            request_timing=timing,
            tls_fingerprint=tls_fingerprint,
            source_ip=source_ip,
            source_port=source_port,
            user_agent=headers.get("User-Agent"),
        )

        # Heuristic analysis and state machine
        heuristic_alerts = self._heuristic_engine.evaluate_all(session, call)
        trigger = determine_trigger(action, credentials, detections)

        if state_machine:
            state_machine.process_trigger(
                trigger,
                context={
                    "service": service,
                    "action": action,
                    "detections": len(detections),
                },
            )

        # Update session
        session.api_call_count += 1
        session.services_accessed.add(service)
        session.actions_performed.add(action)
        session.api_calls.append(call.call_id)

        # Generate response
        response_body, http_status = self._generate_response(
            service, action, parameters, session, call
        )

        call.response_code = http_status
        if http_status >= 400:
            session.error_count += 1
            call.simulated_error = response_body.get("Error", {}).get("Code")
        else:
            session.success_count += 1

        # Emit events
        attack_event = create_attack_event(
            session=session,
            call=call,
            detections=detections,
            heuristic_alerts=heuristic_alerts,
            request=request,
            config=self.config,
            pattern_detector=self._pattern_detector,
        )

        asyncio.create_task(self.emit_event(attack_event))
        await self._emit_high_severity_event(session, call, attack_event, severity)

        return self._format_response(response_body, http_status, service)

    async def _handle_imds_token(self, request: web.Request) -> web.Response:
        """Handle IMDSv2 token request (PUT /latest/api/token)."""
        source_ip = self._extract_source_ip(request)

        logger.info(f"IMDSv2 token request from {source_ip}")
        await self.apply_stealth_delay()

        # Get TTL from header (default 21600 = 6 hours)
        try:
            ttl = int(
                request.headers.get("X-aws-ec2-metadata-token-ttl-seconds", 21600)
            )
        except ValueError:
            ttl = 21600

        token, http_status = self._response_generator.imds_put_token(ttl)

        return web.Response(
            text=token,
            status=http_status,
            headers={"X-aws-ec2-metadata-token-ttl-seconds": str(ttl)},
        )

    async def _handle_metadata_request(self, request: web.Request) -> web.Response:
        """Handle IMDS metadata service requests (SSRF detection)."""
        source_ip = self._extract_source_ip(request)
        subpath = request.match_info.get("path", "")
        full_path = f"/latest/{subpath}"

        logger.warning(f"IMDS access attempt from {source_ip}: {full_path}")
        await self.apply_stealth_delay()

        session = self._session_manager.get_or_create_session(source_ip, 0, request)

        # Extract IMDSv2 token if present
        imds_token = request.headers.get("X-aws-ec2-metadata-token")
        response_body, http_status = self._response_generator.imds_metadata(
            full_path, token=imds_token
        )

        # Create critical event for IMDS access
        event = AttackEvent(
            event_id=self._generate_event_id(),
            session_id=session.session_id,
            honeypot_id=self._session_manager.honeypot_id,
            protocol=HoneypotProtocol.HTTP,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=0,
            event_type="metadata_access",
            raw_data=full_path,
            http_method="GET",
            http_path=full_path,
            detected_patterns=["imds_access", "ssrf_aws_metadata"],
            severity=AttackSeverity.CRITICAL,
            metadata={
                "service": "imds",
                "imds_path": subpath,
                "is_credential_path": "security-credentials" in full_path,
            },
        )

        asyncio.create_task(self.emit_event(event))
        asyncio.create_task(
            emit_honeypot_event(
                HoneypotEvents.ATTACK_HIGH_SEVERITY,
                {
                    "event_id": event.event_id,
                    "session_id": session.session_id,
                    "attack_type": "imds_access",
                    "cloud_service": "imds",
                    "category": "metadata_service_abuse",
                    "severity": "critical",
                    "source_ip": source_ip,
                    "imds_path": subpath,
                    "is_credential_path": "security-credentials" in full_path,
                    "mitre_techniques": ["T1552.005"],
                    "related_cves": ["CVE-2019-5736", "CVE-2020-8555"],
                },
            )
        )

        if isinstance(response_body, dict):
            return web.json_response(response_body, status=http_status)
        return web.Response(text=str(response_body), status=http_status)

    async def _handle_health(self, _request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response(
            {
                "status": "healthy",
                "service": "cloud-management-api",
                "provider": self.provider.value,
            }
        )

    def _extract_source_ip(self, request: web.Request) -> str:
        """Extract real client IP from request headers."""
        return (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "")
            or request.headers.get("CF-Connecting-IP", "")
            or request.remote
            or "unknown"
        )

    def _generate_response(
        self,
        service: str,
        action: str,
        parameters: Dict[str, Any],
        session: CloudSession,
        _call: CloudAPICall,
    ) -> tuple:
        """Generate API response based on session state."""
        state = session.current_state

        if state in (SessionState.DISCOVERY, SessionState.PRE_AUTH):
            return self._response_generator.error_response("MissingAuthenticationToken")

        if state == SessionState.BLOCKED:
            return self._response_generator.access_denied(
                action=f"{service}:{action}", resource="*"
            )

        return self._response_generator.handle_action(
            service=service,
            action=action,
            parameters=parameters,
            authenticated=session.auth_success,
        )

    async def _emit_high_severity_event(
        self,
        session: CloudSession,
        call: CloudAPICall,
        attack_event: AttackEvent,
        severity: APICallSeverity,
    ) -> None:
        """Emit high severity event if applicable."""
        if severity not in (APICallSeverity.CRITICAL, APICallSeverity.HIGH):
            return

        await emit_honeypot_event(
            HoneypotEvents.ATTACK_HIGH_SEVERITY,
            {
                "event_id": attack_event.event_id,
                "session_id": session.session_id,
                "attack_type": "cloud_api_attack",
                "cloud_service": call.service,
                "cloud_action": call.action,
                "category": attack_event.category.value,
                "severity": attack_event.severity.value,
                "source_ip": call.source_ip,
                "threat_score": session.threat_score,
                "mitre_techniques": attack_event.metadata.get(
                    "mitre_technique_ids", []
                ),
                "zero_day_candidate": attack_event.metadata.get(
                    "zero_day_candidate", False
                ),
            },
        )

        if self._on_high_severity_event:
            asyncio.create_task(self._on_high_severity_event(attack_event, session))

    def _on_state_change(
        self,
        old_state: SessionState,
        new_state: SessionState,
        trigger: str,
    ) -> None:
        """Callback for state changes."""
        logger.info(f"State change: {old_state.value} -> {new_state.value} ({trigger})")

        if new_state in (
            SessionState.EXFILTRATING,
            SessionState.PRIVILEGE_ESCALATION,
            SessionState.LATERAL_MOVEMENT,
        ):
            logger.warning(
                f"High-risk state reached: {new_state.value} (trigger: {trigger})"
            )

    def _format_response(
        self,
        body: Dict,
        status: int,
        _service: str,
    ) -> web.Response:
        """Format response with AWS-like headers."""
        headers = {
            "x-amzn-RequestId": uuid.uuid4().hex,
            "x-amz-id-2": hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:56],
            "Server": "AmazonS3",  # Override aiohttp default
        }
        headers = self.mask_response_headers(headers)
        return web.json_response(body, status=status, headers=headers)

    # Public Interface
    def get_session(self, session_id: str) -> Optional[CloudSession]:
        """Get session by ID."""
        return self._session_manager.get_session(session_id)

    def get_active_sessions(self) -> List[CloudSession]:
        """Get all active sessions."""
        return self._session_manager.get_active_sessions()

    def get_heuristic_alerts(self) -> list:
        """Get all heuristic alerts."""
        alerts = []
        for session in self._session_manager.get_all_sessions():
            alerts.extend(self._heuristic_engine.get_session_alerts(session.session_id))
        return alerts

    def get_zero_day_candidates(self) -> list:
        """Get alerts flagged as potential zero-day indicators."""
        return self._heuristic_engine.get_zero_day_candidates()

    def set_high_severity_callback(self, callback: Callable) -> None:
        """Set callback for high severity events."""
        self._on_high_severity_event = callback

    def set_session_end_callback(self, callback: Callable) -> None:
        """Set callback for session end."""
        self._on_session_end = callback
