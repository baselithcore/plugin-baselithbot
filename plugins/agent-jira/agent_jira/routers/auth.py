"""
Auth endpoints per autenticazione built-in.

POST /auth/register  — registrazione utente + creazione tenant
POST /auth/login     — login con email/password, restituisce JWT
GET  /auth/me        — profilo utente corrente (da JWT)

Progettato per essere sostituibile con IdP esterno (Okta, Microsoft, ecc.):
basta disabilitare questi endpoint e configurare la validazione JWT con JWKS.
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from agent_jira.auth_tokens import (
    TokenError,
    issue_access_token,
    issue_refresh_token,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from agent_jira.security import rate_limiter

from agent_jira.db.users import (
    count_users,
    count_users_by_tenant,
    create_user,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    list_users_by_tenant,
    update_last_login,
    update_user,
    verify_password,
)
from agent_jira.config import (
    MULTI_TENANT_ENABLED,
    PLAN_MAX_USERS,
    POSTGRES_ENABLED,
    SECRET_KEY,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_JWT_EXPIRY_HOURS = 24
_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Sprint 11: rate limit auth endpoints (anti-brute-force).
# Sliding window in Redis (o in-process fallback via app.security.rate_limiter).
_RATE_LIMIT_LOGIN_PER_MIN = 10  # per-IP
_RATE_LIMIT_LOGIN_PER_EMAIL = 5  # per-email (più stretto)
_RATE_LIMIT_REGISTER_PER_HOUR = 5  # per-IP
_RATE_LIMIT_REFRESH_PER_MIN = 30  # per-IP

# Cookie name del refresh token (httpOnly + Secure + SameSite=Strict in prod).
_REFRESH_COOKIE_NAME = "agent_jira_refresh"


def _client_ip(request: Request) -> str:
    """IP client real (rispetta X-Forwarded-For se dietro proxy/ingress)."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


def _user_agent(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:500]


def _set_refresh_cookie(
    response: Response,
    token: str,
    expires_at: datetime.datetime,
) -> None:
    """Imposta il refresh token come cookie httpOnly Secure SameSite=Strict.

    In dev (AUTH_COOKIE_SECURE=false) relaxed a non-Secure per localhost HTTP.
    """
    import os

    secure = os.getenv("AUTH_COOKIE_SECURE", "true").strip().lower() != "false"
    samesite = os.getenv("AUTH_COOKIE_SAMESITE", "strict").strip().lower()
    max_age = int(
        (expires_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    )
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path="/auth")


def _audit_safe(action: str, **kwargs) -> None:
    """Audit record tollerante: non blocca il flusso principale."""
    try:
        from agent_jira.audit import record as audit_record

        audit_record(action=action, **kwargs)
    except Exception:
        pass


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    display_name: str = Field(default="")
    organization: str = Field(
        default="",
        description="Nome organizzazione — verrà creato un tenant dedicato",
    )


class LoginRequest(BaseModel):
    email: str
    password: str


