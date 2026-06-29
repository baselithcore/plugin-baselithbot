"""Plugin meta route — localized titles + the regulatory domains it governs.

Exercises the backend i18n layer (``Accept-Language`` → ``en``/``it``) so the
console title and domain labels are server-localized in addition to the SPA's
client-side i18n. Open to any authenticated reader.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from ..i18n import negotiate_locale, translate
from ._guards import read_guard

router = APIRouter(tags=["compliance:meta"])

_DOMAIN_KEYS = (
    "domain.incidents",
    "domain.dora",
    "domain.dsr",
    "domain.thirdparty",
    "domain.transparency",
)


@router.get("/info", dependencies=[Depends(read_guard)])
async def info(request: Request) -> Dict[str, Any]:
    """Return the localized console title/subtitle and governed domains."""
    locale = negotiate_locale(request.headers.get("accept-language"))
    return {
        "locale": locale,
        "title": translate("plugin.title", locale),
        "subtitle": translate("plugin.subtitle", locale),
        "domains": [translate(key, locale) for key in _DOMAIN_KEYS],
    }


__all__ = ["router"]
