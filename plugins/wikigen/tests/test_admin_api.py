"""HTTP integration tests for the admin router.

Covers what unit tests can't:

- the loopback middleware refuses non-local clients with 403
- pydantic validation surfaces 422 for malformed bodies
- conflict (409) when scaffolding a slug that already exists
- a real round-trip through the FastAPI stack — tests assemble the same
  middleware chain that production runs

We isolate filesystem effects to ``tmp_path`` by pointing
``WIKI_ROOT_<NAME>`` env vars at it; the actual ``domains/<name>/`` dir
on disk gets cleaned up in the fixture.

The tests run with the lifespan disabled (no embedder/qdrant warmup)
because admin endpoints don't depend on those services.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from llm_wiki.admin.scaffold import repo_root
from llm_wiki.admin.tenants import reset_registry

REPO = repo_root()


def _isolate_admin_env(monkeypatch: pytest.MonkeyPatch, *, loopback_only: bool) -> None:
    """Common env setup for admin-router fixtures.

    Disable Postgres + AUTH_REQUIRED so the new ``_require_admin_or_first_boot``
    gate (api/admin.py) short-circuits without needing a JWT. Without this,
    a populated dev DB makes ``count_users()`` return >0 and every admin
    request fails 401 even with the loopback gate disabled.
    """
    monkeypatch.setenv("ADMIN_API_ENABLED", "true")
    monkeypatch.setenv("ADMIN_API_LOOPBACK_ONLY", "true" if loopback_only else "false")
    monkeypatch.setenv("APP_DOMAIN", "")
    monkeypatch.setenv("POSTGRES_ENABLED", "false")
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_HOST", raising=False)


@pytest.fixture
def loopback_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient with the loopback middleware disabled.

    TestClient uses ``testclient`` as the request host, which the
    loopback middleware refuses. We toggle the flag *before* importing
    ``main`` so the conditional `add_middleware` path doesn't attach.
    """
    _isolate_admin_env(monkeypatch, loopback_only=False)
    import importlib

    import llm_wiki.config as cfg

    importlib.reload(cfg)
    import main as main_mod

    importlib.reload(main_mod)
    reset_registry()

    with TestClient(main_mod.app) as client:
        yield client


