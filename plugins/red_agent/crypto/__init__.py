"""Crypto primitives for the Red Agent endpoint daemon control plane.

This subpackage hosts CA / signing / verification helpers that the
plugin needs to issue agent certs and verify signed bundles. All
externally-facing key material is wrapped in ``pydantic.SecretStr`` at
the configuration boundary; this module deals only with already-loaded
in-memory key objects from ``cryptography``.
"""

from .ca import (
    AgentCAConfig,
    AgentCAService,
    CSRValidationError,
    IssuedCert,
)

__all__ = [
    "AgentCAConfig",
    "AgentCAService",
    "CSRValidationError",
    "IssuedCert",
]
