"""mTLS peer-cert → tenant context resolution for the AgentChannel.

The interceptor extracts the SPIFFE-style URI SAN from the peer
certificate at handshake time and decodes ``tenant_id`` and
``agent_uuid`` from it. Both values flow through the request as a
:class:`TenantContext` attached to the gRPC ``ServicerContext``;
downstream handlers retrieve them via :func:`tenant_context_from`.

Trust invariants:

* The interceptor only trusts values derived from
  ``peer_identities`` / ``auth_context``. Anything in metadata
  headers is informational and never authoritative.
* Cert revocation is checked against the
  :class:`AgentCertPersistence` store (active cert with matching
  fingerprint required). Revoked / rotated / expired certs are
  rejected before the servicer body runs.
* On any resolution failure the RPC is closed with
  ``UNAUTHENTICATED`` — never with a deserialization error that
  could leak protocol-level information.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

import grpc
from grpc.aio import ServerInterceptor

from core.observability.logging import get_logger
from plugins.red_agent.persistence.agent_certs import AgentCertPersistence

logger = get_logger(__name__)


_SPIFFE_URI_RE = re.compile(
    r"^spiffe://(?P<trust_domain>[a-z0-9.\-]+)"
    r"/tenant/(?P<tenant_id>[a-zA-Z0-9_:.\-@]+)"
    r"/agent/(?P<agent_uuid>[0-9a-fA-F\-]{36})$"
)


class TenantResolutionError(Exception):
    """Raised when peer cert cannot be mapped to a tenant context."""


@dataclass(frozen=True)
class TenantContext:
    """Authoritative identity attached to every authenticated RPC."""

    tenant_id: str
    agent_uuid: UUID
    spiffe_uri: str
    fingerprint_sha256: str


def tenant_context_from(context: grpc.aio.ServicerContext) -> TenantContext:
    """Recover the :class:`TenantContext` injected by the interceptor.

    Raises :class:`RuntimeError` if no context is attached — that
    indicates the interceptor is missing from the server pipeline,
    which is a configuration bug, not a runtime auth failure.
    """
    ctx = getattr(context, "_baselith_tenant_context", None)
    if ctx is None:
        raise RuntimeError(
            "TenantContext not present — TenantInterceptor must be installed"
        )
    return ctx


class TenantInterceptor(ServerInterceptor):
    """Resolve tenant identity from peer cert before any servicer runs.

    The interceptor is async-only (server runs in ``grpc.aio``). It
    inspects ``context.auth_context()`` for the
    ``x509_subject_alternative_name`` entry, parses the SPIFFE URI,
    looks up the cert by its SHA-256 fingerprint, and verifies the
    cert is still ``active``. Resolution failure aborts the call with
    ``UNAUTHENTICATED``.
    """

    def __init__(self, certs: AgentCertPersistence) -> None:
        self._certs = certs

    async def intercept_service(
        self,
        continuation: Callable[
            [grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]
        ],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        # Wrap each method type so the auth check runs once per call,
        # *before* the servicer body. We only need stream_stream for
        # AgentChannel.Connect, but the other branches stay correct
        # for future RPCs.
        if handler.stream_stream is not None:
            return self._wrap_stream_stream(handler)
        if handler.unary_unary is not None:
            return self._wrap_unary_unary(handler)
        if handler.unary_stream is not None:
            return self._wrap_unary_stream(handler)
        return handler

    # ----- internals -----------------------------------------------------

    async def _resolve(self, context: grpc.aio.ServicerContext) -> TenantContext:
        auth = context.auth_context()
        san_values = auth.get(b"x509_subject_alternative_name", []) or auth.get(
            "x509_subject_alternative_name", []
        )
        spiffe_uri: str | None = None
        for raw in san_values:
            value = raw.decode("ascii") if isinstance(raw, bytes) else str(raw)
            if value.startswith("URI:"):
                value = value[4:]
            if value.startswith("spiffe://"):
                spiffe_uri = value
                break
        if spiffe_uri is None:
            raise TenantResolutionError("peer cert lacks SPIFFE URI SAN")

        match = _SPIFFE_URI_RE.match(spiffe_uri)
        if match is None:
            raise TenantResolutionError(f"unrecognized SPIFFE URI: {spiffe_uri}")

        try:
            agent_uuid = UUID(match.group("agent_uuid"))
        except ValueError as exc:
            raise TenantResolutionError("malformed agent UUID") from exc
        tenant_id = match.group("tenant_id")

        # Cert fingerprint is the canonical revocation lookup key. We
        # accept whichever fingerprint identity gRPC exposes; if none
        # is available we treat the call as unauthenticated.
        fingerprint = self._extract_fingerprint(auth)
        if fingerprint is None:
            raise TenantResolutionError("peer cert fingerprint missing")

        cert = await self._certs.get_by_fingerprint(fingerprint, tenant_id=tenant_id)
        if cert is None or cert.state.value != "active":
            raise TenantResolutionError("cert not active or unknown")
        if cert.spiffe_uri != spiffe_uri or cert.agent_uuid != agent_uuid:
            raise TenantResolutionError("cert SPIFFE/UUID mismatch")

        return TenantContext(
            tenant_id=tenant_id,
            agent_uuid=agent_uuid,
            spiffe_uri=spiffe_uri,
            fingerprint_sha256=fingerprint,
        )

    @staticmethod
    def _extract_fingerprint(auth: dict[Any, Any]) -> str | None:
        """Return the lowercase hex SHA-256 of the leaf cert if present.

        gRPC's auth_context may expose the fingerprint under several
        keys depending on the server backend; we try the common ones.
        Returns None when nothing is available — the caller treats
        that as an authentication failure rather than guessing.
        """
        for key in (
            b"x509_pem_cert",
            "x509_pem_cert",
            b"transport_security_type_x509",
            "x509_subject",
        ):
            if key in auth:
                # We don't recompute the hash here — production servers
                # are expected to surface the SHA-256 explicitly. Many
                # do via a custom header set by the TLS terminator.
                pass
        for key in (b"x509_sha256_fingerprint", "x509_sha256_fingerprint"):
            value = auth.get(key)
            if value:
                first = value[0] if isinstance(value, list) else value
                if isinstance(first, bytes):
                    first = first.decode("ascii", errors="ignore")
                return first.lower()
        return None

    def _attach(
        self,
        context: grpc.aio.ServicerContext,
        tenant_ctx: TenantContext,
    ) -> None:
        # We intentionally use a private attribute name that mirrors
        # this plugin's namespace so a misconfigured interceptor stack
        # does not silently overwrite another framework's context.
        setattr(context, "_baselith_tenant_context", tenant_ctx)

    def _wrap_stream_stream(
        self, handler: grpc.RpcMethodHandler
    ) -> grpc.RpcMethodHandler:
        original = handler.stream_stream

        async def wrapped(
            request_iterator: Any, context: grpc.aio.ServicerContext
        ) -> Any:
            try:
                tenant_ctx = await self._resolve(context)
            except TenantResolutionError as exc:
                logger.warning(
                    "red_agent.grpc.auth_failed",
                    extra={"reason": str(exc)},
                )
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "agent identity rejected"
                )
                return
            self._attach(context, tenant_ctx)
            assert original is not None  # narrowed by the wrap path
            async for response in original(request_iterator, context):
                yield response

        return grpc.stream_stream_rpc_method_handler(
            wrapped,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    def _wrap_unary_unary(
        self, handler: grpc.RpcMethodHandler
    ) -> grpc.RpcMethodHandler:
        original = handler.unary_unary

        async def wrapped(request: Any, context: grpc.aio.ServicerContext) -> Any:
            try:
                tenant_ctx = await self._resolve(context)
            except TenantResolutionError as exc:
                logger.warning(
                    "red_agent.grpc.auth_failed",
                    extra={"reason": str(exc)},
                )
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "agent identity rejected"
                )
                return None
            self._attach(context, tenant_ctx)
            assert original is not None
            return await original(request, context)

        return grpc.unary_unary_rpc_method_handler(
            wrapped,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    def _wrap_unary_stream(
        self, handler: grpc.RpcMethodHandler
    ) -> grpc.RpcMethodHandler:
        original = handler.unary_stream

        async def wrapped(request: Any, context: grpc.aio.ServicerContext) -> Any:
            try:
                tenant_ctx = await self._resolve(context)
            except TenantResolutionError as exc:
                logger.warning(
                    "red_agent.grpc.auth_failed",
                    extra={"reason": str(exc)},
                )
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "agent identity rejected"
                )
                return
            self._attach(context, tenant_ctx)
            assert original is not None
            async for response in original(request, context):
                yield response

        return grpc.unary_stream_rpc_method_handler(
            wrapped,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
