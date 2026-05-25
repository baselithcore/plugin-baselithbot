"""JWT auditor.

Static analyser for sample JWTs supplied by the operator via
``Target.metadata['jwt_samples']`` (list of opaque token strings).
The auditor never crafts requests against the target — it inspects
each token offline and emits findings for the four high-impact
attack classes:

- ``alg=none`` — token header advertises the unsigned algorithm,
  meaning verification is delegated to a library that may accept
  unsigned tokens.
- **Weak HS256 secret** — token uses HS256; HMAC verifies against a
  small built-in wordlist of common weak secrets. A match yields a
  Critical finding.
- ``kid`` path traversal — header's ``kid`` value contains ``..`` /
  ``/`` segments. Vulnerable verifiers read the keystore by
  filename, so traversal turns the JWT into a file-read primitive.
- ``jku`` / ``x5u`` redirection — header references an external URL
  that the verifier may fetch to retrieve the public key.

Operators run the auditor by attaching captured tokens to a target
in the New Target wizard. The tokens are never persisted; the
finding's evidence carries header + payload claims only, never the
raw signature.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.models import Finding, ScanIntensity, Severity, Target
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


# Top-32 most-leaked HS256 secrets (CTFs + public dump audits).
_DEFAULT_HS256_WORDLIST = (
    "secret",
    "password",
    "test",
    "admin",
    "changeme",
    "12345",
    "123456",
    "1234567890",
    "qwerty",
    "letmein",
    "default",
    "jwt-secret",
    "supersecret",
    "topsecret",
    "secret123",
    "p@ssw0rd",
    "P@ssw0rd",
    "your-256-bit-secret",
    "key",
    "private",
    "private-key",
    "myjwtsecret",
    "node-secret",
    "spring-secret",
    "express-secret",
    "auth-secret",
    "api-secret",
    "api-key",
    "production",
    "staging",
    "development",
    "dev",
)


def _b64decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def _split_jwt(
    token: str,
) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes] | None:
    """Return ``(header, payload, signing_input, signature)`` or None.

    Lenient: accepts whitespace, ``Bearer `` prefix, and trims to the
    first three dot-separated segments. Returns None for anything that
    doesn't decode cleanly.
    """

    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    parts = token.split(".")
    if len(parts) < 3:
        return None
    h_seg, p_seg, s_seg = parts[0], parts[1], parts[2]
    try:
        header = json.loads(_b64decode(h_seg).decode("utf-8"))
        payload = json.loads(_b64decode(p_seg).decode("utf-8"))
        signature = _b64decode(s_seg)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None
    signing_input = f"{h_seg}.{p_seg}".encode("ascii")
    return header, payload, signing_input, signature


class JWTAuditScanner(Scanner):
    name = "jwt_audit"
    kind = ScannerKind.DAST
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
        ScanIntensity.INTRUSIVE,
    )
    requires_network = False
    default_timeout = 30

    def __init__(
        self,
        sandbox: Any = None,
        config: RedAgentConfig | None = None,
        timeout: int | None = None,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)  # type: ignore[arg-type]
        self._config = config

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if self._config is not None and not self._config.jwt_audit_enabled:
            return []
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        samples = meta.get("jwt_samples")
        if not isinstance(samples, list) or not samples:
            return []
        wordlist = self._wordlist()
        findings: list[Finding] = []
        for token in samples:
            if not isinstance(token, str):
                continue
            findings.extend(self._audit_token(token, wordlist, target))
        return findings

    def _wordlist(self) -> tuple[str, ...]:
        if self._config is None or not self._config.jwt_audit_hs256_wordlist_path:
            return _DEFAULT_HS256_WORDLIST
        path = Path(self._config.jwt_audit_hs256_wordlist_path)
        if not path.is_file():
            logger.warning(
                "red_agent.jwt_audit.wordlist_missing",
                extra={"path": str(path)},
            )
            return _DEFAULT_HS256_WORDLIST
        try:
            return tuple(
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        except OSError:
            return _DEFAULT_HS256_WORDLIST

    def _audit_token(
        self, token: str, wordlist: tuple[str, ...], target: Target
    ) -> list[Finding]:
        parsed = _split_jwt(token)
        if parsed is None:
            return []
        header, payload, signing_input, signature = parsed
        alg = str(header.get("alg", "")).lower()
        kid = header.get("kid")
        jku = header.get("jku")
        x5u = header.get("x5u")
        claims_summary = {
            "alg": alg,
            "iss": payload.get("iss"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
            "exp": payload.get("exp"),
        }

        findings: list[Finding] = []

        if alg == "none":
            findings.append(
                Finding(
                    scanner=self.name,
                    title="JWT alg=none accepted",
                    description=(
                        "Token uses the unsigned algorithm. Verifiers "
                        "that follow the spec accept it as valid; "
                        "attackers forge any payload."
                    ),
                    severity=Severity.CRITICAL,
                    target=target.value,
                    endpoint=str(payload.get("iss") or ""),
                    evidence={"header": header, "claims": claims_summary},
                    cwe="CWE-347",
                )
            )

        if alg == "hs256":
            cracked = self._crack_hs256(signing_input, signature, wordlist)
            if cracked is not None:
                findings.append(
                    Finding(
                        scanner=self.name,
                        title="JWT HS256 signed with weak secret",
                        description=(
                            "Token signature verifies against a "
                            f"{len(cracked)}-character secret from a "
                            "common-secrets wordlist. Operators may "
                            "forge arbitrary tokens for this issuer."
                        ),
                        severity=Severity.CRITICAL,
                        target=target.value,
                        endpoint=str(payload.get("iss") or ""),
                        evidence={
                            "header": header,
                            "claims": claims_summary,
                            "secret_length": len(cracked),
                            "wordlist_match": True,
                        },
                        cwe="CWE-326",
                        remediation=(
                            "Rotate the signing secret to a 32+ byte "
                            "random value, or migrate to RS256 / "
                            "EdDSA."
                        ),
                    )
                )

        if isinstance(kid, str) and ("../" in kid or kid.startswith("/")):
            findings.append(
                Finding(
                    scanner=self.name,
                    title="JWT kid path traversal candidate",
                    description=(
                        "Token header carries a ``kid`` value that "
                        "contains path traversal characters. "
                        "Verifiers that read the keystore by filename "
                        "may load arbitrary files."
                    ),
                    severity=Severity.HIGH,
                    target=target.value,
                    endpoint=str(payload.get("iss") or ""),
                    evidence={"kid": kid},
                    cwe="CWE-22",
                )
            )

        for h_field, name in (("jku", jku), ("x5u", x5u)):
            if isinstance(name, str) and name.startswith(("http://", "https://")):
                findings.append(
                    Finding(
                        scanner=self.name,
                        title=f"JWT {h_field} references external URL",
                        description=(
                            f"Token header includes a ``{h_field}`` URL. "
                            "Verifiers that fetch the URL to retrieve "
                            "the key are vulnerable to attacker-"
                            "controlled key substitution."
                        ),
                        severity=Severity.HIGH,
                        target=target.value,
                        endpoint=str(payload.get("iss") or ""),
                        evidence={h_field: name, "header": header},
                        cwe="CWE-918",
                        remediation=(
                            f"Pin the {h_field} URL to a known host, "
                            "or disable external key resolution."
                        ),
                    )
                )

        return findings

    def _crack_hs256(
        self,
        signing_input: bytes,
        signature: bytes,
        wordlist: tuple[str, ...],
    ) -> str | None:
        for candidate in wordlist:
            digest = hmac.new(
                candidate.encode("utf-8"), signing_input, hashlib.sha256
            ).digest()
            if hmac.compare_digest(digest, signature):
                return candidate
        return None
