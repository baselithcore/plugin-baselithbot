"""FortiGate SSL VPN (CVE-2024-21762) Handler.

This handler implements a honeypot for detection of CVE-2024-21762,
a CVSS 9.6 unauthenticated RCE vulnerability in FortiOS SSL VPN.

The vulnerability exploits improper bounds checking in HTTP chunked transfer
encoding parser:
1. Normal flow: HTTP chunked encoding safely parsed with bounds checks
2. Vulnerable: Chunk length field with 4000+ "0" characters causes overflow
3. Exploit: Out-of-bounds write corrupts stack pointer → structure hijack → RCE

Attack Chain:
  Heap Spray (/remote/hostcheck_validate) → Chunked encoding overflow →
  Stack corruption (r13 register) → Fake SSL_CTX structure → ROP chain → RCE

References:
- https://github.com/h4x0r-dz/CVE-2024-21762
- Fortinet PSIRT Advisory FG-IR-24-015
- Patched in FortiOS 7.4.3+ (build 2573+)
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


# CVE-2024-21762 specific exploit patterns
FORTIGATE_EXPLOIT_PATTERNS = {
    # Core exploit: excessive chunk size field (4000+ zeros)
    "excessive_chunk_size": r"^0{4000,}",
    # Chunked encoding header (required for exploit)
    "chunked_encoding": r"Transfer-Encoding:\s*chunked",
    # Heap spray endpoint
    "hostcheck_endpoint": r"^/remote/hostcheck_validate$",
    # FortiGate-specific form fields (heap spray indicators)
    "heap_spray_fields": r"(sslvpn_websession|sslvpn_auth_id|sslvpn_logindomain)",
    # Structure corruption markers (CRLF + base64-like data)
    "structure_marker": r"\r\n[A-Za-z0-9+/=]{100,}",
    # ROP chain indicators
    "rop_indicators": r"(SSL_do_handshake|SSL_CTX_new|GOT|PLT|gadget)",
    # Post-exploitation payloads
    "nodejs_shell": r"/bin/node\s+-e",
    "reverse_shell": r"require\(['\"]child_process['\"]\)",
    "bind_shell": r"net\.createServer|net\.connect",
}

# FortiOS SSL VPN endpoints
FORTIGATE_ENDPOINTS = {
    "/remote/hostcheck_validate": "heap_spray",
    "/remote/login": "login_page",
    "/remote/logincheck": "auth_check",
    "/remote/logout": "logout",
    "/remote/info": "system_info",
    "/": "root",
    "//": "double_slash",  # Often used in overflow trigger
}

# FortiGate user-agents (scanners/exploit tools)
SCANNER_USER_AGENTS = [
    r"python-requests/",
    r"python-urllib/",
    r"curl/",
    r"Go-http-client/",
    r"Nuclei",
    r"Metasploit",
]


class FortiGateHandler(BaseHandler):
    """Custom handler for FortiGate SSL VPN emulation and CVE-2024-21762 detection."""

    def __init__(self, config: HoneypotConfig, definition=None):
        """Initialize handler."""
        super().__init__(config, definition)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._sessions: Dict[str, dict] = {}
        # Default FortiGate SSL VPN port (HTTPS)
        self._default_port = 10443

    async def start(self, port: Optional[int] = None) -> None:
        """Start the FortiGate honeypot server."""
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
            logger.info(f"FortiGate SSL VPN honeypot started on port {listen_port}")
        except OSError as e:
            logger.error(f"Failed to start FortiGate honeypot: {e}")
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
        logger.info("FortiGate SSL VPN honeypot stopped")

    def _setup_routes(self) -> None:
        """Setup routes to emulate FortiGate SSL VPN endpoints."""
        # SSL VPN specific endpoints
        self._app.router.add_route(
            "*", "/remote/hostcheck_validate", self._handle_hostcheck
        )
        self._app.router.add_get("/remote/login", self._handle_login)
        self._app.router.add_post("/remote/logincheck", self._handle_logincheck)
        self._app.router.add_get("/remote/logout", self._handle_logout)
        self._app.router.add_get("/remote/info", self._handle_info)

        # Root paths (used in overflow trigger)
        self._app.router.add_route("*", "/", self._handle_root)
        self._app.router.add_route("*", "//", self._handle_double_slash)

        # Catch-all for other paths
        self._app.router.add_route("*", "/{path:.*}", self._handle_generic)

    async def _handle_login(self, request: web.Request) -> web.Response:
        """Handle /remote/login - returns SSL VPN login page."""
        await self._log_reconnaissance(request, "login_page")

        # Simplified FortiGate login page
        login_html = """<!DOCTYPE html>
<html>
<head>
    <title>SSL-VPN Login</title>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head>
