"""SPIFFE URI parsing rules enforced by TenantInterceptor.

These exercise the regex-level invariants without spinning up a real
gRPC server. Wire-level tests live under ``tests/integration/``.
"""

from __future__ import annotations

import pytest

from plugins.red_agent.grpc.tenant_interceptor import _SPIFFE_URI_RE


@pytest.mark.parametrize(
    "uri,tenant,uuid_str",
    [
        (
            "spiffe://baselith.io/tenant/acme-prod/agent/"
            "12345678-1234-5678-1234-567812345678",
            "acme-prod",
            "12345678-1234-5678-1234-567812345678",
        ),
        (
            "spiffe://example.com/tenant/team_42@example/agent/"
            "abcdef00-0000-4000-8000-000000000001",
            "team_42@example",
            "abcdef00-0000-4000-8000-000000000001",
        ),
    ],
)
def test_valid_spiffe_uris_match(uri: str, tenant: str, uuid_str: str) -> None:
    m = _SPIFFE_URI_RE.match(uri)
    assert m is not None
    assert m.group("tenant_id") == tenant
    assert m.group("agent_uuid") == uuid_str


@pytest.mark.parametrize(
    "uri",
    [
        # No tenant segment
        "spiffe://baselith.io/agent/12345678-1234-5678-1234-567812345678",
        # Wrong scheme
        "https://baselith.io/tenant/x/agent/12345678-1234-5678-1234-567812345678",
        # Trailing path
        "spiffe://baselith.io/tenant/x/agent/"
        "12345678-1234-5678-1234-567812345678/extra",
        # Bad UUID length
        "spiffe://baselith.io/tenant/x/agent/12345678-not-a-uuid",
        # Unsafe character in tenant
        "spiffe://baselith.io/tenant/with space/agent/"
        "12345678-1234-5678-1234-567812345678",
    ],
)
def test_invalid_spiffe_uris_rejected(uri: str) -> None:
    assert _SPIFFE_URI_RE.match(uri) is None
