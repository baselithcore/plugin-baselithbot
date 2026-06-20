"""Unit tests for the central plugin-access middleware (pure logic, no DB).

Focus: a browser navigation to a plugin's SPA shell carries only the refresh
cookie — never the localStorage access token that is the app's primary identity.
When that cookie is absent the caller resolves as anonymous, so gating the shell
would lock out a logged-in admin. The middleware must fail open for anonymous
UI-surface loads while keeping API routes (and authenticated users) gated.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.auth import AuthRole, AuthUser
from plugins.auth.access_middleware import PluginAccessMiddleware


class FakeRegistry:
    """Minimal registry: API prefixes via match_plugin_route, UI via static."""

    def __init__(self, static: dict[str, str], api: dict[str, str]) -> None:
        self._static = static
        self._api = api

    def match_plugin_route(self, path: str) -> str | None:
        for prefix, name in self._api.items():
            if path == prefix or path.startswith(f"{prefix}/"):
                return name
        return None

    def get_all_static_paths(self) -> dict[str, str]:
        return self._static


def _scope(path: str, registry: FakeRegistry) -> dict:
    app = SimpleNamespace(state=SimpleNamespace(plugin_registry=registry))
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "app": app,
    }


async def _noop_receive() -> dict:
    return {"type": "http.request", "body": b""}


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


async def test_anonymous_ui_shell_load_fails_open(monkeypatch) -> None:
    """An unauthenticated SPA navigation must load (admin lockout fix)."""
    reg = FakeRegistry(static={"baselithbot": "/srv/x"}, api={})

    async def fake_auth(self, request):  # noqa: ANN001
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})

    monkeypatch.setattr(PluginAccessMiddleware, "_authenticate", fake_auth)

    def boom():  # rbac must never be consulted on the fail-open path
        raise AssertionError("rbac should not run for anonymous UI loads")

    monkeypatch.setattr("plugins.auth.rbac.service.get_rbac_service", boom)

    mw = PluginAccessMiddleware(app=None)
    assert await mw._is_allowed(_scope("/baselithbot", reg), _noop_receive) is True


async def test_anonymous_api_route_stays_gated(monkeypatch) -> None:
    """API routes carry the Bearer token; anonymous stays subject to the gate."""
    reg = FakeRegistry(static={}, api={"/api/baselithbot": "baselithbot"})

    async def fake_auth(self, request):  # noqa: ANN001
        return AuthUser(user_id="anonymous", roles={AuthRole.ANONYMOUS})

    monkeypatch.setattr(PluginAccessMiddleware, "_authenticate", fake_auth)

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
    reg = FakeRegistry(static={"auth": "/srv/auth"}, api={})
    plugin, is_ui = PluginAccessMiddleware._resolve_plugin("/auth", reg)
    assert plugin == "auth" and is_ui is True
    assert plugin in PluginAccessMiddleware._UNGATED_PLUGINS


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