def _generate_jwt(
    user_id: str,
    role: str,
    tenant_id: Optional[str] = None,
) -> str:
    """Genera un JWT HS256 con claim user, role e tenant_id."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user_id,
        "uid": user_id,
        "role": role,
        "iat": now,
        "exp": now + datetime.timedelta(hours=_JWT_EXPIRY_HOURS),
    }
    if tenant_id:
        payload["tenant_id"] = tenant_id
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-")[:50] or "org"


@router.post("/register")
def register(req: RegisterRequest, request: Request) -> Dict[str, Any]:
    """Registra un nuovo utente. Se multi-tenancy attiva, crea anche il tenant.

    Sprint 11: rate limited per-IP (anti signup abuse).
    """

    if not POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database non disponibile.",
        )

    ip = _client_ip(request)
    rate_limiter.check(f"register:ip:{ip}", _RATE_LIMIT_REGISTER_PER_HOUR, 3600)

    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email non valida.",
        )

    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un account con questa email esiste già.",
        )

    display_name = req.display_name.strip() or email.split("@")[0]

    if MULTI_TENANT_ENABLED:
        # Modello 1:1 strict — tenant + user creati atomicamente.
        from agent_jira.db.tenants import create_tenant_with_owner, get_tenant_by_slug

        org_name = req.organization.strip() or email.split("@")[0]
        slug = _slugify(org_name)

        base_slug = slug
        counter = 1
        while get_tenant_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        try:
            result = create_tenant_with_owner(
                tenant_name=org_name,
                tenant_slug=slug,
                user_email=email,
                user_password_hash=hash_password(req.password),
                user_display_name=display_name,
            )
        except Exception as exc:
            logger.exception("Registration atomica fallita: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registrazione fallita. Riprova.",
            )
        user = result["user"]
        tenant_id = result["tenant"]["id"]
    else:
        # Single-tenant (legacy / dev)
        user = create_user(
            email=email,
            password=req.password,
            display_name=display_name,
            tenant_id=None,
            role="admin",
        )
        tenant_id = None

    token = _generate_jwt(user["id"], user["role"], tenant_id)

    _audit_safe(
        "auth.register",
        resource_type="user",
        resource_id=user["id"],
        user_id=user["id"],
        tenant_id=tenant_id,
        metadata={"email": email},
        request=request,
    )

    return {
        "status": "ok",
        "token": token,
        "user": user,
    }


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response) -> Dict[str, Any]:
    """Autentica con email/password e restituisce access token + refresh cookie.

    Sprint 11: rate limited per-IP e per-email. Access token breve (15m),
    refresh token opaco (30d) in cookie httpOnly Secure SameSite=Strict.
    """

    if not POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database non disponibile.",
        )

    email = req.email.strip().lower()
    ip = _client_ip(request)

    # Rate limit anti brute-force: per-IP + per-email (più stretto).
    rate_limiter.check(f"login:ip:{ip}", _RATE_LIMIT_LOGIN_PER_MIN, 60)
    rate_limiter.check(f"login:email:{email}", _RATE_LIMIT_LOGIN_PER_EMAIL, 60)

    user_row = get_user_by_email(email)

    if not user_row:
        _audit_safe(
            "auth.login.failed",
            resource_type="user",
            metadata={"email": email, "reason": "unknown_email"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
        )

    if not user_row.get("is_active"):
        _audit_safe(
            "auth.login.failed",
            resource_type="user",
            resource_id=str(user_row["id"]),
            user_id=str(user_row["id"]),
            tenant_id=str(user_row["tenant_id"]) if user_row.get("tenant_id") else None,
            metadata={"reason": "account_disabled"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabilitato.",
        )

    if not verify_password(user_row["password_hash"], req.password):
        _audit_safe(
            "auth.login.failed",
            resource_type="user",
            resource_id=str(user_row["id"]),
            user_id=str(user_row["id"]),
            tenant_id=str(user_row["tenant_id"]) if user_row.get("tenant_id") else None,
            metadata={"reason": "bad_password"},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
        )

    user_id = str(user_row["id"])
    tenant_id = str(user_row["tenant_id"]) if user_row.get("tenant_id") else None
    role = user_row.get("role", "user")

    update_last_login(user_id)

    # Access token breve (15m)
    access_token, access_exp = issue_access_token(
        user_id=user_id, tenant_id=tenant_id or "", role=role
    )

    # Refresh token opaco (30d) in cookie httpOnly
    refresh_token, refresh_exp, _ = issue_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id or "",
        user_agent=_user_agent(request),
        ip_address=ip,
    )
    _set_refresh_cookie(response, refresh_token, refresh_exp)

    user_data = {
        "id": user_id,
        "email": user_row["email"],
        "display_name": user_row.get("display_name", ""),
        "tenant_id": tenant_id,
        "role": role,
    }

    _audit_safe(
        "auth.login.success",
        resource_type="user",
        resource_id=user_id,
        user_id=user_id,
        tenant_id=tenant_id,
        request=request,
    )

    return {
        "status": "ok",
        "token": access_token,  # backward-compat: il frontend esistente usa `token`
        "access_token": access_token,
        "access_token_expires_at": access_exp.isoformat(),
        "user": user_data,
    }


@router.post("/refresh")
def refresh(request: Request, response: Response) -> Dict[str, Any]:
    """
    Ruota il refresh token (dal cookie httpOnly) e restituisce nuovi
    access + refresh. Replay detection: se il token presentato è già
    stato ruotato, tutta la famiglia viene revocata → 401.
    """
    ip = _client_ip(request)
    rate_limiter.check(f"refresh:ip:{ip}", _RATE_LIMIT_REFRESH_PER_MIN, 60)

    presented = request.cookies.get(_REFRESH_COOKIE_NAME)
    if not presented:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token mancante.",
        )

    try:
        rotated = rotate_refresh_token(
            presented,
            user_agent=_user_agent(request),
            ip_address=ip,
        )
    except TokenError as exc:
        _audit_safe(
            "auth.refresh.failed",
            resource_type="refresh_token",
            metadata={"reason": str(exc)},
            request=request,
        )
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessione non valida. Effettua nuovamente il login.",
        )

    _set_refresh_cookie(
        response, rotated["refresh_token"], rotated["refresh_token_expires_at"]
    )

    _audit_safe(
        "auth.refresh.success",
        resource_type="refresh_token",
        user_id=rotated["user_id"],
        tenant_id=rotated["tenant_id"],
        request=request,
    )

    return {
        "status": "ok",
        "access_token": rotated["access_token"],
        "access_token_expires_at": rotated["access_token_expires_at"].isoformat(),
    }


@router.post("/logout")
def logout(request: Request, response: Response) -> Dict[str, Any]:
    """Revoca il refresh della sessione corrente e pulisce il cookie."""
    presented = request.cookies.get(_REFRESH_COOKIE_NAME)
    revoked = False
    if presented:
        revoked = revoke_refresh_token(presented)
    _clear_refresh_cookie(response)

    # Audit: se c'era un access token, logga l'user_id
    try:
        user = _extract_user_from_jwt(request)
        _audit_safe(
            "auth.logout",
            resource_type="user",
            resource_id=str(user.get("id", "")),
            user_id=str(user.get("id", "")),
            tenant_id=str(user.get("tenant_id") or ""),
            metadata={"refresh_revoked": revoked},
            request=request,
        )
    except Exception:
        pass
    return {"status": "ok", "refresh_revoked": revoked}


@router.post("/logout-all")
def logout_all(request: Request, response: Response) -> Dict[str, Any]:
    """Revoca TUTTI i refresh dell'utente (logout everywhere)."""
    user = _extract_user_from_jwt(request)
    user_id = str(user.get("id", ""))
    revoked_count = revoke_all_for_user(user_id)
    _clear_refresh_cookie(response)
    _audit_safe(
        "auth.logout_all",
        resource_type="user",
        resource_id=user_id,
        user_id=user_id,
        tenant_id=str(user.get("tenant_id") or ""),
        metadata={"revoked_count": revoked_count},
        request=request,
    )
    return {"status": "ok", "revoked_count": revoked_count}


