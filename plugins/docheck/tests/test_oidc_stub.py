"""OIDC stub: config gating + claim extraction without external network."""

import pytest

from docheck.core.oidc import get_oidc_config, provision_user_from_claims


def test_disabled_when_no_issuer(monkeypatch) -> None:
    monkeypatch.setenv("DOCHECK_OIDC_ISSUER", "")
    import importlib

    from docheck.core import config as cfg

    importlib.reload(cfg)

    cfg_obj = get_oidc_config()
    assert cfg_obj.enabled is False


def test_enabled_with_issuer(monkeypatch) -> None:
    monkeypatch.setenv("DOCHECK_OIDC_ISSUER", "https://idp.example.local/realms/d")
    import importlib

    from docheck.core import config as cfg

    importlib.reload(cfg)
    from docheck.core import oidc as oidc_mod

    importlib.reload(oidc_mod)

    cfg_obj = oidc_mod.get_oidc_config()
    assert cfg_obj.enabled is True
    assert cfg_obj.issuer == "https://idp.example.local/realms/d"
    assert cfg_obj.jwks_uri.endswith("/.well-known/jwks.json")


async def test_provision_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        await provision_user_from_claims({"sub": "user-1", "tid": "acme"})
