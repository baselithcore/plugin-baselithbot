"""Tenant-aware ed25519 Certificate Authority for endpoint-daemon enrollment.

Phase 1 design: a single intermediate CA (loaded from disk at plugin
startup) signs every agent leaf cert. The SPIFFE-style URI SAN is
derived from ``tenant_id`` + ``agent_uuid`` so RLS server-side keeps
its single source of truth: the cert itself.

Phase 2 will introduce per-tenant Sub-CAs and an HSM/KMS backend; the
``AgentCAService`` interface is intentionally thin so that the
implementation can be swapped without touching callers.

Threat-model invariants enforced here:

* Refuse any CSR whose subject public key is **not** ed25519. RSA / EC
  certs would weaken the fleet baseline and complicate the daemon's
  trust anchor pinning.
* Refuse any CSR with embedded SAN, EKU, or BasicConstraints. The
  daemon does not get to choose its own identity — the issuer does.
* Cap the leaf cert validity at ``max_validity_days`` (default 90).
  A CSR cannot extend its own lifetime.
* The leaf SAN URI is computed server-side (tenant + uuid) and
  authenticated by issuance, never trusted from the CSR.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID

from core.observability.logging import get_logger

logger = get_logger(__name__)


class CSRValidationError(ValueError):
    """Raised when an agent-supplied CSR fails validation."""


@dataclass(frozen=True)
class AgentCAConfig:
    """File-backed CA configuration.

    The CA private key file is expected to be ed25519, PKCS#8, PEM-
    encoded. Keys MUST live on a tmpfs / memfd in production or in an
    HSM-backed KMS adapter (Phase 2). The plugin process must run with
    minimal filesystem access to these paths.
    """

    cert_pem_path: Path
    key_pem_path: Path
    spiffe_trust_domain: str = "baselith.io"
    backend_grpc_endpoint: str = "https://red-agent.local:443"
    max_validity_days: int = 90


@dataclass(frozen=True)
class IssuedCert:
    """Result of a successful CSR signing pass."""

    cert_pem: str
    chain_pem: str
    serial: str
    fingerprint_sha256: str
    spiffe_uri: str
    not_before: datetime
    not_after: datetime
    public_key_pem: str


class AgentCAService:
    """Validates CSRs and issues short-lived ed25519 leaf certs.

    A single instance is shared across the plugin's request handlers.
    The instance loads CA material once at startup; rotation requires
    a plugin reload (Phase 1 simplicity; Phase 2 hot-reload via SIGHUP
    or KMS pull).
    """

    def __init__(self, config: AgentCAConfig) -> None:
        self.config = config
        self._ca_cert: x509.Certificate | None = None
        self._ca_key: ed25519.Ed25519PrivateKey | None = None
        self._root_fingerprint_sha256: str | None = None

    def load(self) -> None:
        """Load CA material from disk. Raises on misconfiguration."""
        cert_bytes = self.config.cert_pem_path.read_bytes()
        key_bytes = self.config.key_pem_path.read_bytes()

        ca_cert = x509.load_pem_x509_certificate(cert_bytes)
        loaded_key = serialization.load_pem_private_key(key_bytes, password=None)
        if not isinstance(loaded_key, ed25519.Ed25519PrivateKey):
            raise RuntimeError(
                "red_agent CA key must be ed25519 (got %r)" % type(loaded_key).__name__
            )

        self._ca_cert = ca_cert
        self._ca_key = loaded_key
        self._root_fingerprint_sha256 = self._compute_fingerprint(ca_cert)

        logger.info(
            "red_agent.ca.loaded",
            extra={
                "subject": ca_cert.subject.rfc4514_string(),
                "not_after": ca_cert.not_valid_after_utc.isoformat(),
                "fingerprint_sha256": self._root_fingerprint_sha256,
            },
        )

    @property
    def root_fingerprint_sha256(self) -> str:
        if self._root_fingerprint_sha256 is None:
            raise RuntimeError("AgentCAService not loaded — call load() first")
        return self._root_fingerprint_sha256

    @property
    def chain_pem(self) -> str:
        if self._ca_cert is None:
            raise RuntimeError("AgentCAService not loaded — call load() first")
        return self._ca_cert.public_bytes(serialization.Encoding.PEM).decode("ascii")

    def issue_from_csr(
        self,
        csr_pem: str,
        *,
        tenant_id: str,
        agent_uuid: UUID,
        validity_days: int | None = None,
    ) -> IssuedCert:
        """Validate a CSR and emit a leaf cert.

        The leaf SAN URI is computed server-side from ``tenant_id`` +
        ``agent_uuid``; the CSR's own SAN extension (if any) is
        ignored. This guarantees PKI is the only source of identity
        truth.
        """
        if self._ca_cert is None or self._ca_key is None:
            raise RuntimeError("AgentCAService not loaded — call load() first")

        csr = self._parse_csr(csr_pem)
        public_key = self._validate_csr(csr)

        now = datetime.now(timezone.utc)
        days = min(
            validity_days
            if validity_days is not None
            else self.config.max_validity_days,
            self.config.max_validity_days,
        )
        not_before = now - timedelta(minutes=5)  # account for clock skew
        not_after = now + timedelta(days=days)

        spiffe_uri = (
            f"spiffe://{self.config.spiffe_trust_domain}"
            f"/tenant/{tenant_id}/agent/{agent_uuid}"
        )

        builder = (
            x509.CertificateBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BaselithCore"),
                        x509.NameAttribute(
                            NameOID.ORGANIZATIONAL_UNIT_NAME, "red-agent"
                        ),
                        x509.NameAttribute(NameOID.COMMON_NAME, str(agent_uuid)),
                    ]
                )
            )
            .issuer_name(self._ca_cert.subject)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.UniformResourceIdentifier(spiffe_uri)]
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(public_key),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self._ca_cert.public_key()  # type: ignore[arg-type]
                ),
                critical=False,
            )
        )

        # ed25519 cert signing — `algorithm` MUST be None per RFC 8410.
        leaf = builder.sign(private_key=self._ca_key, algorithm=None)

        leaf_pem = leaf.public_bytes(serialization.Encoding.PEM).decode("ascii")
        public_key_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        return IssuedCert(
            cert_pem=leaf_pem,
            chain_pem=self.chain_pem,
            serial=format(leaf.serial_number, "x"),
            fingerprint_sha256=self._compute_fingerprint(leaf),
            spiffe_uri=spiffe_uri,
            not_before=not_before,
            not_after=not_after,
            public_key_pem=public_key_pem,
        )

    # --- internals --------------------------------------------------------

    @staticmethod
    def _parse_csr(csr_pem: str) -> x509.CertificateSigningRequest:
        try:
            csr = x509.load_pem_x509_csr(csr_pem.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise CSRValidationError("CSR is not valid PEM") from exc
        if not csr.is_signature_valid:
            raise CSRValidationError("CSR signature is invalid")
        return csr

    @staticmethod
    def _validate_csr(
        csr: x509.CertificateSigningRequest,
    ) -> ed25519.Ed25519PublicKey:
        public_key = csr.public_key()
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise CSRValidationError("CSR public key must be ed25519")

        # Refuse any CSR that pre-declares its own identity material —
        # the issuer is authoritative.
        forbidden_ext_oids = {
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
            ExtensionOID.EXTENDED_KEY_USAGE,
            ExtensionOID.BASIC_CONSTRAINTS,
            ExtensionOID.KEY_USAGE,
        }
        for ext in csr.extensions:
            if ext.oid in forbidden_ext_oids:
                raise CSRValidationError(
                    f"CSR contains forbidden extension {ext.oid.dotted_string}"
                )
        return public_key

    @staticmethod
    def _compute_fingerprint(cert: x509.Certificate) -> str:
        der = cert.public_bytes(serialization.Encoding.DER)
        return hashlib.sha256(der).hexdigest()

    # --- helpers used by tests -------------------------------------------

    @staticmethod
    def fingerprint_of_pem(pem: str) -> str:
        cert = x509.load_pem_x509_certificate(pem.encode("ascii"))
        return AgentCAService._compute_fingerprint(cert)

    def cert_validity_window(self, validity_days: int | None = None) -> timedelta:
        days = min(
            validity_days
            if validity_days is not None
            else self.config.max_validity_days,
            self.config.max_validity_days,
        )
        return timedelta(days=days)

    def __repr__(self) -> str:
        # Never expose the private key. Show only the public-side
        # identifiers a human operator might care about.
        del self  # avoid leaking key fingerprints in tracebacks
        return "AgentCAService(loaded=…)"

    @staticmethod
    def hash_sha256(data: bytes | str) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Test helper: minimal in-memory CA generation. Useful for unit tests
# and dev bootstrap (smallstep CA is the production path). Not exposed
# in __init__.
# ---------------------------------------------------------------------------


def generate_self_signed_ca(
    common_name: str = "BaselithCore Red Agent CA (dev)",
    validity_days: int = 365,
) -> tuple[bytes, bytes]:
    """Return (cert_pem, key_pem) for an ed25519 self-signed CA.

    Intended for local development and tests only — production uses a
    real PKI (smallstep CA in Phase 1, HSM/KMS in Phase 2).
    """
    key = ed25519.Ed25519PrivateKey.generate()
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=validity_days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
        )
    )
    cert = builder.sign(private_key=key, algorithm=None)
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem
