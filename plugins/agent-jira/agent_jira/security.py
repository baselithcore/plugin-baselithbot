from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from typing import Iterable, Optional, Set

import jwt
from fastapi import HTTPException, Request, status
from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware

from agent_jira.config import (
    ADMIN_PASS,
    ADMIN_PASS_HASHED,
    API_KEYS_ADMIN,
    API_KEYS_JOB,
    API_KEYS_USER,
    AUTH_REQUIRED,
    CONTENT_SECURITY_POLICY,
    ENABLE_HSTS,
    RATE_LIMIT_ADMIN_PER_MINUTE,
    RATE_LIMIT_JOB_PER_MINUTE,
    RATE_LIMIT_USER_PER_MINUTE,
    RATE_LIMIT_WINDOW_SECONDS,
    SECRET_KEY,
    SECURITY_HEADERS_ENABLED,
)

SECURITY_EVENTS = Counter(
    "agent_jira_security_events_total",
    "Eventi di sicurezza (auth/rate-limit)",
    ["reason"],
)


class RateLimiter:
    """
    Rate limiter con supporto in-process (default) e Redis distribuito.
    In modalità Redis usa sliding window con sorted sets (ZRANGEBYSCORE).
    """

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            try:
                from agent_jira.config import CACHE_BACKEND, CACHE_REDIS_URL

                if CACHE_BACKEND == "redis" and CACHE_REDIS_URL:
                    from agent_jira.cache import create_redis_client

                    self._redis = create_redis_client(CACHE_REDIS_URL)
            except Exception:
                self._redis = None
        return self._redis

    def check(self, identifier: str, limit: Optional[int], window_seconds: int) -> None:
        if not limit or limit <= 0:
            return

        redis = self._get_redis()
        if redis:
            self._check_redis(redis, identifier, limit, window_seconds)
        else:
            self._check_local(identifier, limit, window_seconds)

    def _check_local(self, identifier: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._buckets[identifier]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            SECURITY_EVENTS.labels(reason="rate_limited").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit superato, riprova tra pochi secondi.",
            )
        bucket.append(now)

    def _check_redis(
        self, redis, identifier: str, limit: int, window_seconds: int
    ) -> None:
        import time as _time

        key = f"ratelimit:{identifier}"
        now = _time.time()
        window_start = now - window_seconds

        pipe = redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 1)
        results = pipe.execute()

        current_count = results[1]
        if current_count >= limit:
            SECURITY_EVENTS.labels(reason="rate_limited").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit superato, riprova tra pochi secondi.",
            )


rate_limiter = RateLimiter()


