"""GraphQL endpoint auditor.

Network-light scanner aimed at the four GraphQL misconfigurations
the OpenAPI fuzzer can't see:

- **Introspection enabled in production.** Posts the standard
  ``__schema`` introspection query. A non-empty types list means the
  schema is public — a Medium-severity finding.
- **Field-suggestion leakage.** Sends a query against a deliberately
  misspelt field. ``Did you mean "<field>"?`` responses leak the
  schema even when introspection is disabled.
- **Alias overload.** Sends a single document with a large number
  of aliased calls to the same root field. A 200 response means
  aliasing is unbounded — a low-severity DoS surface.
- **Batch attack.** Posts a JSON array of operations. The server
  accepting the batched payload exposes a request-amplification
  vector for brute-force / DoS.

The auditor is read-only; the alias-overload and batch probes use a
benign read-only query (``__typename`` against the root). Endpoint
discovery is operator-supplied via ``Target.metadata['graphql_path']``
(default ``/graphql``).
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


_INTROSPECTION_QUERY = "query IntrospectionQuery { __schema { types { name } } }"


class GraphQLAuditScanner(Scanner):
    name = "graphql_audit"
    kind = ScannerKind.DAST
    supports_intensity = (ScanIntensity.PASSIVE, ScanIntensity.ACTIVE)
    requires_network = True
    default_timeout = 60

    def __init__(
        self,
        sandbox: Any = None,
        timeout: int | None = None,
        *,
        request_timeout_seconds: float = 15.0,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)  # type: ignore[arg-type]
        self._request_timeout = request_timeout_seconds

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type not in (TargetType.URL, TargetType.HOSTNAME):
            return []
        endpoint = self._endpoint(target)
        if endpoint is None:
            return []

        findings: list[Finding] = []
        async with httpx.AsyncClient(timeout=self._request_timeout) as client:
            findings.extend(await self._check_introspection(client, endpoint, target))
            findings.extend(await self._check_suggestion(client, endpoint, target))
            findings.extend(await self._check_alias_overload(client, endpoint, target))
            findings.extend(await self._check_batch(client, endpoint, target))
        return findings

    def _endpoint(self, target: Target) -> str | None:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        path = meta.get("graphql_path") or "/graphql"
        if not isinstance(path, str):
            return None
        if target.type == TargetType.HOSTNAME:
            return f"https://{target.value.rstrip('/')}{path}"
        # URL target: append path if not already present.
        base = target.value.rstrip("/")
        if base.endswith(path):
            return base
        return f"{base}{path}"

    async def _post_json(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        payload: Any,
    ) -> tuple[int, dict[str, Any] | list[Any] | None]:
        try:
            resp = await client.post(endpoint, json=payload)
        except httpx.HTTPError as exc:
            logger.debug(
                "red_agent.graphql_audit.request_failed",
                extra={"endpoint": endpoint, "err": str(exc)},
            )
            return -1, None
        try:
            return resp.status_code, resp.json()
        except (ValueError, json.JSONDecodeError):
            return resp.status_code, None

    async def _check_introspection(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        target: Target,
    ) -> list[Finding]:
        status, body = await self._post_json(
            client, endpoint, {"query": _INTROSPECTION_QUERY}
        )
        if status != 200 or not isinstance(body, dict):
            return []
        types = ((body.get("data") or {}).get("__schema") or {}).get("types") or []
        if not isinstance(types, list) or not types:
            return []
        return [
            Finding(
                scanner=self.name,
                title="GraphQL introspection enabled",
                description=(
                    "The endpoint exposes the GraphQL introspection "
                    "schema. Production deployments should disable "
                    "introspection so attackers cannot enumerate types "
                    "and field signatures."
                ),
                severity=Severity.MEDIUM,
                target=target.value,
                endpoint=endpoint,
                evidence={"types_returned": len(types)},
                cwe="CWE-200",
                remediation=(
                    "Disable introspection in production: e.g. "
                    "Apollo's ``introspection: false`` option."
                ),
            )
        ]

    async def _check_suggestion(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        target: Target,
    ) -> list[Finding]:
        status, body = await self._post_json(
            client, endpoint, {"query": "{ __typenameXX }"}
        )
        if status not in (200, 400) or not isinstance(body, dict):
            return []
        errors = body.get("errors") or []
        if not isinstance(errors, list):
            return []
        for err in errors:
            if not isinstance(err, dict):
                continue
            msg = str(err.get("message", ""))
            if "Did you mean" in msg:
                return [
                    Finding(
                        scanner=self.name,
                        title="GraphQL field-suggestion leakage",
                        description=(
                            "The endpoint returns ``Did you mean ...?``"
                            " hints on misspelled fields. Even with "
                            "introspection disabled, this leaks "
                            "schema names to an attacker who probes "
                            "the API."
                        ),
                        severity=Severity.LOW,
                        target=target.value,
                        endpoint=endpoint,
                        evidence={"sample_message": msg[:200]},
                        cwe="CWE-200",
                    )
                ]
        return []

    async def _check_alias_overload(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        target: Target,
    ) -> list[Finding]:
        # 100 aliases of __typename. A safe limit (e.g. 50) returns 400.
        aliases = " ".join(f"a{i}: __typename" for i in range(100))
        query = "{ " + aliases + " }"
        status, body = await self._post_json(client, endpoint, {"query": query})
        if status == 200 and isinstance(body, dict) and "data" in body:
            return [
                Finding(
                    scanner=self.name,
                    title="GraphQL alias overload accepted",
                    description=(
                        "The endpoint accepts a single document with "
                        "100 aliased calls. Without an alias-count "
                        "limit, an attacker amplifies a single request "
                        "into many — useful for brute force and DoS."
                    ),
                    severity=Severity.LOW,
                    target=target.value,
                    endpoint=endpoint,
                    evidence={"alias_count": 100},
                    cwe="CWE-770",
                    remediation=("Install a depth/alias limiter (e.g. graphql-armor)."),
                )
            ]
        return []

    async def _check_batch(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        target: Target,
    ) -> list[Finding]:
        status, body = await self._post_json(
            client,
            endpoint,
            [{"query": "{ __typename }"}, {"query": "{ __typename }"}],
        )
        if status == 200 and isinstance(body, list) and len(body) >= 2:
            return [
                Finding(
                    scanner=self.name,
                    title="GraphQL batch operations accepted",
                    description=(
                        "The endpoint accepts JSON-array batched "
                        "operations. Combined with weak rate limits "
                        "this becomes a brute-force amplification "
                        "vector."
                    ),
                    severity=Severity.LOW,
                    target=target.value,
                    endpoint=endpoint,
                    evidence={"batched": True},
                    cwe="CWE-770",
                )
            ]
        return []