def _extract_user_from_jwt(request: Request) -> Dict[str, Any]:
    """Decodifica JWT e restituisce l'utente. Raise HTTPException se non valido."""

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT richiesto.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token scaduto.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido.",
        )

    user_id = payload.get("sub") or payload.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non contiene identificativo utente.",
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato.",
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabilitato.",
        )

    return user


def _require_admin_user(request: Request) -> Dict[str, Any]:
    """Richiede JWT valido con ruolo admin."""

    user = _extract_user_from_jwt(request)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Richiesto ruolo admin.",
        )
    return user


def _purge_tenant_data(tenant_id: str) -> Dict[str, Any]:
    """
    Rimuove tutti i dati del tenant dai sistemi non-DB:
      - Qdrant: delete by payload filter tenant_id
      - FalkorDB: DETACH DELETE WHERE n.tenant_id = $tid (per ogni label)
      - Filesystem: rmtree documents/<tenant_id>
      - Redis cache: del chiavi con prefisso contenente il tenant_id

    Postgres (tenant, users, feedback) viene gestito dalla FK ON DELETE CASCADE
    tramite delete_tenant().

    Non solleva: errori loggati ma non bloccano il flusso GDPR.
    """
    report: Dict[str, Any] = {
        "qdrant": {"deleted": False, "error": None},
        "falkordb": {"deleted": False, "error": None},
        "filesystem": {"deleted": False, "error": None},
        "redis": {"deleted_keys": 0, "error": None},
    }

    # Qdrant: delete points by tenant_id filter
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        from agent_jira.config import COLLECTION, QDRANT

        QDRANT.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
                ]
            ),
        )
        report["qdrant"]["deleted"] = True
    except Exception as exc:
        report["qdrant"]["error"] = str(exc)
        logger.warning("Qdrant purge tenant %s failed: %s", tenant_id, exc)

    # FalkorDB: DETACH DELETE WHERE tenant_id = tid
    try:
        from agent_jira.graphdb import graph_db

        if graph_db.is_enabled():
            graph_db.query(
                "MATCH (n) WHERE n.tenant_id = $tid DETACH DELETE n",
                {"tid": tenant_id},
            )
            report["falkordb"]["deleted"] = True
    except Exception as exc:
        report["falkordb"]["error"] = str(exc)
        logger.warning("FalkorDB purge tenant %s failed: %s", tenant_id, exc)

    # Filesystem: documents/<tenant_id>/
    try:
        import shutil
        from pathlib import Path

        from agent_jira.config import DOCUMENTS_ROOT

        tenant_dir = Path(DOCUMENTS_ROOT) / tenant_id
        if tenant_dir.exists() and tenant_dir.is_dir():
            shutil.rmtree(tenant_dir)
            report["filesystem"]["deleted"] = True
    except Exception as exc:
        report["filesystem"]["error"] = str(exc)
        logger.warning("Filesystem purge tenant %s failed: %s", tenant_id, exc)

    # Redis cache: chiavi con prefisso tenant
    try:
        from agent_jira.cache import create_redis_client
        from agent_jira.config import CACHE_BACKEND, CACHE_REDIS_PREFIX, CACHE_REDIS_URL

        if CACHE_BACKEND == "redis":
            client = create_redis_client(CACHE_REDIS_URL)
            pattern = f"{CACHE_REDIS_PREFIX}*:t:{tenant_id}:*"
            keys_deleted = 0
            for key in client.scan_iter(match=pattern):
                client.delete(key)
                keys_deleted += 1
            report["redis"]["deleted_keys"] = keys_deleted
    except Exception as exc:
        report["redis"]["error"] = str(exc)
        logger.warning("Redis purge tenant %s failed: %s", tenant_id, exc)

    return report