def _extract_credentials(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Restituisce (api_key, bearer_token).
    - api_key da header X-API-Key
    - bearer_token da Authorization: Bearer <token>
    """

    header_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    api_key = header_key.strip() if header_key else None

    authorization = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()
    return api_key, bearer


def _decode_jwt(token: str) -> tuple[Optional[str], Optional[str]]:
    """
    Decodifica JWT HS256 firmato con SECRET_KEY.
    Ritorna (role, subject) o (None, None) se non valido.
    """

    if not SECRET_KEY:
        return None, None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None, None
    role = payload.get("role")
    subject = payload.get("sub") or payload.get("uid")
    return role, subject


def _decode_jwt_tenant(token: str) -> Optional[str]:
    """Estrae il claim tenant_id dal JWT, se presente."""

    if not SECRET_KEY:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    tenant_id = payload.get("tenant_id")
    return str(tenant_id) if tenant_id else None


def _resolve_role(api_key: str | None) -> Optional[str]:
    if not api_key:
        return None
    if api_key in API_KEYS_ADMIN:
        return "admin"
    if api_key in API_KEYS_JOB:
        return "job"
    if api_key in API_KEYS_USER:
        return "user"
    return None


def _first_matching_role(candidate: str | None, allowed: Set[str]) -> Optional[str]:
    role = _resolve_role(candidate)
    if role and role in allowed:
        return role
    return None


def _rate_limit_identifier(request: Request, api_key: str | None, role: str) -> str:
    if api_key:
        return f"{role}:{api_key}"
    client_host = request.client.host if request.client else "unknown"
    return f"{role}:{client_host}"


def _enforce_auth(
    request: Request,
    allowed_roles: Iterable[str],
    *,
    limit_per_minute: Optional[int],
    allow_anonymous_when_auth_disabled: bool = True,
) -> str:
    allowed_set = set(allowed_roles)
    has_keys_for_allowed = any(
        [
            ("admin" in allowed_set and API_KEYS_ADMIN),
            ("job" in allowed_set and API_KEYS_JOB),
            ("user" in allowed_set and API_KEYS_USER),
        ]
    )
    api_key, bearer = _extract_credentials(request)

    # Preferisci JWT se presente e valido
    jwt_role, jwt_subject = (None, None)
    if bearer:
        jwt_role, jwt_subject = _decode_jwt(bearer)
        if jwt_role:
            if jwt_role not in allowed_set:
                SECURITY_EVENTS.labels(reason="forbidden").inc()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permesso negato per questo ruolo.",
                )
            # Propaga tenant_id dal JWT al request state per il TenantMiddleware
            jwt_tenant = _decode_jwt_tenant(bearer)
            if jwt_tenant:
                request.state.tenant_id = jwt_tenant
            identifier = f"{jwt_role}:jwt:{jwt_subject or 'token'}"
            rate_limiter.check(identifier, limit_per_minute, RATE_LIMIT_WINDOW_SECONDS)
            return jwt_role

    resolved_role = _resolve_role(api_key)
    if resolved_role and resolved_role not in allowed_set:
        SECURITY_EVENTS.labels(reason="forbidden").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permesso negato per questo ruolo.",
        )

    role = _first_matching_role(api_key, allowed_set)
    if role is None:
        if (
            not AUTH_REQUIRED
            and allow_anonymous_when_auth_disabled
            and not has_keys_for_allowed
        ):
            return "anonymous"
        SECURITY_EVENTS.labels(reason="unauthorized").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    identifier = _rate_limit_identifier(request, api_key, role)
    rate_limiter.check(identifier, limit_per_minute, RATE_LIMIT_WINDOW_SECONDS)
    return role


async def require_user(request: Request) -> str:
    """
    Dipendenza per rotte utente (chat/console).
    Admin/job sono accettati come superset.
    """

    return _enforce_auth(
        request,
        allowed_roles={"user", "admin", "job"},
        limit_per_minute=RATE_LIMIT_USER_PER_MINUTE,
        allow_anonymous_when_auth_disabled=True,
    )


async def require_admin(request: Request) -> str:
    """Dipendenza per rotte amministrative/metriche."""

    return _enforce_auth(
        request,
        allowed_roles={"admin"},
        limit_per_minute=RATE_LIMIT_ADMIN_PER_MINUTE,
        allow_anonymous_when_auth_disabled=False,
    )


async def require_admin_or_job(request: Request) -> str:
    """Dipendenza per rotte di indicizzazione/automazione (admin + job)."""

    limit = RATE_LIMIT_JOB_PER_MINUTE or RATE_LIMIT_ADMIN_PER_MINUTE
    return _enforce_auth(
        request,
        allowed_roles={"admin", "job"},
        limit_per_minute=limit,
        allow_anonymous_when_auth_disabled=False,
    )


def _verify_pbkdf2_sha256(encoded: str, candidate: str) -> bool:
    """
    Confronta hash PBKDF2-SHA256 nel formato:
    pbkdf2_sha256$<iterazioni>$<salt_hex>$<hash_hex>
    """

    try:
        scheme, iter_str, salt_hex, hash_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(hash_hex)
    except Exception:
        return False

    derived = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(derived, digest)


def verify_admin_password(candidate: str) -> bool:
    """
    Verifica password admin:
    - se ADMIN_PASS_HASHED è valorizzato (PBKDF2-SHA256) usa confronto con costante,
    - altrimenti fallback su ADMIN_PASS in chiaro per retrocompatibilità.
    """

    if ADMIN_PASS_HASHED:
        return _verify_pbkdf2_sha256(ADMIN_PASS_HASHED, candidate)
    return secrets.compare_digest(candidate, ADMIN_PASS)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Aggiunge header di sicurezza alle risposte HTTP.
    CSP e HSTS sono configurabili via .env (CONTENT_SECURITY_POLICY, ENABLE_HSTS).
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not SECURITY_HEADERS_ENABLED:
            return response

        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "same-origin")
        headers.setdefault("X-XSS-Protection", "1; mode=block")
        if CONTENT_SECURITY_POLICY:
            headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if ENABLE_HSTS:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response
