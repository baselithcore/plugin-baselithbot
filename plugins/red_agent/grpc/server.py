"""gRPC server bootstrap for the AgentChannel.

Hosts the bidirectional ``OpenStream`` RPC on a separate port from the
FastAPI HTTP surface (default 50443). Production deployments terminate
mTLS at an upstream Envoy and forward plaintext HTTP/2 to this server
on a private network; the server still validates the peer cert
fingerprint via the :class:`TenantInterceptor`. The handler can also
terminate TLS directly via ``server_credentials`` for single-binary
local-dev / on-prem deployments.

Lifecycle ownership:

* Started during the plugin's ``initialize`` phase, after persistence
  and the CA service are registered.
* Stopped during ``shutdown`` with a 5 s grace window so in-flight
  agent streams can drain (`AgentSession` honors stream cancellation).
* Failure to start is logged at WARNING and does not abort plugin
  load — a missing daemon channel must not break the rest of the
  plugin in dev / test environments without identity material.
"""

from __future__ import annotations

import asyncio
import os

import grpc
from grpc import aio as grpc_aio

from core.observability.logging import get_logger
from plugins.red_agent.persistence.agent_audit import AgentAuditLog
from plugins.red_agent.persistence.agent_certs import AgentCertPersistence
from plugins.red_agent.persistence.agent_telemetry import AgentTelemetryStore
from plugins.red_agent.persistence.agents import AgentPersistence
from plugins.red_agent.proto._generated import agent_pb2_grpc

from .servicer import AgentChannelServicer
from .tenant_interceptor import TenantInterceptor

logger = get_logger(__name__)


DEFAULT_BIND_HOST = "0.0.0.0"  # nosec B104  # noqa: S104  bound on internal cluster network only
DEFAULT_BIND_PORT = 50443
GRACEFUL_SHUTDOWN_SECONDS = 5
MAX_MESSAGE_SIZE_BYTES = 4 * 1024 * 1024
KEEPALIVE_TIME_MS = 20_000
KEEPALIVE_TIMEOUT_MS = 5_000


class AgentGrpcServer:
    """Owns the ``grpc.aio.Server`` instance for the daemon channel."""

    def __init__(
        self,
        *,
        agents: AgentPersistence,
        certs: AgentCertPersistence,
        audit: AgentAuditLog,
        telemetry: AgentTelemetryStore | None = None,
        bind_host: str | None = None,
        bind_port: int | None = None,
        tls_credentials: grpc.ServerCredentials | None = None,
    ) -> None:
        self._agents = agents
        self._certs = certs
        self._audit = audit
        self._telemetry = telemetry
        self._bind_host = bind_host or os.getenv(
            "RED_AGENT_GRPC_BIND_HOST", DEFAULT_BIND_HOST
        )
        self._bind_port = bind_port or int(
            os.getenv("RED_AGENT_GRPC_BIND_PORT", str(DEFAULT_BIND_PORT))
        )
        self._tls_credentials = tls_credentials
        self._server: grpc_aio.Server | None = None

    async def start(self) -> bool:
        """Build, register, and start the gRPC server.

        Returns True on success, False on graceful failure (e.g.
        port already bound). The plugin keeps loading either way.
        """
        if self._server is not None:
            return True

        interceptor = TenantInterceptor(certs=self._certs)
        server = grpc_aio.server(
            interceptors=(interceptor,),
            options=(
                ("grpc.max_send_message_length", MAX_MESSAGE_SIZE_BYTES),
                ("grpc.max_receive_message_length", MAX_MESSAGE_SIZE_BYTES),
                ("grpc.keepalive_time_ms", KEEPALIVE_TIME_MS),
                ("grpc.keepalive_timeout_ms", KEEPALIVE_TIMEOUT_MS),
                ("grpc.keepalive_permit_without_calls", 1),
                # Reject HTTP/2 PINGs sent more often than every 10s
                # by misbehaving clients.
                ("grpc.http2.min_ping_interval_without_data_ms", 10_000),
            ),
        )

        servicer = AgentChannelServicer(
            agents=self._agents,
            audit=self._audit,
            telemetry=self._telemetry,
        )
        agent_pb2_grpc.add_AgentChannelServicer_to_server(servicer, server)

        bind = f"{self._bind_host}:{self._bind_port}"
        try:
            if self._tls_credentials is not None:
                server.add_secure_port(bind, self._tls_credentials)
                logger.info(
                    "red_agent.grpc.server.binding_secure",
                    extra={"bind": bind},
                )
            else:
                # Plaintext binding is for upstream-terminated TLS only
                # (Envoy / ALB sidecar). In production this MUST be
                # bound to a private network interface.
                server.add_insecure_port(bind)
                logger.warning(
                    "red_agent.grpc.server.binding_insecure",
                    extra={
                        "bind": bind,
                        "reason": (
                            "tls_credentials not supplied; relying on "
                            "upstream proxy mTLS termination. The interceptor "
                            "still requires a SPIFFE peer identity."
                        ),
                    },
                )
        except RuntimeError as exc:
            logger.warning(
                "red_agent.grpc.server.bind_failed",
                extra={"bind": bind, "error": str(exc)},
            )
            return False

        await server.start()
        self._server = server
        logger.info(
            "red_agent.grpc.server.started",
            extra={"bind": bind},
        )
        return True

    async def stop(self) -> None:
        if self._server is None:
            return
        try:
            await asyncio.wait_for(
                self._server.stop(GRACEFUL_SHUTDOWN_SECONDS),
                timeout=GRACEFUL_SHUTDOWN_SECONDS + 2,
            )
        except asyncio.TimeoutError:
            logger.warning("red_agent.grpc.server.stop_timeout")
        finally:
            self._server = None
            logger.info("red_agent.grpc.server.stopped")

    @property
    def running(self) -> bool:
        return self._server is not None
