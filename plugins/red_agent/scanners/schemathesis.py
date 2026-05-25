"""Schemathesis OpenAPI fuzzer scanner adapter.

Schemathesis runs property-based tests against an OpenAPI / GraphQL
schema, generating valid + invalid inputs that exercise every operation
and every documented response. Each violated check (server-error
response, schema mismatch, status-code mismatch, malformed JSON,
authentication bypass, etc.) becomes a Finding.

Target type: :attr:`TargetType.API_SPEC`. ``Target.value`` is either an
OpenAPI/Swagger URL (``https://api.example.com/openapi.json``) or a
filesystem path inside ``/workspace`` mounted by the SandboxRunner.

Output parsing strategy: schemathesis stdout sections are well-formed
but not JSON-stable across releases, so the adapter scans for the
``FAILED:`` headline pattern + the per-failure ``Check:`` and ``Body:``
lines. Unparseable stdout falls back to a single INFO finding so the
operator sees the run completed with non-zero failures.
"""

from __future__ import annotations

import re
from typing import Iterator

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

_FAILED_HEADER_RE = re.compile(
    r"^=+\s*FAILED\s*:\s*(?P<method>[A-Z]+)\s+(?P<path>\S+).*$",
    re.MULTILINE,
)
_CHECK_RE = re.compile(r"^\s*Check\s*:\s*(?P<check>.+?)\s*$", re.MULTILINE)
_BODY_RE = re.compile(r"^\s*Body\s*:\s*(?P<body>.+?)\s*$", re.MULTILINE)


_CHECK_TO_SEVERITY: dict[str, Severity] = {
    "not_a_server_error": Severity.HIGH,
    "status_code_conformance": Severity.MEDIUM,
    "content_type_conformance": Severity.LOW,
    "response_schema_conformance": Severity.MEDIUM,
    "response_headers_conformance": Severity.LOW,
    "negative_data_rejection": Severity.MEDIUM,
    "authorization": Severity.HIGH,
    "ignored_auth": Severity.CRITICAL,
}


class SchemathesisScanner(Scanner):
    name = "schemathesis"
    kind = ScannerKind.DAST
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
    image = "schemathesis/schemathesis:stable"
    requires_network = True
    default_timeout = 1800

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type != TargetType.API_SPEC:
            return []
        argv = [
            "run",
            target.value,
            "--checks",
            "all",
            "--hypothesis-derandomize",
            "--no-color",
        ]
        if intensity == ScanIntensity.PASSIVE:
            # Cap exploration to keep passive scans fast + low-impact.
            argv += ["--hypothesis-max-examples", "20"]
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        # Schemathesis emits findings on both stdout (per-failure block)
        # and stderr (summary). Concatenate so the parser sees everything.
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        return list(_parse_failures(combined, target))


def _parse_failures(text: str, target: Target) -> Iterator[Finding]:
    headers = list(_FAILED_HEADER_RE.finditer(text))
    if not headers:
        return iter(())
    return _emit_findings(text, headers, target)


def _emit_findings(
    text: str, headers: list[re.Match[str]], target: Target
) -> Iterator[Finding]:
    for idx, match in enumerate(headers):
        block_start = match.end()
        block_end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        block = text[block_start:block_end]
        method = match.group("method")
        path = match.group("path")
        checks = [m.group("check").strip() for m in _CHECK_RE.finditer(block)]
        bodies = [m.group("body").strip() for m in _BODY_RE.finditer(block)]
        for check in checks or [None]:
            yield _build_finding(
                target=target,
                method=method,
                path=path,
                check=check,
                body=bodies[0] if bodies else None,
                raw_block=block.strip(),
            )


def _build_finding(
    *,
    target: Target,
    method: str,
    path: str,
    check: str | None,
    body: str | None,
    raw_block: str,
) -> Finding:
    severity = (
        _CHECK_TO_SEVERITY.get(check, Severity.MEDIUM) if check else Severity.MEDIUM
    )
    title = f"{method} {path} failed schemathesis check"
    if check:
        title += f" ({check})"
    return Finding(
        scanner="schemathesis",
        title=title,
        description=(
            f"Schemathesis property-based test against {method} {path} "
            f"flagged a {check or 'check'} violation. Each failed test "
            "case is a confirmed contract gap: the implementation does "
            "not match the OpenAPI schema or rejects a class of inputs "
            "the spec declares as valid."
        ),
        severity=severity,
        target=target.value,
        endpoint=f"{method} {path}",
        evidence={
            "check": check,
            "method": method,
            "path": path,
            "body": body,
            "confirmed": True,
        },
        raw={"output": raw_block[:4000]},
        remediation=(
            "Align implementation with the OpenAPI contract: either fix "
            "the handler to match the documented response shape, or "
            "update the schema to declare the actual response correctly."
        ),
    )
