"""Credential resolver — pluggable backend for identity scanners.

Identity tools (BloodHound, Certipy, ROADrecon) need a
username/password (or refresh token) to talk to a domain controller
or the Microsoft Graph API. We never accept those creds in the scan
request body; instead, the request carries a ``credentials_ref``
opaque key, and this resolver maps it to a concrete credential at
run-time.

Two backends ship today:

- ``metadata`` — reads from ``Target.metadata['credentials']``. For
  development / single-tenant labs only.
- ``vault`` — reads from a HashiCorp Vault KV v2 mount. The
  ``credentials_ref`` is the relative path under
  ``identity_vault_kv_mount``. Tokens come from ``VAULT_TOKEN`` /
  the configured AppRole.

Adding a new backend = subclass :class:`CredentialBackend`, register
via :func:`register_backend`, and bump
``RED_AGENT_IDENTITY_CREDENTIALS_BACKEND``. The resolver itself never
logs credential values; callers should pass the returned object to
the sandbox runner immediately and let it fall out of scope.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import SecretStr

from core.observability.logging import get_logger
from plugins.red_agent.models import Target

logger = get_logger(__name__)


@dataclass(frozen=True)
class IdentityCredential:
    """Minimal credential shape consumed by identity scanners.

    ``username`` and ``password`` cover AD / LDAP. ``refresh_token`` is
    populated for Entra ID flows where ROADrecon uses an OAuth refresh
    token instead of a password. Implementations leave irrelevant
    fields as ``None``.
    """

    username: str | None
    password: SecretStr | None
    domain: str | None = None
    refresh_token: SecretStr | None = None


class CredentialResolutionError(RuntimeError):
    """Raised when the resolver cannot fulfil a credentials_ref."""


class CredentialBackend(ABC):
    """Strategy interface for credential lookups."""

    name: str = ""

    @abstractmethod
    async def resolve(
        self, *, target: Target, credentials_ref: str | None
    ) -> IdentityCredential:
        """Return an :class:`IdentityCredential` or raise.

        ``credentials_ref`` is opaque to the resolver caller (orch /
        scanner); each backend defines its own grammar.
        """


class MetadataBackend(CredentialBackend):
    """Reads ``Target.metadata['credentials']`` directly. Dev-only."""

    name = "metadata"

    async def resolve(
        self, *, target: Target, credentials_ref: str | None
    ) -> IdentityCredential:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        creds = meta.get("credentials")
        if not isinstance(creds, dict):
            raise CredentialResolutionError(
                "metadata backend requires Target.metadata.credentials"
            )
        password = creds.get("password")
        refresh_token = creds.get("refresh_token")
        return IdentityCredential(
            username=creds.get("username"),
            password=SecretStr(password) if isinstance(password, str) else None,
            domain=creds.get("domain"),
            refresh_token=(
                SecretStr(refresh_token) if isinstance(refresh_token, str) else None
            ),
        )


class VaultBackend(CredentialBackend):
    """HashiCorp Vault KV v2 backend.

    ``credentials_ref`` is the relative path under
    ``identity_vault_kv_mount`` (e.g. ``red-agent/engagements/acme/ad``).
    The backend pulls the latest version, expects the secret payload
    to carry ``username``, ``password`` and optionally ``domain`` /
    ``refresh_token`` keys.

    Authentication: a token is read from the ``VAULT_TOKEN``
    environment variable. Production deployments are expected to seed
    the token via AppRole or Kubernetes auth and refresh it
    out-of-process; the backend itself is intentionally
    auth-agnostic.

    Failures convert to :class:`CredentialResolutionError` so the
    caller can surface a structured 4xx instead of leaking Vault
    internals.
    """

    name = "vault"

    def __init__(
        self,
        *,
        addr: str,
        kv_mount: str,
        token: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._addr = addr.rstrip("/")
        self._mount = kv_mount.strip("/")
        self._token = token
        self._timeout = timeout_seconds

    async def resolve(
        self, *, target: Target, credentials_ref: str | None
    ) -> IdentityCredential:
        if not credentials_ref:
            raise CredentialResolutionError("vault backend requires credentials_ref")

        # Lazy import so the dependency is only required when the
        # backend is actually selected.
        import httpx

        path = credentials_ref.strip("/")
        url = f"{self._addr}/v1/{self._mount}/data/{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers={"X-Vault-Token": self._token})
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            logger.warning(
                "red_agent.vault.fetch_failed",
                extra={"path": path, "err": str(exc)},
            )
            raise CredentialResolutionError(f"vault read failed for {path}") from exc

        data = (
            payload.get("data", {}).get("data") if isinstance(payload, dict) else None
        )
        if not isinstance(data, dict):
            raise CredentialResolutionError(
                f"vault payload missing data.data for {path}"
            )

        username = data.get("username")
        password = data.get("password")
        refresh_token = data.get("refresh_token")
        if not isinstance(username, str):
            username = None
        return IdentityCredential(
            username=username,
            password=SecretStr(password) if isinstance(password, str) else None,
            domain=data.get("domain") if isinstance(data.get("domain"), str) else None,
            refresh_token=(
                SecretStr(refresh_token) if isinstance(refresh_token, str) else None
            ),
        )


_REGISTRY: dict[str, type[CredentialBackend]] = {
    "metadata": MetadataBackend,
    "vault": VaultBackend,  # type: ignore[type-abstract]
}


def register_backend(name: str, cls: type[CredentialBackend]) -> None:
    """Install a backend implementation under ``name``."""

    _REGISTRY[name] = cls


def get_backend(
    name: str,
    *,
    vault_addr: str | None = None,
    vault_kv_mount: str = "kv",
    vault_token: str | None = None,
    vault_timeout_seconds: float = 10.0,
) -> CredentialBackend:
    """Construct a backend instance from ``name``.

    The metadata backend takes no parameters. The vault backend
    requires ``vault_addr`` + ``vault_token`` and falls back to
    metadata with a warning when either is missing — the caller is
    responsible for surfacing the misconfiguration to the operator.
    Custom backends registered via :func:`register_backend` must
    accept zero positional arguments; if they need configuration
    they should be installed as already-bound instances.
    """

    key = (name or "metadata").lower()
    if key == "vault":
        if not vault_addr or not vault_token:
            logger.warning(
                "red_agent.credentials.vault_misconfigured",
                extra={"have_addr": bool(vault_addr), "have_token": bool(vault_token)},
            )
            return MetadataBackend()
        return VaultBackend(
            addr=vault_addr,
            kv_mount=vault_kv_mount,
            token=vault_token,
            timeout_seconds=vault_timeout_seconds,
        )
    cls = _REGISTRY.get(key, MetadataBackend)
    return cls()


async def resolve_credentials(
    *,
    backend_name: str,
    target: Target,
    credentials_ref: str | None,
    vault_addr: str | None = None,
    vault_kv_mount: str = "kv",
    vault_token: str | None = None,
) -> IdentityCredential:
    """Convenience wrapper that picks a backend and runs ``resolve``.

    The wrapper exists so scanners take a single function dependency
    rather than juggling backend objects themselves.
    """

    backend = get_backend(
        backend_name,
        vault_addr=vault_addr,
        vault_kv_mount=vault_kv_mount,
        vault_token=vault_token,
    )
    return await backend.resolve(target=target, credentials_ref=credentials_ref)
