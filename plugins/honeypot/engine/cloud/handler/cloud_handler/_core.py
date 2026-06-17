"""CloudManagementHandler core class."""

import asyncio
import hashlib
import uuid
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web
from core.observability.logging import get_logger

from .....config import HoneypotConfig
from .....events import HoneypotEvents, emit_honeypot_event
from ....base import BaseHandler
from ...heuristics import get_heuristic_engine
from ...models import (
    APICallSeverity,
    CloudAPICall,
    CloudSession,
    CloudProvider,
    SessionState,
)
from ...patterns import get_cloud_pattern_detector
from ...protocols import (
    CloudPatternDetectorProtocol,
    GeoIPServiceProtocol,
    HeuristicEngineProtocol,
    TLSFingerprintingServiceProtocol,
)
from ...responses import CloudResponseGenerator
from ...services import get_fingerprinting_service, get_geoip_service
from ..session_manager import CloudSessionManager
from ._request_handlers import RequestHandlersMixin

logger = get_logger(__name__)


class CloudManagementHandler(RequestHandlersMixin, BaseHandler):
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
        attack_event: Any,
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
