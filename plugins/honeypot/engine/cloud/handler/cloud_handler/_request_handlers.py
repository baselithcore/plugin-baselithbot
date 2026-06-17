"""Request handler mixin for CloudManagementHandler."""

import asyncio
import hashlib
import time
import uuid
from datetime import datetime, timezone

from aiohttp import web

from .....events import HoneypotEvents, emit_honeypot_event
from .....models import AttackEvent, AttackSeverity, HoneypotProtocol
from ...models import (
    CloudAPICall,
    CloudAttackCategory,
    TLSFingerprint,
)
from ..helpers import (
    calculate_timing,
    create_attack_event,
    determine_trigger,
    extract_credentials,
)
from ..parsers import parse_aws_request


class RequestHandlersMixin:
    """Mixin providing HTTP request handler methods for the cloud honeypot."""

    async def _handle_metadata_request(self, request: web.Request) -> web.Response:
        """Handle IMDS metadata service requests (SSRF detection)."""
        source_ip = self._extract_source_ip(request)
        subpath = request.match_info.get("path", "")
        full_path = f"/latest/{subpath}"

        from core.observability.logging import get_logger

        logger = get_logger(__name__)
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

    async def _handle_imds_token(self, request: web.Request) -> web.Response:
        """Handle IMDSv2 token request (PUT /latest/api/token)."""
        source_ip = self._extract_source_ip(request)

        from core.observability.logging import get_logger

        logger = get_logger(__name__)
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

    async def _handle_health(self, _request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response(
            {
                "status": "healthy",
                "service": "cloud-management-api",
                "provider": self.provider.value,
            }
        )

    async def _handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming API request."""
        source_ip = self._extract_source_ip(request)
        source_port = 0
        now = time.time()

        # Rate limiting
        if not self.check_rate_limit(source_ip):
            from core.observability.logging import get_logger

            logger = get_logger(__name__)
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
