"""Tests for the playbook library + HTTP catalogue."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.red_agent import dependencies as deps
from plugins.red_agent.models import ScanIntensity, TargetKind
from plugins.red_agent.playbooks import (
    Playbook,
    PlaybookCatalogue,
    PlaybookNotFoundError,
    default_catalogue,
    load_playbook_files,
)
from plugins.red_agent.routers import playbooks_router


def test_default_catalogue_loads_bundled_playbooks() -> None:
    catalogue = default_catalogue()
    ids = {p.id for p in catalogue.all()}
    assert {"web-baseline", "web-active", "llm-top10-surface"}.issubset(ids)


def test_get_unknown_playbook_raises() -> None:
    catalogue = default_catalogue()
    with pytest.raises(PlaybookNotFoundError):
        catalogue.get("nope")


def test_filter_by_intensity_drops_higher_levels() -> None:
    catalogue = default_catalogue()
    only_passive = catalogue.filter_for(max_intensity=ScanIntensity.PASSIVE)
    assert all(p.intensity == ScanIntensity.PASSIVE for p in only_passive)
    assert "web-active" not in {p.id for p in only_passive}


def test_filter_by_target_kind() -> None:
    catalogue = default_catalogue()
    web_only = catalogue.filter_for(target_kind=TargetKind.WEB)
    assert all(not p.target_kinds or TargetKind.WEB in p.target_kinds for p in web_only)


def test_loader_skips_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "broken.yaml"
    bad.write_text(": not valid yaml :", encoding="utf-8")
    good = tmp_path / "ok.yaml"
    good.write_text(
        """
id: smoke
name: Smoke
intensity: passive
scanners: [nuclei]
""",
        encoding="utf-8",
    )
    rows = load_playbook_files(tmp_path)
    assert [p.id for p in rows] == ["smoke"]


def test_duplicate_ids_rejected() -> None:
    p = Playbook(id="dup", name="x")
    with pytest.raises(ValueError):
        PlaybookCatalogue([p, p])


@pytest.fixture()
def http_client() -> TestClient:
    app = FastAPI()
    app.include_router(playbooks_router)

    async def _allow() -> None:
        return None

    app.dependency_overrides[deps._viewer_dep] = _allow
    return TestClient(app)


def test_http_list(http_client: TestClient) -> None:
    resp = http_client.get("/playbooks")
    assert resp.status_code == 200
    rows = resp.json()
    ids = {p["id"] for p in rows}
    assert "web-baseline" in ids


def test_http_get_returns_404_for_missing(http_client: TestClient) -> None:
    resp = http_client.get("/playbooks/nope")
    assert resp.status_code == 404


def test_http_get_returns_playbook(http_client: TestClient) -> None:
    resp = http_client.get("/playbooks/web-baseline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "web-baseline"
    assert "nuclei" in body["scanners"]