<body>
    <h1>FortiGate SSL-VPN Login</h1>
    <form method="post" action="/remote/logincheck">
        <input type="text" name="username" placeholder="Username">
        <input type="password" name="password" placeholder="Password">
        <input type="hidden" name="ajax" value="1">
        <button type="submit">Login</button>
    </form>
    <div id="version">v7.4.2 build2571</div>
</body>
</html>"""

        return web.Response(
            text=login_html,
            content_type="text/html",
            headers=self._get_fortigate_headers(),
        )

    async def _handle_logincheck(self, request: web.Request) -> web.Response:
        """Handle /remote/logincheck - authentication endpoint."""
        await self._log_reconnaissance(request, "auth_attempt")

        # Always fail authentication (honeypot)
        return web.json_response(
            {"ret": 1, "status": "failed", "message": "Invalid credentials"},
            status=401,
            headers=self._get_fortigate_headers(),
        )

    async def _handle_logout(self, request: web.Request) -> web.Response:
        """Handle /remote/logout."""
        await self._log_reconnaissance(request, "logout")

        return web.Response(
            text="<html><body>Logged out</body></html>",
            content_type="text/html",
            headers=self._get_fortigate_headers(),
        )

    async def _handle_info(self, request: web.Request) -> web.Response:
        """Handle /remote/info - system information endpoint."""
        await self._log_reconnaissance(request, "system_info")

        info = {
            "version": "v7.4.2",
            "build": "2571",
            "platform": "FortiGate-VM64",
            "serial": "FGVM" + "0" * 12,
        }

        return web.json_response(info, headers=self._get_fortigate_headers())

    async def _handle_hostcheck(self, request: web.Request) -> web.Response:
        """Handle /remote/hostcheck_validate - primary heap spray endpoint."""
        return await self._process_exploit_attempt(request, endpoint_type="hostcheck")

    async def _handle_root(self, request: web.Request) -> web.Response:
        """Handle / - root path."""
        return await self._process_exploit_attempt(request, endpoint_type="root")

    async def _handle_double_slash(self, request: web.Request) -> web.Response:
        """Handle // - double slash path (often used in overflow trigger)."""
        return await self._process_exploit_attempt(
            request, endpoint_type="double_slash"
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

        # Return generic FortiGate-style 404
        return web.Response(
            text="<html><body>404 Not Found</body></html>",
            status=404,
            content_type="text/html",
            headers=self._get_fortigate_headers(),
        )

    async def _process_exploit_attempt(
        self, request: web.Request, endpoint_type: str
    ) -> web.Response:
        """Process potential CVE-2024-21762 exploit attempts."""
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
        transfer_encoding = headers.get("Transfer-Encoding", "").lower()
        user_agent = headers.get("User-Agent", "")
        body = ""

        try:
            # Read body carefully (might be chunked or large)
            body = await request.text()
        except Exception:
            pass  # nosec B110

        # Build full payload for analysis
        full_payload = f"{method} {path}\nHeaders: {headers}\nBody: {body}"

        # Detect CVE-2024-21762 patterns
        detected_patterns, is_fortigate_exploit = self._analyze_fortigate_payload(
            body, path, transfer_encoding, method, headers
        )

        # Check for scanner user-agents
        is_scanner = any(
            re.search(pattern, user_agent, re.IGNORECASE)
            for pattern in SCANNER_USER_AGENTS
        )
        if is_scanner:
            detected_patterns.append("known_scanner")

        # Determine severity and category
        if is_fortigate_exploit:
            category = AttackCategory.EXPLOIT_ATTEMPT
            severity = AttackSeverity.CRITICAL
        elif detected_patterns:
            category = AttackCategory.RECONNAISSANCE
            severity = AttackSeverity.HIGH
        else:
            # Still log suspicious requests
            base_detected, category = self.detect_patterns(full_payload)
            detected_patterns = base_detected
            severity = self.calculate_severity(category, detected_patterns)

        # Create event if patterns detected or suspicious activity
        if detected_patterns or (method == "POST" and transfer_encoding == "chunked"):
            # Sanitize payload for LLM safety
            sanitized_body = sanitize_for_llm(body, max_length=2000)

            event = AttackEvent(
                event_id=self._generate_event_id(),
                session_id=session_id,
                protocol=HoneypotProtocol.HTTP,
                timestamp=datetime.now(timezone.utc),
                source_ip=source_ip,
                source_port=source_port,
                event_type="fortigate_exploit"
                if is_fortigate_exploit
                else "fortigate_probe",
                raw_data=full_payload[: self.config.max_payload_size_kb * 1024],
                http_method=method,
                http_path=path,
                http_headers=headers,
                http_body=sanitized_body,
                detected_patterns=detected_patterns,
                category=category,
                severity=severity,
                matched_cves=["CVE-2024-21762"] if is_fortigate_exploit else [],
            )

            asyncio.create_task(self.emit_event(event))
            logger.info(
                f"FortiGate exploit attempt from {source_ip}: "
                f"patterns={detected_patterns}, exploit={is_fortigate_exploit}"
            )

        # Generate realistic response
        return self._generate_exploit_response(
            endpoint_type, is_fortigate_exploit, method
        )

    def _analyze_fortigate_payload(
        self,
        body: str,
        path: str,
        transfer_encoding: str,
        method: str,
        headers: Dict[str, str],
    ) -> Tuple[List[str], bool]:
        """Analyze if the payload matches CVE-2024-21762 exploit patterns.

        Returns:
            Tuple of (detected_pattern_names, is_fortigate_exploit)
        """
        detected = []
        is_exploit = False

        # Phase 1: Detect heap spray attempt
        is_heap_spray = False
        if re.search(FORTIGATE_EXPLOIT_PATTERNS["hostcheck_endpoint"], path):
            detected.append("hostcheck_endpoint")
            is_heap_spray = True

            # Check for heap spray form fields
            if re.search(FORTIGATE_EXPLOIT_PATTERNS["heap_spray_fields"], body):
                detected.append("heap_spray_fields")

        # Phase 2: Detect chunked encoding overflow
        is_chunked_overflow = False
        if "chunked" in transfer_encoding:
            detected.append("chunked_encoding")

            # Check for excessive chunk size field (4000+ zeros)
            if re.search(FORTIGATE_EXPLOIT_PATTERNS["excessive_chunk_size"], body):
                detected.append("excessive_chunk_size")
                is_chunked_overflow = True

        # Check for structure corruption markers
        if re.search(FORTIGATE_EXPLOIT_PATTERNS["structure_marker"], body):
            detected.append("structure_marker")

        # Check for ROP chain indicators
        if re.search(FORTIGATE_EXPLOIT_PATTERNS["rop_indicators"], body, re.IGNORECASE):
            detected.append("rop_indicators")

        # Check for post-exploitation payloads
        if re.search(FORTIGATE_EXPLOIT_PATTERNS["nodejs_shell"], body):
            detected.append("nodejs_shell")
        if re.search(FORTIGATE_EXPLOIT_PATTERNS["reverse_shell"], body):
            detected.append("reverse_shell")
        if re.search(FORTIGATE_EXPLOIT_PATTERNS["bind_shell"], body):
            detected.append("bind_shell")

        # CVE-2024-21762 signature:
        # 1. Heap spray OR chunked encoding with overflow markers
        # 2. Additional exploitation indicators (structure/ROP/shell)
        exploitation_indicators = (
            "structure_marker" in detected
            or "rop_indicators" in detected
            or "nodejs_shell" in detected
            or "reverse_shell" in detected
        )

        if (is_heap_spray or is_chunked_overflow) and exploitation_indicators:
            is_exploit = True
        elif is_chunked_overflow and "excessive_chunk_size" in detected:
            # Even without other indicators, excessive chunk size is highly suspicious
            is_exploit = True

        return detected, is_exploit

    def _generate_exploit_response(
        self, endpoint_type: str, is_exploit: bool, method: str
    ) -> web.Response:
        """Generate realistic FortiGate response to keep attacker engaged."""
        headers = self._get_fortigate_headers()
        headers = self.mask_response_headers(headers)

        if is_exploit:
            # Simulate crash/error (indicates vulnerability might exist)
            # This keeps attacker engaged without exposing real system
            return web.Response(
                text="",
                status=500,
                headers=headers,
            )

        # Normal responses based on endpoint
        if endpoint_type == "hostcheck":
            # Successful hostcheck response
            return web.json_response(
                {"ret": 0, "status": "success"},
                headers=headers,
            )
        elif endpoint_type in ["root", "double_slash"]:
            # Redirect to login
            return web.Response(
                status=302,
                headers={**headers, "Location": "/remote/login"},
            )
        else:
            return web.Response(
                text="<html><body>OK</body></html>",
                content_type="text/html",
                headers=headers,
            )

    def _get_fortigate_headers(self) -> Dict[str, str]:
        """Get realistic FortiGate response headers."""
        return {
            "Server": "xxxxxxxx-xxxxx",  # FortiGate obfuscated server header
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'",
        }

    async def _log_reconnaissance(self, request: web.Request, recon_type: str) -> None:
        """Log reconnaissance requests (login page probes, etc.)."""
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
            event_type=f"fortigate_{recon_type}",
            raw_data=f"{request.method} {request.path}",
            http_method=request.method,
            http_path=request.path,
            http_headers=headers,
            detected_patterns=[recon_type],
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
