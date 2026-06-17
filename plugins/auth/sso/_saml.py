"""SAML 2.0 SP support via python3-saml (onelogin.saml2).

Degrades gracefully when the library (and its xmlsec system dep) is absent:
``SAML_AVAILABLE`` is False and the routes return 503.
"""

from typing import Any, Dict, Optional, Tuple

from core.observability.logging import get_logger

logger = get_logger(__name__)

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    SAML_AVAILABLE = True
except Exception:  # pragma: no cover - optional system dep
    SAML_AVAILABLE = False
    logger.warning("python3-saml not available; SAML SSO disabled.")


def sp_urls(base_url: str, slug: str) -> Dict[str, str]:
    """Service-provider entity/ACS/metadata URLs for a provider."""
    base = base_url.rstrip("/")
    prefix = f"{base}/api/auth/sso/{slug}"
    return {
        "entity_id": f"{prefix}/metadata",
        "acs": f"{prefix}/acs",
        "metadata": f"{prefix}/metadata",
    }


def build_settings(provider: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """Assemble python3-saml settings from provider config."""
    cfg = provider.get("config") or {}
    urls = sp_urls(base_url, provider["slug"])
    return {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": cfg.get("sp_entity_id") or urls["entity_id"],
            "assertionConsumerService": {
                "url": urls["acs"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "NameIDFormat": cfg.get(
                "name_id_format",
                "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            ),
            "x509cert": cfg.get("sp_x509cert", ""),
            "privateKey": provider.get("sp_private_key", ""),
        },
        "idp": {
            "entityId": cfg.get("idp_entity_id", ""),
            "singleSignOnService": {
                "url": cfg.get("idp_sso_url", ""),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": cfg.get("idp_x509cert", ""),
        },
    }


def _prepare_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Shape a FastAPI request into the dict python3-saml expects."""
    return {
        "https": "on" if request_data.get("https") else "off",
        "http_host": request_data.get("host", ""),
        "script_name": request_data.get("path", ""),
        "server_port": request_data.get("port"),
        "get_data": request_data.get("get_data", {}),
        "post_data": request_data.get("post_data", {}),
    }


def _auth(provider: Dict[str, Any], base_url: str, request_data: Dict[str, Any]):
    settings = build_settings(provider, base_url)
    return OneLogin_Saml2_Auth(_prepare_request(request_data), old_settings=settings)


def login_redirect(
    provider: Dict[str, Any],
    base_url: str,
    request_data: Dict[str, Any],
    relay_state: str,
) -> str:
    """Build the IdP SSO redirect URL (SP-initiated AuthnRequest)."""
    if not SAML_AVAILABLE:
        raise RuntimeError("SAML not available")
    auth = _auth(provider, base_url, request_data)
    return auth.login(return_to=relay_state)


def process_acs(
    provider: Dict[str, Any], base_url: str, request_data: Dict[str, Any]
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Process the IdP assertion at the ACS; return (nameid, attributes)."""
    if not SAML_AVAILABLE:
        raise RuntimeError("SAML not available")
    auth = _auth(provider, base_url, request_data)
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        raise RuntimeError(
            f"SAML validation failed: {errors}; {auth.get_last_error_reason()}"
        )
    if not auth.is_authenticated():
        raise RuntimeError("SAML assertion not authenticated")
    return auth.get_nameid(), auth.get_attributes() or {}


def metadata_xml(provider: Dict[str, Any], base_url: str) -> str:
    """Return the SP metadata XML for a provider."""
    if not SAML_AVAILABLE:
        raise RuntimeError("SAML not available")
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    settings = OneLogin_Saml2_Settings(
        build_settings(provider, base_url), sp_validation_only=True
    )
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        raise RuntimeError(f"Invalid SP metadata: {errors}")
    return metadata.decode("utf-8") if isinstance(metadata, bytes) else metadata


def extract_saml_identity(nameid: str, attributes: Dict[str, Any]):
    """Normalize (subject, email, name) from a SAML assertion."""

    def first(*keys):
        for k in keys:
            v = attributes.get(k)
            if v:
                return v[0] if isinstance(v, list) else v
        return None

    email = first(
        "email",
        "Email",
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    ) or (nameid if "@" in (nameid or "") else None)
    name = first(
        "displayName",
        "name",
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    )
    return nameid, email, name
