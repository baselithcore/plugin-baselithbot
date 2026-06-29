"""End-to-end tests for the compliance console API.

Mounts the plugin router on a bare FastAPI app and overrides the auth guards so
the per-domain routes can be exercised against the in-memory core services. An
autouse fixture resets the global compliance singletons so tests are isolated.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth.types import AuthRole, AuthUser
from plugins.compliance.router import _guards, build_compliance_router


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset the core compliance singletons between tests for isolation."""
    import core.incidents.dora_service as dora
    import core.incidents.service as incidents
    import core.privacy.service as privacy
    import core.thirdparty.register as register
    import core.transparency.service as transparency

    incidents._service = None
    dora._service = None
    register._register = None
    transparency._service = None
    privacy._service = None
    yield


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(build_compliance_router(), prefix="/api/compliance")
    app.dependency_overrides[_guards.read_guard] = lambda: None
    app.dependency_overrides[_guards.admin_principal] = lambda: AuthUser(
        user_id="tester", roles={AuthRole.ADMIN}
    )
    return TestClient(app)


def test_overview_aggregates_domains(client: TestClient) -> None:
    client.post(
        "/api/compliance/incidents", json={"title": "Breach", "severity": "high"}
    )
    ov = client.get("/api/compliance/overview").json()
    assert set(ov.keys()) >= {
        "nis2",
        "dora",
        "dsr",
        "thirdparty",
        "transparency",
        "deadlines",
    }
    assert ov["nis2"]["open"] >= 1
    # A significant incident has three upcoming NIS2 milestones surfaced.
    assert len(ov["deadlines"]) >= 1
    assert ov["deadlines"][0]["regime"] in {"nis2", "dora"}


def test_info_localized(client: TestClient) -> None:
    en = client.get("/api/compliance/info").json()
    assert en["locale"] == "en"
    assert en["title"] == "Compliance"
    it = client.get(
        "/api/compliance/info", headers={"Accept-Language": "it-IT,it;q=0.9"}
    ).json()
    assert it["locale"] == "it"
    assert it["title"] == "Conformità"
    assert len(it["domains"]) == 5


def test_nis2_incident_lifecycle(client: TestClient) -> None:
    created = client.post(
        "/api/compliance/incidents",
        json={"title": "Breach", "severity": "high", "affected_subjects": 3},
    )
    assert created.status_code == 201
    incident_id = created.json()["id"]
    assert len(created.json()["milestones"]) == 3  # significant ⇒ reporting clock

    listing = client.get("/api/compliance/incidents").json()
    assert any(i["id"] == incident_id for i in listing["incidents"])

    advanced = client.post(f"/api/compliance/incidents/{incident_id}/early-warning")
    assert advanced.status_code == 200
    ew = next(m for m in advanced.json()["milestones"] if m["kind"] == "early_warning")
    assert ew["submitted"] is True


def test_nis2_unknown_milestone_is_400(client: TestClient) -> None:
    created = client.post("/api/compliance/incidents", json={"title": "X"})
    incident_id = created.json()["id"]
    bad = client.post(f"/api/compliance/incidents/{incident_id}/nope")
    assert bad.status_code == 400


def test_dora_classify_makes_it_major(client: TestClient) -> None:
    created = client.post("/api/compliance/dora", json={"title": "ICT outage"})
    incident_id = created.json()["id"]
    assert created.json()["is_major"] is False
    assert created.json()["milestones"] == []  # no clock until classified major

    classified = client.post(
        f"/api/compliance/dora/{incident_id}/classify",
        json={
            "critical_services_affected": True,
            "clients_affected": True,
            "service_downtime": True,
        },
    )
    assert classified.status_code == 200
    assert classified.json()["is_major"] is True
    assert len(classified.json()["milestones"]) == 3


def test_dsr_export_unknown_subject_is_empty(client: TestClient) -> None:
    providers = client.get("/api/compliance/dsr/providers")
    assert providers.status_code == 200
    out = client.post("/api/compliance/dsr/export", json={"subject_id": "ghost"})
    assert out.status_code == 200
    assert out.json()["subject_id"] == "ghost"


def test_thirdparty_register_and_validate(client: TestClient) -> None:
    prov = client.post(
        "/api/compliance/thirdparty/providers",
        json={"name": "CloudCo", "country": "IE", "is_critical_designated": True},
    )
    assert prov.status_code == 201
    provider_id = prov.json()["id"]

    listing = client.get("/api/compliance/thirdparty/providers").json()
    assert any(p["id"] == provider_id for p in listing["providers"])

    # Arrangement referencing an unknown provider is rejected (422).
    bad = client.post(
        "/api/compliance/thirdparty/arrangements",
        json={"reference_number": "C-1", "provider_id": "unknown"},
    )
    assert bad.status_code == 422

    conc = client.get("/api/compliance/thirdparty/concentration").json()
    assert conc["providers"] == 1


def test_transparency_status_and_mark(client: TestClient) -> None:
    status = client.get("/api/compliance/transparency/status")
    assert status.status_code == 200
    assert "enabled" in status.json()

    marked = client.post(
        "/api/compliance/transparency/mark",
        json={"content": "hello world", "model": "claude-opus-4-8"},
    )
    assert marked.status_code == 201
    assert "tag" in marked.json() and "header" in marked.json()
