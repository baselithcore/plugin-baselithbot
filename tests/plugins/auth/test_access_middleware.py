"""Unit tests for the central plugin-access middleware (pure logic, no DB).

Focus: a browser navigation to a plugin's SPA shell carries only the refresh
cookie — never the localStorage access token that is the app's primary identity.
When that cookie is absent the caller resolves as anonymous, so gating the shell
would lock out a logged-in admin. The middleware fails open ONLY for anonymous
UI-surface loads; an authenticated caller and every API route stay gated. UI
mounts that live UNDER a plugin's API prefix (e.g. red_agent at ``/red-agent/ui``)
are recognised as UI via the plugin's declared ``ui_tabs`` urls.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.auth import AuthRole, AuthUser
from plugins.auth.access_middleware import PluginAccessMiddleware


class FakeRegistry:
    """Minimal registry stub.

    ``api`` maps an API router prefix -> plugin name (match_plugin_route).
    ``static`` maps a plugin name -> static dir (get_all_static_paths).
    ``ui_tabs`` maps a plugin name -> list of declared tab dicts (frontend
    manifest), used to recognise a SPA mounted under the API prefix.
    """

    def __init__(
        self,
        static: dict[str, str] | None = None,
        api: dict[str, str] | None = None,
        ui_tabs: dict[str, list[dict]] | None = None,
    ) -> None:
        self._static = static or {}
        self._api = api or {}
        self._ui_tabs = ui_tabs or {}

    def match_plugin_route(self, path: str) -> str | None:
        for prefix, name in self._api.items():
            if path == prefix or path.startswith(f"{prefix}/"):
                return name
        return None

    def get_all_static_paths(self) -> dict[str, str]:
        return self._static

    def get_frontend_manifest(self) -> dict:
        return {"plugins": {n: {"ui_tabs": t} for n, t in self._ui_tabs.items()}}


def _scope(path: str, registry: FakeRegistry) -> dict:
    app = SimpleNamespace(state=SimpleNamespace(plugin_registry=registry))
    return {"type": "http", "method": "GET", "path": path, "headers": [], "app": app}


async def _noop_receive() -> dict:
    return {"type": "http.request", "body": b""}


def _patch_anon(monkeypatch) -> None:
    async def fake_auth(self, request):  # noqa: ANN001
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})

    monkeypatch.setattr(PluginAccessMiddleware, "_authenticate", fake_auth)


def _patch_user(monkeypatch, roles: set) -> None:
    async def fake_auth(self, request):  # noqa: ANN001
        return AuthUser(user_id="11111111-1111-1111-1111-111111111111", roles=roles)

    monkeypatch.setattr(PluginAccessMiddleware, "_authenticate", fake_auth)


# ---- classification ---------------------------------------------------------


def test_resolve_plugin_classifies_ui_vs_api() -> None:
    reg = FakeRegistry(
        static={"baselithbot": "/srv/baselithbot/static"},
        api={"/api/baselithbot": "baselithbot"},
    )
    assert PluginAccessMiddleware._resolve_plugin("/api/baselithbot/x", reg) == (
        "baselithbot",
        False,
    )
    assert PluginAccessMiddleware._resolve_plugin("/baselithbot", reg) == (
        "baselithbot",
        True,
    )
    assert PluginAccessMiddleware._resolve_plugin(
        "/plugins/baselithbot/static/app.js", reg
    ) == ("baselithbot", True)
    assert PluginAccessMiddleware._resolve_plugin("/docs", reg) == (None, False)


def test_resolve_plugin_spa_under_api_prefix_is_ui() -> None:
    """red_agent: SPA at /red-agent/ui sits under API prefix /red-agent."""
    reg = FakeRegistry(
        api={"/red-agent": "red_agent"},
        ui_tabs={"red_agent": [{"id": "red_agent", "url": "/red-agent/ui"}]},
    )
    # The shell + its assets are UI despite matching the API prefix.
    assert PluginAccessMiddleware._resolve_plugin("/red-agent/ui", reg) == (
        "red_agent",
        True,
    )
    assert PluginAccessMiddleware._resolve_plugin(
        "/red-agent/ui/assets/app.js", reg
    ) == ("red_agent", True)
    # A genuine data route under the same prefix stays API.
    assert PluginAccessMiddleware._resolve_plugin("/red-agent/findings", reg) == (
        "red_agent",
        False,
    )


# ---- enforcement ------------------------------------------------------------


async def test_anonymous_ui_shell_load_fails_open(monkeypatch) -> None:
    """An unauthenticated SPA navigation must load (admin lockout fix)."""
    reg = FakeRegistry(static={"baselithbot": "/srv/x"})
    _patch_anon(monkeypatch)

    def boom():  # rbac must never be consulted on the fail-open path
        raise AssertionError("rbac should not run for anonymous UI loads")

    monkeypatch.setattr("plugins.auth.rbac.service.get_rbac_service", boom)

    mw = PluginAccessMiddleware(app=None)
    assert await mw._is_allowed(_scope("/baselithbot", reg), _noop_receive) is True


async def test_anonymous_red_agent_shell_under_prefix_fails_open(monkeypatch) -> None:
    """red_agent shell (under its API prefix) must load for an anonymous nav."""
    reg = FakeRegistry(
        api={"/red-agent": "red_agent"},
        ui_tabs={"red_agent": [{"url": "/red-agent/ui"}]},
    )
    _patch_anon(monkeypatch)

    def boom():
        raise AssertionError("rbac should not run for an anonymous UI load")

    monkeypatch.setattr("plugins.auth.rbac.service.get_rbac_service", boom)

    mw = PluginAccessMiddleware(app=None)
    assert await mw._is_allowed(_scope("/red-agent/ui", reg), _noop_receive) is True
    asset = _scope("/red-agent/ui/assets/app.js", reg)
    assert await mw._is_allowed(asset, _noop_receive) is True


async def test_authenticated_ui_load_is_always_gated(monkeypatch) -> None:
    """Security: an authenticated caller is NEVER fail-open — the spoofable
    header bypass is gone; UI loads run through plugin_allowed too."""
    reg = FakeRegistry(
        api={"/red-agent": "red_agent"},
        ui_tabs={"red_agent": [{"url": "/red-agent/ui"}]},
    )
    _patch_user(monkeypatch, {AuthRole.USER})

    consulted: list[str] = []

    class StubRBAC:
        def plugin_allowed(self, user_id, roles, plugin, registry) -> bool:  # noqa: ANN001
            consulted.append(plugin)
            return False  # non-admin, restricted plugin

    monkeypatch.setattr(
        "plugins.auth.rbac.service.get_rbac_service", lambda: StubRBAC()
    )

    mw = PluginAccessMiddleware(app=None)
    allowed = await mw._is_allowed(_scope("/red-agent/ui", reg), _noop_receive)
    assert allowed is False
    assert consulted == ["red_agent"]  # gate WAS consulted for the UI load


async def test_anonymous_api_route_stays_gated(monkeypatch) -> None:
    """API routes carry the Bearer token; anonymous stays subject to the gate."""
    reg = FakeRegistry(api={"/api/baselithbot": "baselithbot"})
    _patch_anon(monkeypatch)

    class StubRBAC:
        def plugin_allowed(self, *a, **k) -> bool:
            return False

    monkeypatch.setattr(
        "plugins.auth.rbac.service.get_rbac_service", lambda: StubRBAC()
    )

    mw = PluginAccessMiddleware(app=None)
    allowed = await mw._is_allowed(_scope("/api/baselithbot/stats", reg), _noop_receive)
    assert allowed is False


def test_ungated_plugins_always_pass() -> None:
    reg = FakeRegistry(static={"auth": "/srv/auth"})
    plugin, is_ui = PluginAccessMiddleware._resolve_plugin("/auth", reg)
    assert plugin == "auth" and is_ui is True
    assert plugin in PluginAccessMiddleware._UNGATED_PLUGINS


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
