"""Postgres persistence for Red Agent.

Stores immutable scan/finding records (single source of truth) for
audit, RBAC, multi-tenancy, and SARIF export. The graph layer is a
projection optimized for traversal queries.

This package is the modular replacement for the prior monolithic
``persistence.py``. Public API is preserved — callers continue to
``from plugins.red_agent.persistence import X``.
"""

from ._schema import SCHEMA_DDL, ensure_schema
from ._tenant import set_session_tenant, tenant_scope
from .agent_audit import AgentAuditLog
from .agent_certs import AgentCertPersistence
from .agent_telemetry import AgentTelemetryStore
from .agents import AgentPersistence
from .approvals import ApprovalPersistence
from .enrollment_tokens import EnrollmentTokenPersistence
from .engagements import EngagementPersistence
from .fingerprints import FingerprintStore
from .policy import PolicyStore
from .scans import RedAgentPersistence
from .targets import TargetPersistence

__all__ = [
    "SCHEMA_DDL",
    "AgentAuditLog",
    "AgentCertPersistence",
    "AgentPersistence",
    "AgentTelemetryStore",
    "ApprovalPersistence",
    "EnrollmentTokenPersistence",
    "EngagementPersistence",
    "FingerprintStore",
    "PolicyStore",
    "RedAgentPersistence",
    "TargetPersistence",
    "ensure_schema",
    "set_session_tenant",
    "tenant_scope",
]
