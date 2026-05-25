"""Authenticated-scan profile model.

Captures the operator's authentication configuration for a target so
DAST/recon scanners (nuclei, zap, schemathesis) can run *as a user*
instead of probing only the unauthenticated surface. Profiles are
target-bound and resolved at scan time the same way credentials are:
the operator stores an opaque ``credentials_ref`` on the target, the
:class:`CredentialBackend` resolves it, and this module renders the
result into the wire format each scanner expects (headers, cookies,
or a login script).

The profile is intentionally minimal — it covers the four flows we
see in the field today and leaves room for richer ones. SAML / SSO
flows that require browser automation are out of scope for this
module; they belong in the headless-browser scanner adapter.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class AuthKind(str, enum.Enum):
    """The shape of credentials a scanner needs to talk to the target."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    COOKIE = "cookie"
    FORM_LOGIN = "form_login"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"


class AuthProfile(BaseModel):
    """Operator-authored authentication configuration for a target.

    Different fields are required for different ``kind`` values; the
    helpers in ``scanners._auth_helpers`` validate the combination
    before any scanner consumes the profile, raising a clear error
    rather than letting an under-specified profile silently produce
    unauthenticated traffic.
    """

    kind: AuthKind = AuthKind.NONE

    username: str | None = Field(
        default=None,
        description="HTTP Basic / form-login username.",
    )
    password: SecretStr | None = Field(
        default=None,
        description="HTTP Basic / form-login password.",
    )
    token: SecretStr | None = Field(
        default=None,
        description=(
            "Bearer token, session cookie value, or pre-issued opaque "
            "auth token. Interpretation depends on ``kind``."
        ),
    )
    cookie_name: str | None = Field(
        default=None,
        description="Cookie name when ``kind=cookie``. Defaults to ``session``.",
    )
    login_url: str | None = Field(
        default=None,
        description=("Form-login endpoint (POST). Required when ``kind=form_login``."),
    )
    login_form_user_field: str = Field(
        default="username",
        description="Form field carrying the username for ``form_login``.",
    )
    login_form_password_field: str = Field(
        default="password",
        description="Form field carrying the password for ``form_login``.",
    )
    login_check_regex: str | None = Field(
        default=None,
        description=(
            "Regex matched against the post-login response body to "
            "confirm a successful authentication. Required by ZAP's "
            "auth context wiring."
        ),
    )
    oauth2_token_url: str | None = Field(
        default=None,
        description="OAuth2 token endpoint when ``kind=oauth2_client_credentials``.",
    )
    oauth2_client_id: str | None = Field(
        default=None,
        description="OAuth2 client_id (public).",
    )
    oauth2_client_secret: SecretStr | None = Field(
        default=None,
        description="OAuth2 client_secret.",
    )
    oauth2_scope: str | None = Field(
        default=None,
        description="Space-separated scope list, e.g. ``api.read api.write``.",
    )
    extra_headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Additional headers appended to every authenticated "
            "request — typically tenant pinning or anti-CSRF tokens "
            "the scanner cannot derive on its own."
        ),
    )

    def to_redacted_dict(self) -> dict[str, Any]:
        """Render the profile for the audit log without leaking secrets.

        Replaces every ``SecretStr`` with ``"<redacted>"`` and keeps
        the structural fields so an operator can confirm later that
        the right kind of profile ran without recovering the secret.
        """

        out = self.model_dump(mode="python", exclude_none=True)
        for k, v in list(out.items()):
            if isinstance(v, SecretStr):
                out[k] = "<redacted>"
        if self.password is not None:
            out["password"] = "<redacted>"
        if self.token is not None:
            out["token"] = "<redacted>"
        if self.oauth2_client_secret is not None:
            out["oauth2_client_secret"] = "<redacted>"
        return out