class DeleteWorkspaceRequest(BaseModel):
    confirm_email: str = Field(
        ...,
        description="Per conferma, l'email dell'account. Deve corrispondere al JWT.",
    )


@router.delete("/me/workspace")
async def delete_my_workspace(
    request: Request, req: DeleteWorkspaceRequest
) -> Dict[str, Any]:
    """
    Cancella definitivamente il workspace (tenant) dell'utente autenticato.

    Operazione irreversibile. Rimuove: account utente, tenant, documenti,
    embedding vettoriali, nodi/archi del grafo, cache per-tenant.

    Richiede conferma tramite email per prevenire esecuzioni accidentali
    (CSRF-like / click errato). L'email deve corrispondere a quella del JWT.

    Implementa GDPR Art. 17 (Right to erasure).
    """
    user = _extract_user_from_jwt(request)
    user_email = user.get("email", "").strip().lower()
    confirm_email = req.confirm_email.strip().lower()

    if not confirm_email or confirm_email != user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conferma email non corrisponde all'account corrente.",
        )

    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nessun workspace associato all'account.",
        )

    logger.warning(
        "Self-service workspace DELETE: user=%s tenant=%s",
        user.get("id"),
        tenant_id,
    )

    # Audit log PRIMA della cancellazione (dopo il cascade il tenant_id
    # non esisterebbe più come FK).
    try:
        from agent_jira.audit import record as audit_record

        audit_record(
            action="workspace.delete",
            resource_type="tenant",
            resource_id=tenant_id,
            tenant_id=tenant_id,
            user_id=str(user.get("id", "")),
            metadata={"email": user_email},
            request=request,
        )
    except Exception:
        pass

    # Purge non-DB prima, così se fallisce la DELETE DB l'utente può riprovare
    # e il cleanup è idempotente.
    purge_report = _purge_tenant_data(tenant_id)

    # Delete tenant (cascade: users, feedback)
    from agent_jira.db.tenants import delete_tenant

    deleted = delete_tenant(tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cancellazione workspace fallita.",
        )

    return {
        "status": "ok",
        "message": "Workspace eliminato definitivamente.",
        "tenant_id": tenant_id,
        "purged": purge_report,
    }


