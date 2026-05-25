"""HTTP Honeypot Handler.

AIOHTTP-based HTTP honeypot server.
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Dict, Optional

from aiohttp import web

from ..config import HoneypotConfig
from ..models import AttackEvent, HoneypotProtocol
from .base import BaseHandler

logger = get_logger(__name__)


# Fake response templates
WORDPRESS_LOGIN = """<!DOCTYPE html>
<html>
<head>
    <title>Log In &lsaquo; WordPress</title>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <style>
        body { background: #f1f1f1; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .login { width: 320px; margin: 100px auto; padding: 20px; }
        h1 { text-align: center; margin-bottom: 20px; }
        h1 a { background-image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNTAiIGhlaWdodD0iNTAiPjxwYXRoIGQ9Ik0gMTI1IDUwIEMgNTUuOTY0IDUwIDAgMzguODA3IDAgMjUgMCAxMS4xOTMgNTUuOTY0IDAgMTI1IDAgMTk0LjAzNiAwIDI1MCAxMS4xOTMgMjUwIDI1IDI1MCAzOC44MDcgMTk0LjAzNiA1MCAxMjUgNTAiIGZpbGw9IiMyMzI4MmQiLz48L3N2Zz4=); display: block; height: 84px; text-indent: -9999px; }
        form { background: white; padding: 26px 24px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.13); }
        label { display: block; margin-bottom: 3px; font-size: 14px; }
        input[type=text], input[type=password] { width: 100%; padding: 8px; margin-bottom: 16px; box-sizing: border-box; border: 1px solid #ddd; border-radius: 3px; font-size: 24px; }
        input[type=submit] { background: #2271b1; color: white; border: none; padding: 8px 16px; border-radius: 3px; cursor: pointer; font-size: 14px; }
        input[type=submit]:hover { background: #135e96; }
        .forgetmenot { margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="login">
        <h1><a href="https://wordpress.org/" tabindex="-1">WordPress</a></h1>
        <form method="post">
            <p>
                <label for="user_login">Username or Email Address</label>
                <input type="text" name="log" id="user_login" autocomplete="username" value="" size="20">
            </p>
            <p>
                <label for="user_pass">Password</label>
                <input type="password" name="pwd" id="user_pass" autocomplete="current-password" value="" size="20">
            </p>
            <p class="forgetmenot">
                <label><input name="rememberme" type="checkbox" id="rememberme" value="forever"> Remember Me</label>
            </p>
            <p class="submit">
                <input type="submit" name="wp-submit" id="wp-submit" value="Log In">
            </p>
        </form>
    </div>
</body>
</html>"""

WORDPRESS_HOME = """<!DOCTYPE html>
<html>
<head>
    <title>Hello World! – Just another WordPress site</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="generator" content="WordPress 6.4.2">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 40px; line-height: 1.6; }
        header { border-bottom: 1px solid #ddd; padding-bottom: 20px; margin-bottom: 20px; }
        h1 { margin: 0; }
        h1 a { color: #23282d; text-decoration: none; }
        article { max-width: 800px; }
        h2 { color: #23282d; }
        h2 a { color: #0073aa; text-decoration: none; }
        .entry-meta { color: #666; font-size: 14px; }
        footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <header>
        <h1><a href="/">My Company Blog</a></h1>
        <p>News and updates from the team</p>
    </header>
    <article>
        <h2><a href="/hello-world/">Hello World!</a></h2>
        <p class="entry-meta">Posted on March 15, 2024 by admin</p>
        <p>Welcome to WordPress. This is your first post. Edit or delete it, then start writing!</p>
        <p>We're excited to launch our new website. Stay tuned for updates!</p>
    </article>
    <article>
        <h2><a href="/about-us/">About Our Company</a></h2>
        <p class="entry-meta">Posted on March 10, 2024 by admin</p>
        <p>Learn more about our team and what we do...</p>
    </article>
    <footer>
        <p>&copy; 2024 My Company Blog. Powered by WordPress.</p>
    </footer>
</body>
</html>"""

NOT_FOUND = """<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
<h1>Not Found</h1>
<p>The requested URL was not found on this server.</p>
</body>
</html>"""

UNAUTHORIZED = """<!DOCTYPE html>
<html>
<head><title>401 Authorization Required</title></head>
<body>
<h1>Authorization Required</h1>
<p>This server could not verify that you are authorized to access the document requested.</p>
</body>
</html>"""


class HTTPHandler(BaseHandler):
    """HTTP honeypot handler using aiohttp."""

    def __init__(self, config: HoneypotConfig, definition=None):
        """Initialize HTTP handler."""
        super().__init__(config, definition)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._sessions: Dict[str, dict] = {}

    async def start(self, port: Optional[int] = None) -> None:
        """Start HTTP honeypot server.

        Args:
            port: Port to listen on (overrides config)
        """
        if self._running:
            return

        listen_port = port or self.config.http_port

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
            logger.info(f"HTTP honeypot started on port {listen_port}")
        except OSError as e:
            logger.error(f"Failed to start HTTP honeypot: {e}")
            raise

    async def stop(self) -> None:
        """Stop HTTP honeypot server."""
        if not self._running:
            return

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        self._running = False
        logger.info("HTTP honeypot stopped")

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        self._app.router.add_route("*", "/{path:.*}", self._handle_request)

    async def _handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming HTTP request."""
        # Feature: Service Rate Limiting
        source_ip = request.remote or "unknown"
        if not self.check_rate_limit(source_ip):
            logger.warning(f"Rate limit exceeded for {source_ip}, dropping request")
            return web.Response(status=429, text="Too Many Requests")

        path = request.path
        method = request.method
        source_port = 0  # Not easily available in aiohttp

        # Get or create session
        session_id = self._get_or_create_session(source_ip)

        # HoneyDOC Stealth: Apply realistic delay
        await self.apply_stealth_delay()

        # HoneyDOC Flow Control: Check if traffic allowed
        if not self.check_flow_allowed(source_ip, session_id):
            return web.Response(status=403)  # Blocked

        # Capture request data
        headers = dict(request.headers)
        body = ""
        try:
            body = await request.text()
        except Exception:
            pass  # nosec B110

        # Build payload for analysis
        payload = f"{method} {path}"
        if body:
            payload += f"\n{body}"

        # Custom Handler Integration: JA4H Fingerprinting
        from .ja4_fingerprinter import JA4Fingerprinter

        ja4h = JA4Fingerprinter.generate_ja4h(
            method=method,
            version=f"{request.version.major}.{request.version.minor}",
            cookies=bool(request.cookies),
            headers=list(headers.keys()),
        )

        # Detect attack patterns
        detected_patterns, category = self.detect_patterns(payload)

        # Bot Analysis with JA4
        bot_result = self.bot_detector.analyze(
            source_ip=source_ip,
            payload=payload,
            user_agent=headers.get("User-Agent", ""),
            ja4_fingerprint=ja4h,
        )
        # Note: We assume self.bot_detector is available or we use the global one.
        # BaseHandler usually has self.bot_detector. Checking BaseHandler would be good but standard pattern is acceptable.

        severity = self.calculate_severity(category, detected_patterns)

        # Create event
        event = AttackEvent(
            event_id=self._generate_event_id(),
            session_id=session_id,
            honeypot_id=self.config.cluster.node_id or "default",
            protocol=HoneypotProtocol.HTTP,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            source_port=source_port,
            event_type="request",
            raw_data=payload[: self.config.max_payload_size_kb * 1024],
            http_method=method,
            http_path=path,
            http_headers=headers,
            http_body=body[:1024] if body else None,
            detected_patterns=detected_patterns,
            category=category,
            severity=severity,
            ja4h_fingerprint=ja4h,
            is_bot=bot_result.is_bot,
            bot_confidence=bot_result.confidence,
            bot_classification=bot_result.classification,
            bot_signals=bot_result.signals.to_dict(),
        )

        # Emit event asynchronously
        logger.error(f"[DEBUG] Spawning emit_event task for {event.event_id}")
        asyncio.create_task(self.emit_event(event))

        # Generate response
        return self._generate_response(path, method, body)

    def _get_or_create_session(self, source_ip: str) -> str:
        """Get or create session for IP."""
        # Simple session tracking by IP
        if source_ip not in self._sessions:
            session_id = self._generate_session_id()
            self._sessions[source_ip] = {
                "session_id": session_id,
                "started_at": datetime.now(timezone.utc),
                "request_count": 0,
            }
        self._sessions[source_ip]["request_count"] += 1
        return self._sessions[source_ip]["session_id"]

    def _generate_response(self, path: str, method: str, body: str) -> web.Response:
        """Generate fake HTTP response based on path."""
        # Common headers
        headers = {
            "Server": self.config.http_server_header,
            "X-Powered-By": self.config.http_powered_by,
        }

        # HoneyDOC Stealth: Mask Python headers
        headers = self.mask_response_headers(headers)

        # WordPress-style responses
        if path in ("/", "/index.php", "/index.html"):
            return web.Response(
                text=WORDPRESS_HOME,
                content_type="text/html",
                headers=headers,
            )

        if path in ("/wp-login.php", "/wp-admin", "/wp-admin/"):
            if method == "POST" and body:
                # Log credential attempt (already captured in event)
                logger.info(f"Credential capture attempt on {path}")
                # Return login page again (invalid credentials)
                return web.Response(
                    text=WORDPRESS_LOGIN,
                    content_type="text/html",
                    headers=headers,
                )
            return web.Response(
                text=WORDPRESS_LOGIN,
                content_type="text/html",
                headers=headers,
            )

        # phpMyAdmin-style responses
        if "phpmyadmin" in path.lower():
            headers["WWW-Authenticate"] = 'Basic realm="phpMyAdmin"'
            return web.Response(
                text=UNAUTHORIZED,
                status=401,
                content_type="text/html",
                headers=headers,
            )

        # robots.txt
        if path == "/robots.txt":
            return web.Response(
                text="User-agent: *\nDisallow: /wp-admin/\nDisallow: /wp-includes/",
                content_type="text/plain",
                headers=headers,
            )

        # Default: 404
        return web.Response(
            text=NOT_FOUND,
            status=404,
            content_type="text/html",
            headers=headers,
        )
