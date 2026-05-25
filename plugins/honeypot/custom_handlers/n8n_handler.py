"""n8n Ni8mare (CVE-2026-21858) Handler.

This handler implements a honeypot for detection of CVE-2026-21858 (Ni8mare),
a CVSS 10.0 unauthenticated RCE vulnerability in n8n workflow automation platform.

The vulnerability exploits Content-Type confusion in Form Webhook handling:
1. Normal flow: POST with multipart/form-data uses Formidable (secure)
2. Vulnerable: POST with application/json populates req.body.files directly
3. Exploit: Attacker controls filepath to read arbitrary files

Attack Chain:
  Arbitrary File Read → Read database.sqlite (credentials) →
  Read config (JWT key) → Forge admin cookie → Create RCE workflow

References:
- https://beelzebub.ai/blog/catching-ni8mare-in-the-wild-cve-2026-21858/
- Cyera Research Labs disclosure (Jan 7, 2026)
"""

import asyncio
from core.observability.logging import get_logger
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from aiohttp import web

from ..config import HoneypotConfig
from ..engine.base import BaseHandler
from ..models import AttackCategory, AttackEvent, AttackSeverity, HoneypotProtocol
from ..security import sanitize_for_llm

logger = get_logger(__name__)


# Ni8mare / CVE-2026-21858 specific exploit patterns
N8N_EXPLOIT_PATTERNS = {
    # Core exploit: filepath injection in files object
    "filepath_injection": r'"filepath"\s*:\s*"/(etc|home|var|tmp|root|proc)/',
    # Files object manipulation (the vulnerable structure)
    "files_manipulation": r'"files"\s*:\s*\{[^}]*"filepath"',
    # Specific sensitive file targets
    "database_read": r'"filepath"\s*:\s*".*\.(sqlite|db|sqlite3)"',
    "config_read": r'"filepath"\s*:\s*".*/\.n8n/(config|database)"',
    "passwd_read": r'"filepath"\s*:\s*"/etc/passwd"',
    "shadow_read": r'"filepath"\s*:\s*"/etc/shadow"',
    # Secondary indicators
    "json_to_form_endpoint": r"^/(form|webhook|webhook-test)/",
}

# User-Agent patterns commonly seen in exploit scanners
SCANNER_USER_AGENTS = [
    r"python-requests/",
    r"python-urllib/",
    r"curl/",
    r"Go-http-client/",
]