@router.get("/me/usage")
async def me_usage(request: Request) -> Dict[str, Any]:
    """
    Dashboard di consumo del tenant corrente: quota usate vs limiti di piano.

    Aggiorna anche le Gauge Prometheus per-tenant come side-effect.
    """
    user = _extract_user_from_jwt(request)
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        return {"status": "ok", "usage": None, "note": "single-tenant mode"}

    from agent_jira.db.tenants import get_tenant_by_id
    from agent_jira.quotas import quota_tracker

    tenant = get_tenant_by_id(tenant_id)
    plan = (tenant or {}).get("plan", "free")
    summary = quota_tracker.get_usage_summary(tenant_id=tenant_id, plan=plan)
    return {"status": "ok", **summary}


@router.get("/me")
async def me(request: Request) -> Dict[str, Any]:
    """Restituisce il profilo dell'utente corrente dal JWT + info quota tenant."""
    user = _extract_user_from_jwt(request)
    tenant_id = user.get("tenant_id")
    max_users = _get_tenant_max_users(tenant_id) if tenant_id else 1
    return {"status": "ok", "user": user, "max_users": max_users}


# === User management (admin del tenant) ===


class InviteUserRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    display_name: str = Field(default="")
    role: str = Field(default="user")


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


def _get_tenant_max_users(tenant_id: str) -> int:
    """Restituisce il numero massimo di utenti per il piano del tenant."""
    try:
        from agent_jira.db.tenants import get_tenant_by_id

        tenant = get_tenant_by_id(tenant_id)
        plan = (tenant or {}).get("plan", "free")
        return PLAN_MAX_USERS.get(plan, 1)
    except Exception:
        return 1


@router.get("/users")
async def list_users(request: Request) -> Dict[str, Any]:
    """Lista utenti del tenant corrente. Richiede admin."""

    admin = _require_admin_user(request)
    tenant_id = admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Nessun tenant associato.")

    users = list_users_by_tenant(tenant_id)
    max_users = _get_tenant_max_users(tenant_id)

    return {"status": "ok", "users": users, "max_users": max_users}


@router.post("/users")
async def invite_user(request: Request, req: InviteUserRequest) -> Dict[str, Any]:
    """Crea un nuovo utente nel tenant corrente. Richiede admin + quota disponibile."""

    admin = _require_admin_user(request)
    tenant_id = admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Nessun tenant associato.")

    # Quota check
    max_users = _get_tenant_max_users(tenant_id)
    current_count = count_users_by_tenant(tenant_id)
    if current_count >= max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Il piano attuale ammette al massimo {max_users} "
            f"utent{'e' if max_users == 1 else 'i'}. "
            "Effettua l'upgrade per aggiungere membri al team.",
        )

    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Email non valida.")

    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=409, detail="Un utente con questa email esiste già."
        )

    if req.role not in ("user", "admin"):
        raise HTTPException(
            status_code=422, detail="Ruolo non valido. Usa 'user' o 'admin'."
        )

    user = create_user(
        email=email,
        password=req.password,
        display_name=req.display_name.strip() or email.split("@")[0],
        tenant_id=tenant_id,
        role=req.role,
    )

    return {"status": "ok", "user": user}


@router.put("/users/{user_id}")
async def edit_user(
    request: Request, user_id: str, req: UpdateUserRequest
) -> Dict[str, Any]:
    """Modifica un utente del tenant corrente. Richiede admin."""

    admin = _require_admin_user(request)
    tenant_id = admin.get("tenant_id")

    target = get_user_by_id(user_id)
    if not target or target.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Utente non trovato nel tenant.")

    if req.is_active is False and user_id == admin["id"]:
        raise HTTPException(
            status_code=400, detail="Non puoi disattivare il tuo account."
        )

    if req.role is not None and req.role not in ("user", "admin"):
        raise HTTPException(status_code=422, detail="Ruolo non valido.")

    updated = update_user(
        user_id,
        display_name=req.display_name,
        role=req.role,
        is_active=req.is_active,
    )

    return {"status": "ok", "user": updated}


# ──────────────────────────────────────────────────────────────────────────
# First-boot superuser bootstrap (mirrors wikigen / dbview / docheck)
# ──────────────────────────────────────────────────────────────────────────

# Loopback IP set per anti-LAN-attacker. ::ffff:127.0.0.1 copre il mapping
# IPv4 dentro un socket dual-stack (uvicorn dietro `--host 0.0.0.0` su Linux).
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}
_BOOTSTRAP_MIN_PASSWORD = 12


