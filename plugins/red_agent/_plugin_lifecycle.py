"""Lifecycle helpers extracted from ``plugin.py``.

Hosts CA registration, FalkorDB graph client construction, and the
gRPC AgentChannel server bootstrap so ``plugin.py`` stays under the
500-line file cap.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.di.container import ServiceRegistry
from core.observability.logging import get_logger
from plugins.red_agent.config import RedAgentConfig

logger = get_logger(__name__)


def maybe_register_agent_ca() -> None:
    """Register the endpoint-daemon CA service when both PEM paths are set.

    ``RED_AGENT_CA_CERT_PATH`` + ``RED_AGENT_CA_KEY_PATH`` (ed25519
    PKCS#8) gate registration. Absent → ``/agents/enroll`` returns 503.
    """
    from plugins.red_agent.crypto import AgentCAConfig, AgentCAService

    cert_path = os.getenv("RED_AGENT_CA_CERT_PATH")
    key_path = os.getenv("RED_AGENT_CA_KEY_PATH")
    if not cert_path or not key_path:
        logger.warning(
            "red_agent.ca.unconfigured",
            extra={
                "reason": (
                    "RED_AGENT_CA_CERT_PATH / RED_AGENT_CA_KEY_PATH not set; "
                    "endpoint-daemon enrollment will return 503 until configured."
                ),
            },
        )
        return
    try:
        config = AgentCAConfig(
            cert_pem_path=Path(cert_path),
            key_pem_path=Path(key_path),
            spiffe_trust_domain=os.getenv(
                "RED_AGENT_SPIFFE_TRUST_DOMAIN", "baselith.io"
            ),
            backend_grpc_endpoint=os.getenv(
                "RED_AGENT_BACKEND_GRPC_ENDPOINT",
                "https://red-agent.local:443",
            ),
            max_validity_days=int(os.getenv("RED_AGENT_CERT_MAX_VALIDITY_DAYS", "90")),
        )
        service = AgentCAService(config)
        service.load()
        ServiceRegistry.register(AgentCAService, service)
    except Exception as e:  # noqa: BLE001
        logger.error(
            "red_agent.ca.load_failed",
            extra={"err": str(e), "cert_path": cert_path},
        )


def build_graph_client(config: RedAgentConfig) -> Any:
    """Connect to FalkorDB; returns None when the driver is missing or unreachable."""
    try:
        from falkordb import FalkorDB
    except ImportError:
        logger.warning("red_agent.graph.falkordb_missing_running_without_graph")
        return None

    try:
        password = (
            config.graph_password.get_secret_value() if config.graph_password else None
        )
        return FalkorDB(
            host=config.graph_host, port=config.graph_port, password=password
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "red_agent.graph.connect_failed",
            extra={"err": str(e)},
        )
        return None


async def maybe_start_grpc_server() -> Any | None:
    """Start the AgentChannel gRPC server if the toggle is enabled.

    Gated by ``RED_AGENT_GRPC_ENABLED=true`` (default off) so the
    plugin stays loadable in environments that have not yet
    provisioned PKI material or TLS-terminating proxy. The CA service
    is required because the interceptor needs a certs store to
    validate peer fingerprints. Returns the started server (so the
    caller can ``stop()`` on shutdown) or ``None`` when the toggle is
    off / dependencies are missing.
    """
    from plugins.red_agent.grpc import AgentGrpcServer
    from plugins.red_agent.persistence import (
        AgentAuditLog,
        AgentCertPersistence,
        AgentPersistence,
        AgentTelemetryStore,
    )

    if os.getenv("RED_AGENT_GRPC_ENABLED", "").lower() not in {"1", "true", "yes"}:
        logger.info(
            "red_agent.grpc.server.disabled",
            extra={"reason": "RED_AGENT_GRPC_ENABLED not set"},
        )
        return None

    agents = ServiceRegistry.get(AgentPersistence)
    certs = ServiceRegistry.get(AgentCertPersistence)
    audit = ServiceRegistry.get(AgentAuditLog)
    telemetry = ServiceRegistry.get(AgentTelemetryStore)
    if agents is None or certs is None or audit is None:
        logger.warning("red_agent.grpc.server.persistence_missing")
        return None

    server = AgentGrpcServer(
        agents=agents, certs=certs, audit=audit, telemetry=telemetry
    )
    try:
        started = await server.start()
    except Exception as e:  # noqa: BLE001
        logger.warning("red_agent.grpc.server.start_failed", extra={"err": str(e)})
        return None
    if started:
        return server
    return None
