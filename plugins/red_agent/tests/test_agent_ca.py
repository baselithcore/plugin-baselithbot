"""Unit tests for the endpoint-daemon AgentCAService.

Validates the CSR validation rules and the cert issuance pipeline
end-to-end against an in-memory self-signed CA.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from plugins.red_agent.crypto.ca import (
    AgentCAConfig,
    AgentCAService,
    CSRValidationError,
    generate_self_signed_ca,
)


@pytest.fixture()
def loaded_ca(tmp_path: Path) -> AgentCAService:
    cert_pem, key_pem = generate_self_signed_ca("test CA")
    cert_path = tmp_path / "ca.crt"
    key_path = tmp_path / "ca.key"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)
    config = AgentCAConfig(cert_pem_path=cert_path, key_pem_path=key_path)
    ca = AgentCAService(config)
    ca.load()
    return ca


def _ed25519_csr() -> str:
    key = ed25519.Ed25519PrivateKey.generate()
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "agent")]))
        .sign(key, None)
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode("ascii")


def test_issue_from_ed25519_csr_succeeds(loaded_ca: AgentCAService) -> None:
    tenant = "acme-prod"
    agent_uuid = uuid4()
    issued = loaded_ca.issue_from_csr(
        _ed25519_csr(), tenant_id=tenant, agent_uuid=agent_uuid
    )

    assert issued.spiffe_uri == (
        f"spiffe://baselith.io/tenant/{tenant}/agent/{agent_uuid}"
    )
    cert = x509.load_pem_x509_certificate(issued.cert_pem.encode("ascii"))
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    uris = san.value.get_values_for_type(x509.UniformResourceIdentifier)
    assert uris == [issued.spiffe_uri]

    eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    assert ExtendedKeyUsageOID.CLIENT_AUTH in eku.value
    bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
    assert bc.value.ca is False


def test_issue_caps_validity_at_max(loaded_ca: AgentCAService) -> None:
    issued = loaded_ca.issue_from_csr(
        _ed25519_csr(),
        tenant_id="t1",
        agent_uuid=uuid4(),
        validity_days=365,  # well above 90-day cap
    )
    span = issued.not_after - issued.not_before
    # 90 days + 5 minutes of skew tolerance
    assert 89 <= span.days <= 91


def test_issue_rejects_rsa_csr(loaded_ca: AgentCAService) -> None:
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "agent")]))
        .sign(rsa_key, hash_alg())
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("ascii")
    with pytest.raises(CSRValidationError, match="ed25519"):
        loaded_ca.issue_from_csr(csr_pem, tenant_id="t1", agent_uuid=uuid4())


def hash_alg():  # type: ignore[no-untyped-def]
    """Return SHA-256 hash for RSA CSR signing (kept local to avoid extra import)."""
    from cryptography.hazmat.primitives import hashes

    return hashes.SHA256()


def test_issue_rejects_csr_with_san(loaded_ca: AgentCAService) -> None:
    """Agents cannot pre-declare their own SAN; the issuer is authoritative."""
    key = ed25519.Ed25519PrivateKey.generate()
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "agent")]))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.UniformResourceIdentifier("spiffe://evil.example/agent/x")]
            ),
            critical=False,
        )
        .sign(key, None)
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("ascii")
    with pytest.raises(CSRValidationError, match="forbidden extension"):
        loaded_ca.issue_from_csr(csr_pem, tenant_id="t1", agent_uuid=uuid4())


def test_issue_rejects_garbage_pem(loaded_ca: AgentCAService) -> None:
    with pytest.raises(CSRValidationError, match="PEM"):
        loaded_ca.issue_from_csr(
            "-----BEGIN CERTIFICATE REQUEST-----\nGARBAGE\n-----END CERTIFICATE REQUEST-----\n",
            tenant_id="t1",
            agent_uuid=uuid4(),
        )


def test_root_fingerprint_is_stable(loaded_ca: AgentCAService) -> None:
    fp1 = loaded_ca.root_fingerprint_sha256
    fp2 = loaded_ca.root_fingerprint_sha256
    assert fp1 == fp2
    # Hex-encoded SHA-256 is 64 chars.
    assert len(fp1) == 64
    int(fp1, 16)  # raises if non-hex


def test_unloaded_service_raises(tmp_path: Path) -> None:
    config = AgentCAConfig(
        cert_pem_path=tmp_path / "no.crt",
        key_pem_path=tmp_path / "no.key",
    )
    ca = AgentCAService(config)
    with pytest.raises(RuntimeError, match="not loaded"):
        ca.issue_from_csr(_ed25519_csr(), tenant_id="t", agent_uuid=uuid4())


def test_not_before_accounts_for_clock_skew(loaded_ca: AgentCAService) -> None:
    issued = loaded_ca.issue_from_csr(
        _ed25519_csr(), tenant_id="t1", agent_uuid=uuid4()
    )
    now = datetime.now(timezone.utc)
    # not_before is 5 minutes in the past; tolerate execution overhead.
    assert (now - issued.not_before).total_seconds() >= 300 - 30
