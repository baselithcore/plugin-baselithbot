"""Outbound EHR FHIR push.

POSTs a FHIR R4 ``Bundle`` (built by :func:`triage_report_to_fhir_bundle`)
to an external EHR endpoint. The push is **opt-in**: configuration must
declare a target URL via the ``ehr`` block of the plugin config or via the
``BASELITHMED_EHR_FHIR_URL`` environment variable. When neither is set,
the pusher returns ``PushResult(disabled=True)`` and the caller can skip
the network call.

Authentication is bearer-token-based (FHIR servers like SMART-on-FHIR or
Azure Health Data Services). The token lives in
``BASELITHMED_EHR_FHIR_TOKEN`` and is wrapped in :class:`pydantic.SecretStr`
inside :class:`EhrPushConfig` so it never leaks via :func:`repr` or
Sentry frames.

The pusher is **never** allowed to take down the clinical request path:
every exception is captured and returned as a structured failure inside
:class:`PushResult` so the caller can audit + retry.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr

from .fhir import triage_report_to_fhir_bundle
from .models.clinical import TriageReport

_DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0
_MAX_BODY_BYTES_FOR_LOG: Final[int] = 512


class EhrPushConfig(BaseModel):
    """Configuration block consumed by :class:`EhrPusher`."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    bearer_token: SecretStr | None = None
    timeout_seconds: float = Field(default=_DEFAULT_TIMEOUT_SECONDS, ge=0.5, le=120.0)
    verify_tls: bool = True

    @classmethod
    def from_env(cls) -> "EhrPushConfig | None":
        """Build a config from environment variables, or ``None`` if absent."""
        url = os.getenv("BASELITHMED_EHR_FHIR_URL")
        if not url:
            return None
        token = os.getenv("BASELITHMED_EHR_FHIR_TOKEN")
        timeout = float(
            os.getenv("BASELITHMED_EHR_TIMEOUT", str(_DEFAULT_TIMEOUT_SECONDS))
        )
        verify_tls = os.getenv("BASELITHMED_EHR_VERIFY_TLS", "true").lower() != "false"
        return cls(
            url=HttpUrl(url),
            bearer_token=SecretStr(token) if token else None,
            timeout_seconds=timeout,
            verify_tls=verify_tls,
        )


@dataclass
class PushResult:
    """Outcome of an EHR push attempt — structured, never raises."""

    disabled: bool
    ok: bool
    status_code: int | None = None
    error: str | None = None
    response_preview: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "disabled": self.disabled,
            "ok": self.ok,
            "status_code": self.status_code,
            "error": self.error,
            "response_preview": self.response_preview,
        }


class EhrPusher:
    """Async FHIR Bundle pusher with structured failure handling."""

    def __init__(
        self,
        config: EhrPushConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        # Allow injecting a custom AsyncClient for tests (e.g., MockTransport)
        # without spinning up a real network stack.
        self._injected_client = client

    @property
    def enabled(self) -> bool:
        return self._config is not None

    async def push(self, report: TriageReport) -> PushResult:
        """POST the FHIR Bundle for ``report``. Never raises."""
        if self._config is None:
            return PushResult(disabled=True, ok=False)

        bundle = triage_report_to_fhir_bundle(report)
        headers = {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }
        if self._config.bearer_token is not None:
            headers["Authorization"] = (
                f"Bearer {self._config.bearer_token.get_secret_value()}"
            )

        client_cm: httpx.AsyncClient | None = None
        if self._injected_client is None:
            client_cm = httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_tls,
            )
            client = client_cm
        else:
            client = self._injected_client

        try:
            try:
                response = await client.post(
                    str(self._config.url),
                    json=bundle,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                return PushResult(
                    disabled=False,
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                )

            body_preview: str | None = None
            try:
                body_preview = response.text[:_MAX_BODY_BYTES_FOR_LOG]
            except Exception:  # noqa: BLE001 — preview is best-effort
                body_preview = None

            return PushResult(
                disabled=False,
                ok=200 <= response.status_code < 300,
                status_code=response.status_code,
                error=None
                if 200 <= response.status_code < 300
                else f"HTTP {response.status_code}",
                response_preview=body_preview,
            )
        finally:
            if client_cm is not None:
                await client_cm.aclose()
