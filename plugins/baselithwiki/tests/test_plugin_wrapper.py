"""Wrapper-level smoke tests for the BaselithWiki plugin.

These cover the integration seam only — env isolation, sub-app mount, SPA
serving — not the vendored engine's own behaviour (which keeps its upstream
suite). Kept fast: we avoid endpoints that trigger embedder/model warmup.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.plugins.app_setup import apply_plugin_app_middleware
from core.plugins.resource_analyzer import ResourceAnalyzer

_PLUGINS = Path(__file__).resolve().parents[2]
_PLUGIN_DIR = _PLUGINS / "baselithwiki"


def test_discovery_reads_manifest() -> None:
    d = ResourceAnalyzer(_PLUGINS).discover_plugin(_PLUGIN_DIR)
    assert d is not None
    assert d.metadata.name == "baselithwiki"
    assert d.metadata.integrity_sha256


def test_env_isolation_mechanism(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolation pins setup-mode defaults but honours BASELITHWIKI_ overrides.

    Tests the pure ``_apply_env_isolation`` logic directly so it is independent
    of whether a plugin-local ``.env`` is committed.
    """
    from plugins.baselithwiki import _bootstrap

    # Host bleed with NO scoped override → pinned to the safe default.
    monkeypatch.setenv("POSTGRES_ENABLED", "true")
    monkeypatch.delenv("BASELITHWIKI_POSTGRES_ENABLED", raising=False)
    # Scoped override → promoted to the bare key, wins over the default.
    monkeypatch.setenv("BASELITHWIKI_APP_DOMAIN", "insurance")
    _bootstrap._apply_env_isolation()
    assert os.environ["POSTGRES_ENABLED"] == "false"  # host bleed neutralised
    assert os.environ["APP_DOMAIN"] == "insurance"  # scoped override promoted


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    applied = apply_plugin_app_middleware(app, _PLUGINS)
    assert applied >= 1
    return TestClient(app)


def test_engine_mounted_and_live(client: TestClient) -> None:
    r = client.get("/baselithwiki/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_spa_index_served(client: TestClient) -> None:
    r = client.get("/baselithwiki/")
    assert r.status_code == 200
    assert "<!doctype html>" in r.text.lower()


def test_spa_deeplink_fallback(client: TestClient) -> None:
    # Unknown client-side route → SPA shell, not 404.
    r = client.get("/baselithwiki/wiki/some-page")
    assert r.status_code == 200
    assert "<!doctype html>" in r.text.lower()


def test_real_asset_served_with_mime(client: TestClient) -> None:
    r = client.get("/baselithwiki/branding.json")
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")
