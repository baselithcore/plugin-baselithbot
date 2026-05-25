"""Auth router: register / login / refresh / logout / me / password.

Adattato (snellito) da ``agent-jira/app/routers/auth.py``.

Cookie strategy
===============

Refresh token in cookie ``llm_wiki_refresh`` httpOnly + Secure +
SameSite=Strict (dev fallback non-Secure se ``AUTH_COOKIE_SECURE=false``).
Access token in response body — il frontend lo tiene SOLO in memoria
(MAI localStorage: XSS-resistente).

Rate limit
==========

- ``/login``: 10/min per-IP + 5/min per-email (anti-brute force).
- ``/register``: 5/ora per-IP (anti-mass-signup).
- ``/refresh``: 30/min per-IP.

Replay detection: refresh token rotato → vecchio invalido. Riuso del
vecchio = revoca FAMILY → forza re-login totale.

Registration
============

Default ``AUTH_PUBLIC_REGISTRATION=false``: solo admin può creare nuovi
account (POST con bearer admin). True = self-service signup pubblico.
Ogni register crea tenant + user in 1 transazione (1:1 invariant).

Modular layout (>500 LOC budget):
- :mod:`.helpers`     — cookie/rate/ip helpers + constants
- :mod:`.models`      — pydantic request/response
- :mod:`.bootstrap`   — first-superuser endpoints
- :mod:`.invitations` — invite create/peek/accept
- :mod:`.sessions`    — register/login/refresh/logout/me/password
"""

from __future__ import annotations

from fastapi import APIRouter

from llm_wiki.api.routers.auth.bootstrap import router as _bootstrap_router
from llm_wiki.api.routers.auth.invitations import router as _invitations_router
from llm_wiki.api.routers.auth.sessions import router as _sessions_router

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(_bootstrap_router)
router.include_router(_invitations_router)
router.include_router(_sessions_router)

__all__ = ["router"]
