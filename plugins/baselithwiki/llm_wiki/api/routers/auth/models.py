"""Request/response pydantic models for auth endpoints."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=120)
    tenant_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=12, max_length=128)


class BootstrapRequest(BaseModel):
    """Body per :func:`bootstrap_superuser`. Allineato a
    :class:`RegisterRequest` ma è una rotta distinta: questa crea il
    *primo* superuser (ruolo system + tenant enterprise), non un user
    standard tenant-isolato.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=120)
    tenant_slug: str = Field(default="", max_length=50)


class BootstrapStatusResponse(BaseModel):
    needs_bootstrap: bool
    users_count: int


class InviteCreateRequest(BaseModel):
    """Body per :func:`create_invitation_endpoint` (admin-only).

    ``role_slug`` opzionale: NULL = ruolo dedotto al consumo
    (primo invite di sistema → superuser; altrimenti = user). Per
    forzare un ruolo specifico passare lo slug system (es. ``moderator``).
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role_slug: str | None = Field(default=None, max_length=50)
    tenant_slug: str | None = Field(default=None, max_length=50)
    display_name: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=500)
    ttl_hours: int | None = Field(default=None, ge=1, le=168)


class InviteCreateResponse(BaseModel):
    id: str
    email: str
    accept_url: str
    expires_at: str


class InvitePeekResponse(BaseModel):
    """Risposta al GET ``/auth/invite/{token}`` — usato dal frontend
    AcceptInvite per pre-popolare email + verificare validità prima
    del POST. Niente PII di altri utenti, solo info inerenti al token."""

    valid: bool
    email: str | None = None
    role_slug: str | None = None
    display_name: str | None = None
    expires_at: str | None = None
    reason: str | None = None  # "expired" | "used" | "unknown"


class InviteAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=32, max_length=200)
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=120)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime.datetime
    user_id: str
    tenant_id: str
    role: str
    email: str


class GroupRef(BaseModel):
    """Mini-summary di un gruppo (per ``UserMeResponse.groups``)."""

    id: str
    slug: str
    name: str
    is_system: bool = False


class UserMeResponse(BaseModel):
    id: str
    email: str
    display_name: str
    tenant_id: str
    role: str
    is_active: bool
    created_at: str | None = None
    last_login_at: str | None = None
    # RBAC (007_rbac). Vuoti = nessun ruolo/permesso assegnato (dev/setup).
    roles: list[str] = []
    permissions: list[str] = []
    domains: list[str] = []
    # Group membership (015). Read-only — gating sempre via `permissions`.
    groups: list[GroupRef] = []
    # Force password change baseline (009): True ⇒ il frontend deve
    # forzare il redirect a /auth/password prima di mostrare l'app.
    must_change_password: bool = False
