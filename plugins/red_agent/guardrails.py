"""
Red Agent guardrails.

Pre-flight enforcement layer that every scan request must pass before
the orchestrator schedules it. Mirrors the pattern used by BrowserAgent
SSRF protection and integrates with core.human for HITL approvals on
intrusive operations.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from core.observability.logging import get_logger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.models import ScanIntensity, ScanRequest, Target, TargetType

logger = get_logger(__name__)


class GuardrailViolation(Exception):
    """Raised when a scan request violates a guardrail."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass
class GuardrailDecision:
    allowed: bool
    needs_human_approval: bool
    reason: str
    violations: list[str]


class TargetGuardrails:
    """SSRF + scope enforcement."""

    def __init__(self, config: RedAgentConfig) -> None:
        self.config = config

    def validate(
        self,
        target: Target,
        *,
        extra_scope: Iterable[str] | None = None,
    ) -> None:
        # Local binary samples are quarantined files identified by sha256;
        # they have no network host, so SSRF/scope checks do not apply.
        if target.type == TargetType.BINARY:
            return
        # SYSTEM = the host running the orchestrator itself; the scanner
        # reads local files only and never opens a network socket.
        if target.type == TargetType.SYSTEM:
            return
        # Scheme check runs before host extraction so file://, javascript:,
        # data: are rejected even when no hostname is present.
        self._reject_unsafe_scheme(target)

        host = self._extract_host(target)
        if not host:
            raise GuardrailViolation(
                "INVALID_TARGET", f"Cannot extract host from {target.value!r}"
            )

        target_allow_internal = bool(target.metadata.get("allow_internal"))
        if not (self.config.allow_internal_targets or target_allow_internal):
            self._reject_private(host)

        # An explicit per-target ``allow_internal`` opt-in is taken as
        # operator acceptance of scope: the user picked this loopback /
        # private host on purpose, so we do not also gate them on the
        # global scope_allowlist (which is intended for public bug-bounty
        # surfaces). Public targets still go through the full check.
        if target_allow_internal:
            return

        # Per-target scope additions: when an operator created the target
        # in the catalog they implicitly own it, so we let them attach
        # extra scope tokens (typically the target's own host or its
        # parent zone) without mutating the global ``scope_allowlist``.
        target_extra_scope = target.metadata.get("extra_scope")
        merged_scope: list[str] = []
        if extra_scope:
            merged_scope.extend(extra_scope)
        if isinstance(target_extra_scope, list):
            merged_scope.extend(str(s) for s in target_extra_scope)

        if not self._in_scope(host, merged_scope or None):
            raise GuardrailViolation(
                "OUT_OF_SCOPE",
                f"Target {host!r} not in scope_allowlist and bug_bounty_mode disabled",
            )

    @staticmethod
    def _extract_host(target: Target) -> str | None:
        if target.type == TargetType.URL:
            parsed = urlparse(target.value)
            return parsed.hostname
        return target.value

    def _reject_unsafe_scheme(self, target: Target) -> None:
        if target.type != TargetType.URL:
            return
        parsed = urlparse(target.value)
        if parsed.scheme not in {"http", "https"}:
            raise GuardrailViolation(
                "UNSAFE_SCHEME",
                f"Scheme {parsed.scheme!r} is not allowed; use http/https",
            )

    def _reject_private(self, host: str) -> None:
        for ip in self._resolve(host):
            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise GuardrailViolation(
                    "SSRF_BLOCKED",
                    f"Target {host!r} resolves to {ip} (private/loopback/link-local).",
                )

    @staticmethod
    def _resolve(host: str) -> Iterable[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            ip = ipaddress.ip_address(host)
            yield ip
            return
        except ValueError:
            pass
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return
        seen: set[str] = set()
        for info in infos:
            addr = str(info[4][0])
            if addr in seen:
                continue
            seen.add(addr)
            try:
                yield ipaddress.ip_address(addr)
            except ValueError:
                continue

    def _in_scope(
        self,
        host: str,
        extra_scope: Iterable[str] | None = None,
    ) -> bool:
        if self.config.bug_bounty_mode:
            return True
        candidates = list(self.config.scope_allowlist)
        if extra_scope:
            candidates.extend(extra_scope)
        if not candidates:
            return False

        for entry in candidates:
            if self._matches_entry(host, entry):
                return True
        return False

    @staticmethod
    def _matches_entry(host: str, entry: str) -> bool:
        if entry == host or host.endswith("." + entry.lstrip(".")):
            return True
        try:
            net = ipaddress.ip_network(entry, strict=False)
            for ip in TargetGuardrails._resolve(host):
                if ip.version == net.version and ip in net:
                    return True
        except ValueError:
            return False
        return False


class IntensityGuardrails:
    """HITL gating for active/intrusive scans."""

    def __init__(self, config: RedAgentConfig) -> None:
        self.config = config

    def evaluate(self, request: ScanRequest) -> GuardrailDecision:
        violations: list[str] = []
        needs_hitl = False
        reason = "passive scan auto-approved"

        if request.intensity == ScanIntensity.INTRUSIVE:
            if not self.config.require_hitl_for_active:
                # Intrusive scans must always go through human approval; if
                # the HITL gate is off there is no review surface, so block.
                violations.append("INTRUSIVE_REQUIRES_HITL")
            needs_hitl = True
            reason = "intrusive scan requires human approval"

        if (
            request.intensity == ScanIntensity.ACTIVE
            and self.config.require_hitl_for_active
        ):
            needs_hitl = True
            reason = "active scan requires human approval"

        if (
            "sqlmap" in request.scanners
            and request.intensity != ScanIntensity.INTRUSIVE
        ):
            violations.append("SQLMAP_REQUIRES_INTRUSIVE_INTENSITY")

        return GuardrailDecision(
            allowed=not violations,
            needs_human_approval=needs_hitl,
            reason=reason,
            violations=violations,
        )


class GuardrailPipeline:
    """Bundles all guardrail checks in execution order."""

    def __init__(self, config: RedAgentConfig) -> None:
        self.target = TargetGuardrails(config)
        self.intensity = IntensityGuardrails(config)

    def check(
        self,
        request: ScanRequest,
        *,
        extra_scope: Iterable[str] | None = None,
    ) -> GuardrailDecision:
        self.target.validate(request.target, extra_scope=extra_scope)
        return self.intensity.evaluate(request)