def _is_loopback(request: Request) -> bool:
    """True se il client viene da localhost.

    NB: ignora X-Forwarded-For di proposito — durante il bootstrap
    iniziale non ci si può fidare di header proxiati: deve essere
    proprio il browser sulla stessa macchina dell'engine.
    """
    host = request.client.host if request.client else None
    if host is None:
        return False
    return host in _LOOPBACK_HOSTS


class BootstrapStatusResponse(BaseModel):
    needs_bootstrap: bool
    users_count: int


class BootstrapRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=_BOOTSTRAP_MIN_PASSWORD, max_length=512)
    display_name: str = Field(default="")
    organization: str = Field(
        default="",
        description="Nome organizzazione — verrà creato un tenant dedicato",
    )


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
def bootstrap_status() -> BootstrapStatusResponse:
    """Probe public side-effect-free. fail-open su errore DB (legacy
    login resta raggiungibile invece di trap-and-die)."""
    if not POSTGRES_ENABLED:
        return BootstrapStatusResponse(needs_bootstrap=False, users_count=0)
    try:
        n = count_users()
    except Exception:
        return BootstrapStatusResponse(needs_bootstrap=False, users_count=0)
    return BootstrapStatusResponse(needs_bootstrap=(n == 0), users_count=n)


@router.post("/bootstrap")
def bootstrap_admin(
    req: BootstrapRequest, request: Request, response: Response
) -> Dict[str, Any]:
    """Crea il primo superuser. Gate stack:

    - 503 se Postgres non disponibile,
    - 403 se ``count_users > 0`` (idempotent — admin gestiti via UI utenti),
    - 403 se la richiesta non arriva da loopback (anti-LAN-attacker).

    Sul successo apre subito una sessione (access token + refresh cookie)
    riusando lo stesso shape di POST /auth/login, quindi il frontend salta
    direttamente alla UI autenticata.
    """
    if not POSTGRES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database non disponibile.",
        )

    ip = _client_ip(request)
    rate_limiter.check(f"bootstrap:ip:{ip}", 3, 3600)

    try:
        n = count_users()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"DB irraggiungibile: {exc}",
        )

    if n > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap già completato.",
        )

    if not _is_loopback(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Il bootstrap è consentito solo da loopback.",
        )

    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email non valida.",
        )

    display_name = req.display_name.strip() or email.split("@")[0]
    org_name = req.organization.strip() or display_name

    if MULTI_TENANT_ENABLED:
        from agent_jira.db.tenants import create_tenant_with_owner, get_tenant_by_slug

        slug = _slugify(org_name)
        base_slug = slug
        counter = 1
        while get_tenant_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        try:
            result = create_tenant_with_owner(
                tenant_name=org_name,
                tenant_slug=slug,
                user_email=email,
                user_password_hash=hash_password(req.password),
                user_display_name=display_name,
            )
        except Exception as exc:
            logger.exception("Bootstrap atomic creation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Creazione superuser fallita. Riprova.",
            )
        user = result["user"]
        tenant_id = result["tenant"]["id"]
    else:
        user = create_user(
            email=email,
            password=req.password,
            display_name=display_name,
            tenant_id=None,
            role="admin",
        )
        tenant_id = None

    user_id = str(user["id"])
    update_last_login(user_id)

    # Access token breve (15m) + refresh cookie httpOnly (stesso shape di /login).
    access_token, access_exp = issue_access_token(
        user_id=user_id, tenant_id=tenant_id or "", role="admin"
    )
    refresh_token, refresh_exp, _ = issue_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id or "",
        user_agent=_user_agent(request),
        ip_address=ip,
    )
    _set_refresh_cookie(response, refresh_token, refresh_exp)

    _audit_safe(
        "auth.bootstrap",
        resource_type="user",
        resource_id=user_id,
        user_id=user_id,
        tenant_id=tenant_id,
        metadata={"email": email, "source": "web"},
        request=request,
    )

    user_data = {
        "id": user_id,
        "email": user["email"],
        "display_name": user.get("display_name", display_name),
        "tenant_id": tenant_id,
        "role": "admin",
    }
    return {
        "status": "ok",
        "token": access_token,  # backward-compat con frontend esistente
        "access_token": access_token,
        "access_token_expires_at": access_exp.isoformat(),
        "user": user_data,
    }
