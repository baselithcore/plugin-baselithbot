"""gRPC server-side wiring for the endpoint-daemon AgentChannel.

The Python service hosts the bidirectional ``Connect`` stream, the
mTLS interceptor that resolves tenant identity from the peer cert
SAN, and the wiring into the existing persistence layer. Generated
stubs live in ``plugins.red_agent.proto._generated`` and are mirrored
to the Rust daemon repo via the same ``agent.proto`` source.
"""

from .server import AgentGrpcServer
from .servicer import AgentChannelServicer
from .tenant_interceptor import (
    TenantContext,
    TenantInterceptor,
    TenantResolutionError,
)

__all__ = [
    "AgentChannelServicer",
    "AgentGrpcServer",
    "TenantContext",
    "TenantInterceptor",
    "TenantResolutionError",
]