@pytest.fixture
def loopback_only_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient with the loopback middleware *enabled* — expect 403."""
    _isolate_admin_env(monkeypatch, loopback_only=True)
    import importlib

    import llm_wiki.config as cfg

    importlib.reload(cfg)
    import main as main_mod

    importlib.reload(main_mod)
    reset_registry()

    with TestClient(main_mod.app) as client:
        yield client


# --- loopback middleware ---------------------------------------------------


def test_loopback_blocks_non_local(loopback_only_client: TestClient) -> None:
    r = loopback_only_client.get("/api/admin/tenants")
    assert r.status_code == 403
    assert "loopback" in r.json()["detail"].lower()


def test_public_endpoint_unaffected_by_loopback_guard(
    loopback_only_client: TestClient,
) -> None:
    """Branding (public) must keep working even when admin guard rejects testclient."""
    r = loopback_only_client.get("/api/branding")
    assert r.status_code == 200
    body = r.json()
    assert body["setup_mode"] is True


# --- defaults / tenants ----------------------------------------------------


def test_get_scaffold_defaults(loopback_client: TestClient) -> None:
    r = loopback_client.get("/api/admin/scaffold/defaults")
    assert r.status_code == 200
    body = r.json()
    assert "languages" in body
    assert "it" in body["languages"]
    assert isinstance(body["suggested_page_types"], list)


def test_list_tenants_excludes_template(loopback_client: TestClient) -> None:
    r = loopback_client.get("/api/admin/tenants")
    assert r.status_code == 200
    body = r.json()
    names = {t["name"] for t in body["tenants"]}
    assert "_template" not in names
    # at least the seeded packs that ship with the repo
    assert any(n in names for n in {"insurance", "legal", "medical", "technical"})


def test_get_unknown_tenant_returns_404(loopback_client: TestClient) -> None:
    r = loopback_client.get("/api/admin/tenants/does_not_exist")
    assert r.status_code == 404


# --- preview / apply -------------------------------------------------------


@pytest.fixture
def cleanup_smoke_pack() -> Iterator[str]:
    name = "wizard_api_smoke"
    target = REPO / "domains" / name
    if target.exists():
        shutil.rmtree(target)
    yield name
    if target.exists():
        shutil.rmtree(target)


def test_preview_dry_run_does_not_write(
    loopback_client: TestClient, cleanup_smoke_pack: str, tmp_path: Path
) -> None:
    name = cleanup_smoke_pack
    body = {
        "name": name,
        "language": "en",
        "vault_root": str(tmp_path / "vault"),
        "write_env": False,
        "activate": False,
    }
    r = loopback_client.post("/api/admin/scaffold/preview", json=body)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["name"] == name
    assert any(op["kind"] == "copy" for op in plan["operations"])
    # nothing on disk
    assert not (REPO / "domains" / name).exists()
    assert not (tmp_path / "vault").exists()


def test_preview_rejects_reserved_name(loopback_client: TestClient, tmp_path: Path) -> None:
    body = {
        "name": "_template",
        "language": "en",
        "vault_root": str(tmp_path / "v"),
        "write_env": False,
        "activate": False,
    }
    r = loopback_client.post("/api/admin/scaffold/preview", json=body)
    assert r.status_code == 422


def test_preview_rejects_relative_vault(loopback_client: TestClient) -> None:
    body = {
        "name": "fine_slug",
        "language": "en",
        "vault_root": "relative/path",
        "write_env": False,
        "activate": False,
    }
    r = loopback_client.post("/api/admin/scaffold/preview", json=body)
    # zod-style frontend hint AND server-side path safety both apply.
    assert r.status_code in (400, 422)


def test_apply_then_conflict(
    loopback_client: TestClient, cleanup_smoke_pack: str, tmp_path: Path
) -> None:
    name = cleanup_smoke_pack
    body = {
        "name": name,
        "language": "en",
        "vault_root": str(tmp_path / "vault"),
        "write_env": False,
        "activate": False,
    }
    r1 = loopback_client.post("/api/admin/scaffold", json=body)
    assert r1.status_code == 200, r1.text
    result = r1.json()
    assert result["target_pack_dir"].endswith(f"domains/{name}")
    assert (Path(result["vault_path"]) / "wiki").is_dir()

    # second apply without force -> 409
    r2 = loopback_client.post("/api/admin/scaffold", json=body)
    assert r2.status_code == 409


def test_apply_force_overwrites(
    loopback_client: TestClient, cleanup_smoke_pack: str, tmp_path: Path
) -> None:
    name = cleanup_smoke_pack
    body = {
        "name": name,
        "language": "en",
        "vault_root": str(tmp_path / "vault"),
        "write_env": False,
        "activate": False,
    }
    loopback_client.post("/api/admin/scaffold", json=body)
    pack_yaml = REPO / "domains" / name / "pack.yaml"
    pack_yaml.write_text("# tampered\n", encoding="utf-8")

    body_force = {**body, "force": True}
    r = loopback_client.post("/api/admin/scaffold", json=body_force)
    assert r.status_code == 200
    text = pack_yaml.read_text(encoding="utf-8")
    assert "# tampered" not in text


def test_apply_never_echoes_api_key_in_response(
    loopback_client: TestClient, cleanup_smoke_pack: str, tmp_path: Path
) -> None:
    """Provider api_key must be persisted to .env but never returned to the client."""
    name = cleanup_smoke_pack
    body = {
        "name": name,
        "language": "en",
        "vault_root": str(tmp_path / "vault"),
        "write_env": False,  # don't pollute repo .env
        "activate": False,
        "provider": {
            "vendor": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-secret-test-key-1234567890",
        },
    }
    r = loopback_client.post("/api/admin/scaffold", json=body)
    assert r.status_code == 200
    payload = r.text
    assert "sk-secret-test-key-1234567890" not in payload


def test_preview_masks_api_key(
    loopback_client: TestClient, cleanup_smoke_pack: str, tmp_path: Path
) -> None:
    name = cleanup_smoke_pack
    body = {
        "name": name,
        "language": "en",
        "vault_root": str(tmp_path / "vault"),
        "write_env": True,  # so the diff includes provider keys
        "activate": False,
        "provider": {
            "vendor": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-must-not-leak",
        },
    }
    r = loopback_client.post("/api/admin/scaffold/preview", json=body)
    assert r.status_code == 200
    payload = r.text
    assert "sk-must-not-leak" not in payload
    diff = r.json()["env_diff"]
    api_key_entry = next((d for d in diff if d["key"] == "OPENAI_API_KEY"), None)
    assert api_key_entry is not None
    assert api_key_entry["value"] == "***"


# --- branding setup-mode contract -----------------------------------------


def test_branding_returns_setup_mode_when_app_domain_unset(
    loopback_client: TestClient,
) -> None:
    r = loopback_client.get("/api/branding")
    assert r.status_code == 200
    body = r.json()
    assert body["setup_mode"] is True
    assert body["domain"] == ""
    assert body["page_types"] == []


# --- multi-tenant: X-Tenant header routing --------------------------------


def test_branding_resolves_tenant_via_header(
    loopback_client: TestClient,
) -> None:
    """With APP_DOMAIN unset, X-Tenant: <slug> should resolve a known pack."""
    # legal/medical/insurance/technical ship with the repo
    r = loopback_client.get("/api/branding", headers={"X-Tenant": "legal"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["setup_mode"] is False
    assert body["domain"] == "legal"
    assert body["tenant"]["name"] == "legal"
    assert body["tenant"]["is_active"] is False  # APP_DOMAIN unset


def test_branding_unknown_tenant_returns_404(
    loopback_client: TestClient,
) -> None:
    r = loopback_client.get("/api/branding", headers={"X-Tenant": "nonexistent"})
    assert r.status_code == 404


def test_groups_requires_tenant_via_header(
    loopback_client: TestClient,
) -> None:
    """/api/groups returns 503 setup_required when neither APP_DOMAIN nor X-Tenant resolve."""
    r = loopback_client.get("/api/groups")
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["code"] == "setup_required"


def test_groups_resolves_via_header(loopback_client: TestClient) -> None:
    r = loopback_client.get("/api/groups", headers={"X-Tenant": "insurance"})
    assert r.status_code == 200
    body = r.json()
    assert "rules" in body
    assert isinstance(body["rules"], list)


# --- isolation -------------------------------------------------------------


def test_admin_disabled_hides_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ADMIN_API_ENABLED=false, /api/admin/* must 404."""
    monkeypatch.setenv("ADMIN_API_ENABLED", "false")
    monkeypatch.setenv("APP_DOMAIN", "")
    import importlib

    import llm_wiki.config as cfg

    importlib.reload(cfg)
    import main as main_mod

    importlib.reload(main_mod)

    with TestClient(main_mod.app) as client:
        r = client.get("/api/admin/tenants")
        assert r.status_code == 404
        # public still works
        r2 = client.get("/api/branding")
        assert r2.status_code == 200

    # restore for downstream tests
    monkeypatch.setenv("ADMIN_API_ENABLED", "true")
    importlib.reload(cfg)
    importlib.reload(main_mod)


# Reset env after the module finishes so other test modules don't see
# our `APP_DOMAIN=""` override.
@pytest.fixture(autouse=True, scope="module")
def _restore_env() -> Iterator[None]:
    snapshot = {
        k: os.environ.get(k) for k in ("APP_DOMAIN", "ADMIN_API_ENABLED", "ADMIN_API_LOOPBACK_ONLY")
    }
    yield
    for k, v in snapshot.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