class N8nHandler(BaseHandler):
    """Custom handler for n8n emulation and CVE-2026-21858 detection."""

    def __init__(self, config: HoneypotConfig, definition=None):
        """Initialize handler."""
        super().__init__(config, definition)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._sessions: Dict[str, dict] = {}
        # Default n8n port
        self._default_port = 5678

    async def start(self, port: Optional[int] = None) -> None:
        """Start the n8n honeypot server."""
        if self._running:
            return

        listen_port = (
            port
            or (self.definition.port if self.definition else None)
            or self._default_port
        )

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
            logger.info(f"n8n Ni8mare honeypot started on port {listen_port}")
        except OSError as e:
            logger.error(f"Failed to start n8n honeypot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the honeypot server."""
        if not self._running:
            return

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        self._running = False
        logger.info("n8n Ni8mare honeypot stopped")

    def _setup_routes(self) -> None:
        """Setup routes to emulate n8n endpoints."""
        # Version fingerprinting endpoint
        self._app.router.add_get("/rest/settings", self._handle_settings)
        self._app.router.add_get("/rest/login", self._handle_login)

        # Workflow API
        self._app.router.add_get("/api/v1/workflows", self._handle_workflows)

        # Vulnerable endpoints
        self._app.router.add_route("*", "/form/{path:.*}", self._handle_form)
        self._app.router.add_route("*", "/webhook/{path:.*}", self._handle_webhook)
        self._app.router.add_route(
            "*", "/webhook-test/{path:.*}", self._handle_webhook_test
        )

        # Catch-all for other paths
        self._app.router.add_route("*", "/{path:.*}", self._handle_generic)

    async def _handle_settings(self, request: web.Request) -> web.Response:
        """Handle /rest/settings - returns vulnerable version."""
        await self._log_reconnaissance(request)

        # Return n8n 1.120.0 (vulnerable version)
        settings_response = {
            "data": {
                "currentUser": None,
                "settings": {
                    "releaseChannel": "stable",
                    "allowCustomNodesPreview": False,
                    "isPreviewMode": False,
                },
                "version": "1.120.0",  # Vulnerable version
                "versionCli": "1.120.0",
                "instanceId": "a1b2c3d4e5f6g7h8i9j0",
                "pushConfig": {"backend": "websocket"},
                "n8nMetadata": {
                    "n8nCloud": False,
                    "instanceId": "a1b2c3d4e5f6g7h8i9j0",
                },
            }
        }

        return web.json_response(
            settings_response, headers=self._get_n8n_response_headers()
        )

    async def _handle_login(self, request: web.Request) -> web.Response:
        """Handle /rest/login - returns login page info."""
        await self._log_reconnaissance(request)

        return web.json_response(
            {"data": {"loginEnabled": True, "authenticationMethod": "email"}},
            headers=self._get_n8n_response_headers(),
        )

    async def _handle_workflows(self, request: web.Request) -> web.Response:
        """Handle /api/v1/workflows - returns empty workflow list."""
        await self._log_reconnaissance(request)

        return web.json_response(
            {"data": [], "nextCursor": None}, headers=self._get_n8n_response_headers()
        )

    async def _handle_form(self, request: web.Request) -> web.Response:
        """Handle /form/* - primary vulnerable endpoint."""
        return await self._process_exploit_attempt(request, endpoint_type="form")

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Handle /webhook/* - vulnerable webhook endpoint."""
        return await self._process_exploit_attempt(request, endpoint_type="webhook")

    async def _handle_webhook_test(self, request: web.Request) -> web.Response:
        """Handle /webhook-test/* - test webhook endpoint."""
        return await self._process_exploit_attempt(
            request, endpoint_type="webhook-test"
        )

    async def _handle_generic(self, request: web.Request) -> web.Response:
        """Handle generic requests."""
        source_ip = request.remote or "unknown"
        session_id = self._get_or_create_session(source_ip)

        # Check flow control
        if not self.check_flow_allowed(source_ip, session_id):
            return web.Response(status=403)

        # Apply stealth delay
        await self.apply_stealth_delay()

        # Return generic n8n-style 404
        return web.json_response(
            {"code": 404, "message": "Not Found"},
            status=404,
            headers=self._get_n8n_response_headers(),
        )

    async def _process_exploit_attempt(
        self, request: web.Request, endpoint_type: str
    ) -> web.Response:
        """Process potential CVE-2026-21858 exploit attempts."""
        path = request.path
        method = request.method
        source_ip = request.remote or "unknown"
        source_port = 0

        # Get or create session
        session_id = self._get_or_create_session(source_ip)

        # HoneyDOC flow check
        if not self.check_flow_allowed(source_ip, session_id):
            return web.Response(status=403)

        # Apply stealth delay
        await self.apply_stealth_delay()

        # Capture request data
        headers = dict(request.headers)
        content_type = headers.get("Content-Type", "").lower()
        user_agent = headers.get("User-Agent", "")
        body = ""

        try:
            body = await request.text()
        except Exception:
            pass  # nosec B110

        # Build full payload for analysis
        full_payload = f"{method} {path}\nHeaders: {headers}\nBody: {body}"

        # Detect CVE-2026-21858 patterns
        detected_patterns, is_ni8mare_attempt = self._analyze_n8n_payload(
            body, path, content_type, method
        )

        # Check for scanner user-agents
        is_scanner = any(
            re.search(pattern, user_agent, re.IGNORECASE)
            for pattern in SCANNER_USER_AGENTS
        )
        if is_scanner:
            detected_patterns.append("known_scanner")

        # Determine severity and category
        if is_ni8mare_attempt:
            category = AttackCategory.EXPLOIT_ATTEMPT
            severity = AttackSeverity.CRITICAL
        elif detected_patterns:
            category = AttackCategory.RECONNAISSANCE
            severity = AttackSeverity.HIGH
        else:
            # Still log POST requests to vulnerable endpoints
            base_detected, category = self.detect_patterns(full_payload)
            detected_patterns = base_detected
            severity = self.calculate_severity(category, detected_patterns)

        # Create event if patterns detected or suspicious activity
        if detected_patterns or (
            method == "POST" and content_type == "application/json"
        ):
            # Sanitize payload for LLM safety
            sanitized_body = sanitize_for_llm(body, max_length=2000)

            event = AttackEvent(
                event_id=self._generate_event_id(),
                session_id=session_id,
                protocol=HoneypotProtocol.HTTP,
                timestamp=datetime.now(timezone.utc),
                source_ip=source_ip,
                source_port=source_port,
                event_type="ni8mare_exploit" if is_ni8mare_attempt else "n8n_probe",
                raw_data=full_payload[: self.config.max_payload_size_kb * 1024],
                http_method=method,
                http_path=path,
                http_headers=headers,
                http_body=sanitized_body,
                detected_patterns=detected_patterns,
                category=category,
                severity=severity,
                matched_cves=["CVE-2026-21858"] if is_ni8mare_attempt else [],
            )

            asyncio.create_task(self.emit_event(event))
            logger.info(
                f"n8n exploit attempt from {source_ip}: "
                f"patterns={detected_patterns}, ni8mare={is_ni8mare_attempt}"
            )

        # Generate realistic response
        return self._generate_exploit_response(endpoint_type, is_ni8mare_attempt)

    def _analyze_n8n_payload(
        self, body: str, path: str, content_type: str, method: str
    ) -> Tuple[List[str], bool]:
        """Analyze if the payload matches CVE-2026-21858 exploit patterns.

        Returns:
            Tuple of (detected_pattern_names, is_ni8mare_attempt)
        """
        detected = []
        is_ni8mare = False

        # Check for the key Content-Type confusion
        # The exploit uses application/json on form/webhook endpoints
        is_content_type_confusion = (
            method == "POST"
            and content_type == "application/json"
            and re.search(N8N_EXPLOIT_PATTERNS["json_to_form_endpoint"], path)
        )

        if is_content_type_confusion:
            detected.append("content_type_confusion")

        # Check body for exploit patterns
        for name, pattern in N8N_EXPLOIT_PATTERNS.items():
            if name == "json_to_form_endpoint":
                continue  # Already handled above

            if re.search(pattern, body, re.IGNORECASE):
                detected.append(name)

        # Ni8mare signature: Content-Type confusion + filepath manipulation
        if "content_type_confusion" in detected and (
            "filepath_injection" in detected
            or "files_manipulation" in detected
            or "passwd_read" in detected
            or "database_read" in detected
        ):
            is_ni8mare = True

        return detected, is_ni8mare

    def _generate_exploit_response(
        self, endpoint_type: str, is_exploit: bool
    ) -> web.Response:
        """Generate realistic n8n response to keep attacker engaged."""
        # Get headers without Content-Type (json_response sets it automatically)
        headers = self._get_n8n_response_headers()
        headers = self.mask_response_headers(headers)

        if is_exploit:
            # Simulate file read failure (doesn't expose real content)
            # This keeps attacker engaged thinking it almost worked
            response = {
                "code": 500,
                "message": "An error occurred during execution",
                "hint": "There was an issue processing the uploaded file",
            }
            return web.json_response(response, status=500, headers=headers)

        # Normal form/webhook response
        if endpoint_type == "form":
            response = {
                "success": True,
                "executionId": "exec_" + self._generate_event_id()[:8],
            }
        else:
            response = {"message": "Workflow executed successfully"}

        return web.json_response(response, headers=headers)

    def _get_n8n_headers(self) -> Dict[str, str]:
        """Get realistic n8n response headers (includes Content-Type)."""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "X-n8n-Version": "1.120.0",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

    def _get_n8n_response_headers(self) -> Dict[str, str]:
        """Get response headers without Content-Type (for use with json_response)."""
        return {
            "X-n8n-Version": "1.120.0",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

    async def _log_reconnaissance(self, request: web.Request) -> None:
        """Log reconnaissance requests (settings/login probes)."""
        source_ip = request.remote or "unknown"
        session_id = self._get_or_create_session(source_ip)

        if not self.check_flow_allowed(source_ip, session_id):
            return

        headers = dict(request.headers)

        event = AttackEvent(
            event_id=self._generate_event_id(),
            session_id=session_id,
            protocol=HoneypotProtocol.HTTP,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=0,
            event_type="n8n_reconnaissance",
            raw_data=f"GET {request.path}",
            http_method="GET",
            http_path=request.path,
            http_headers=headers,
            detected_patterns=["version_fingerprint"],
            category=AttackCategory.RECONNAISSANCE,
            severity=AttackSeverity.MEDIUM,
            matched_cves=[],
        )

        asyncio.create_task(self.emit_event(event))

    def _get_or_create_session(self, source_ip: str) -> str:
        """Get or create session for IP."""
        if source_ip not in self._sessions:
            session_id = self._generate_session_id()
            self._sessions[source_ip] = {
                "session_id": session_id,
                "started_at": datetime.now(timezone.utc),
            }
        return self._sessions[source_ip]["session_id"]
