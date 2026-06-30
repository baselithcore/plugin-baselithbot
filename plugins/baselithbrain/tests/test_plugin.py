"""Smoke tests for the BaselithBrain backend over a temp vault."""

from __future__ import annotations

import importlib
import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    vault = tempfile.mkdtemp(prefix="bb_pytest_")
    monkeypatch.setenv("BASELITHBRAIN_VAULT_ROOT", vault)
    # Reset cached singletons so the temp vault is picked up per test session.
    os.environ["VAULT_ROOT"] = vault
    cfg = importlib.import_module("plugins.baselithbrain.config")
    cfg.get_settings.cache_clear()
    idx = importlib.import_module("plugins.baselithbrain.backend.index_state")
    idx.get_index.cache_clear()
    app_mod = importlib.import_module("plugins.baselithbrain.backend.app")
    with TestClient(app_mod.app) as c:
        yield c


def test_seed_and_health(client: TestClient) -> None:
    assert client.get("/healthz").json()["ready"] is True
    notes = client.get("/api/notes").json()
    assert len(notes) == 6


def test_wikilinks_and_backlinks(client: TestClient) -> None:
    notes = client.get("/api/notes").json()
    zett = next(n for n in notes if n["title"] == "Zettelkasten")
    full = client.get(f"/api/notes/{zett['id']}").json()
    assert "welcome-to-baselithbrain" in full["backlinks"]


def test_search_and_graph(client: TestClient) -> None:
    hits = client.get("/api/search", params={"q": "atomic"}).json()
    assert any(h["id"] == "atomic-notes" for h in hits)
    graph = client.get("/api/graph").json()
    assert graph["nodes"] and graph["edges"]


def test_crud_roundtrip(client: TestClient) -> None:
    created = client.post(
        "/api/notes",
        json={"title": "Pytest Note", "body": "links [[Zettelkasten]]", "tags": ["x"]},
    ).json()
    assert created["links"] == ["zettelkasten"]
    assert client.delete(f"/api/notes/{created['id']}").json()["deleted"] is True


def test_hierarchy_tree_and_move(client: TestClient) -> None:
    parent = client.post("/api/notes", json={"title": "Parent"}).json()
    child = client.post(
        "/api/notes", json={"title": "Child", "parent": parent["id"]}
    ).json()
    assert child["parent"] == parent["id"]

    tree = client.get("/api/notes/tree").json()
    node = next(n for n in tree if n["id"] == parent["id"])
    assert any(c["id"] == child["id"] for c in node["children"])

    # Re-parent to root, then verify the cycle guard rejects a self/descendant move.
    moved = client.post(f"/api/notes/{child['id']}/move", json={"parent": None}).json()
    assert moved["parent"] is None
    cyclic = client.post(
        f"/api/notes/{parent['id']}/move", json={"parent": parent["id"]}
    ).json()
    assert cyclic["parent"] is None


def test_delete_reparents_children(client: TestClient) -> None:
    root = client.post("/api/notes", json={"title": "Root"}).json()
    mid = client.post("/api/notes", json={"title": "Mid", "parent": root["id"]}).json()
    leaf = client.post("/api/notes", json={"title": "Leaf", "parent": mid["id"]}).json()
    client.delete(f"/api/notes/{mid['id']}")
    # Leaf's parent should climb to Root (mid's parent), never orphan.
    assert client.get(f"/api/notes/{leaf['id']}").json()["parent"] == root["id"]


def test_workspaces_default_and_scoping(client: TestClient) -> None:
    # Seed notes all belong to the default workspace, present on first run.
    workspaces = client.get("/api/workspaces").json()
    default = next(w for w in workspaces if w["id"] == "default")
    assert default["note_count"] == 6

    ws = client.post("/api/workspaces", json={"name": "Work Projects"}).json()
    assert ws["id"] == "work-projects"

    note = client.post(
        "/api/notes", json={"title": "Sprint", "workspace": ws["id"]}
    ).json()
    assert note["workspace"] == ws["id"]

    # Listing/tree are scoped to the requested workspace.
    scoped = client.get("/api/notes", params={"workspace": ws["id"]}).json()
    assert [n["id"] for n in scoped] == [note["id"]]
    assert len(client.get("/api/notes", params={"workspace": "default"}).json()) == 6


def test_workspace_child_inherits_and_assign_moves_subtree(client: TestClient) -> None:
    ws = client.post("/api/workspaces", json={"name": "WS"}).json()
    parent = client.post("/api/notes", json={"title": "P"}).json()
    child = client.post(
        "/api/notes", json={"title": "C", "parent": parent["id"]}
    ).json()
    assert child["workspace"] == "default"  # inherits parent's workspace

    # Assigning a parent carries its whole subtree along.
    client.post(f"/api/notes/{parent['id']}/workspace", json={"workspace": ws["id"]})
    assert client.get(f"/api/notes/{child['id']}").json()["workspace"] == ws["id"]


def test_delete_workspace_reassigns_notes(client: TestClient) -> None:
    ws = client.post("/api/workspaces", json={"name": "Temp"}).json()
    note = client.post(
        "/api/notes", json={"title": "Doomed", "workspace": ws["id"]}
    ).json()
    res = client.delete(f"/api/workspaces/{ws['id']}").json()
    assert res == {"deleted": True, "reassigned": 1}
    assert client.get(f"/api/notes/{note['id']}").json()["workspace"] == "default"
    # The default workspace is undeletable.
    assert client.delete("/api/workspaces/default").status_code == 400


def test_asset_upload_roundtrip(client: TestClient) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    res = client.post("/api/assets", files={"file": ("pic.png", png, "image/png")})
    assert res.status_code == 201
    body = res.json()
    assert body["path"].startswith("_assets/") and body["path"].endswith(".png")
    fetched = client.get(f"/api/assets/{body['name']}")
    assert fetched.status_code == 200 and fetched.content == png
    assert fetched.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in fetched.headers["content-security-policy"]
    # Reject non-image types.
    bad = client.post("/api/assets", files={"file": ("x.txt", b"hi", "text/plain")})
    assert bad.status_code == 415


def test_conversation_crud_and_memory(client: TestClient) -> None:
    # A thread can be opened, renamed, cleared and deleted via the API.
    conv = client.post(
        "/api/ai/conversations", json={"title": "Chat one", "workspace": "default"}
    ).json()
    assert conv["title"] == "Chat one" and conv["messages"] == []

    listed = client.get("/api/ai/conversations", params={"workspace": "default"}).json()
    assert any(c["id"] == conv["id"] for c in listed)

    renamed = client.patch(
        f"/api/ai/conversations/{conv['id']}", json={"title": "Renamed"}
    ).json()
    assert renamed["title"] == "Renamed"

    # Threads are workspace-scoped: a thread in another workspace is filtered out.
    other = client.get(
        "/api/ai/conversations", params={"workspace": "elsewhere"}
    ).json()
    assert all(c["id"] != conv["id"] for c in other)

    assert client.delete(f"/api/ai/conversations/{conv['id']}").json() == {
        "deleted": True
    }
    assert client.get(f"/api/ai/conversations/{conv['id']}").status_code == 404


def test_chat_opens_thread_even_without_llm(client: TestClient) -> None:
    # No LLM is configured in tests, but the chat endpoint must still open a
    # thread (the ``meta`` event) and stream a friendly ``error`` event — never
    # hang. The first turn auto-titles the thread from the question.
    res = client.post(
        "/api/ai/chat", json={"question": "What links my notes about cats?"}
    )
    assert res.status_code == 200
    events = [json.loads(line) for line in res.text.splitlines() if line.strip()]
    kinds = [e["type"] for e in events]
    assert kinds[0] == "meta"
    meta = events[0]
    assert meta["conversation_id"] and meta["title"].startswith("What links")

    # The opened thread is now persisted and discoverable.
    listed = client.get("/api/ai/conversations").json()
    assert any(c["id"] == meta["conversation_id"] for c in listed)


def test_tags_index(client: TestClient) -> None:
    client.post("/api/notes", json={"title": "Tagged", "tags": ["alpha", "beta"]})
    tags = client.get("/api/tags").json()
    names = {t["tag"]: t["count"] for t in tags}
    assert names.get("alpha", 0) >= 1 and names.get("beta", 0) >= 1


def test_daily_note_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/daily", json={}).json()
    assert first["id"].startswith("daily-")
    before = len(client.get("/api/notes").json())
    second = client.post("/api/daily", json={}).json()
    assert second["id"] == first["id"]
    # Opening the same day twice must not create a second note.
    assert len(client.get("/api/notes").json()) == before


def test_templates_crud_and_daily_seed(client: TestClient) -> None:
    tpl = client.post(
        "/api/templates", json={"name": "Journal", "body": "## {{date}}\n\n- "}
    ).json()
    assert tpl["id"] == "journal"
    listed = client.get("/api/templates").json()
    assert any(t["id"] == "journal" for t in listed)

    note = client.post(
        "/api/daily", json={"date": "2024-01-02", "template": tpl["id"]}
    ).json()
    assert "2024-01-02" in note["body"]  # {{date}} expanded
    assert client.delete(f"/api/templates/{tpl['id']}").json() == {"deleted": True}


def test_version_history_and_restore(client: TestClient) -> None:
    note = client.post("/api/notes", json={"title": "Versioned", "body": "v1"}).json()
    client.put(f"/api/notes/{note['id']}", json={"body": "v2"})  # snapshots v1
    history = client.get(f"/api/notes/{note['id']}/history").json()
    assert len(history) >= 1
    version = history[0]["version"]
    assert (
        "v1" in client.get(f"/api/notes/{note['id']}/history/{version}").json()["body"]
    )
    restored = client.post(f"/api/notes/{note['id']}/history/{version}/restore").json()
    assert restored["body"].strip() == "v1"


def test_trash_restore_and_purge(client: TestClient) -> None:
    note = client.post("/api/notes", json={"title": "Disposable"}).json()
    assert client.delete(f"/api/notes/{note['id']}").json()["deleted"] is True
    # Gone from the live list, present in the trash.
    assert all(n["id"] != note["id"] for n in client.get("/api/notes").json())
    trash = client.get("/api/trash").json()
    assert any(t["id"] == note["id"] for t in trash)

    restored = client.post(f"/api/trash/{note['id']}/restore").json()
    assert any(n["id"] == restored["id"] for n in client.get("/api/notes").json())

    # Re-delete then purge for good.
    client.delete(f"/api/notes/{restored['id']}")
    assert client.delete(f"/api/trash/{restored['id']}").json() == {"purged": True}
    assert all(t["id"] != restored["id"] for t in client.get("/api/trash").json())


def test_export_note_and_vault(client: TestClient) -> None:
    note = client.post(
        "/api/notes", json={"title": "Exportable", "body": "hello"}
    ).json()
    one = client.get(f"/api/notes/{note['id']}/export")
    assert one.status_code == 200
    assert "attachment" in one.headers["content-disposition"]
    assert "hello" in one.text

    bundle = client.get("/api/export")
    assert bundle.status_code == 200
    assert bundle.headers["content-type"].startswith("application/zip")
    assert bundle.content[:2] == b"PK"  # zip magic


def test_backlinks_with_context(client: TestClient) -> None:
    # The seed "Welcome" note links to Zettelkasten with surrounding prose.
    ctx = client.get("/api/notes/zettelkasten/backlinks").json()
    assert any(b["id"] == "welcome-to-baselithbrain" for b in ctx)
    src = next(b for b in ctx if b["id"] == "welcome-to-baselithbrain")
    assert isinstance(src["snippet"], str)


def test_asset_rejects_svg_xss(client: TestClient) -> None:
    # SVG can carry <script> → rejected by magic-byte sniff even if the client
    # lies about Content-Type (the XSS-via-SVG vector must not be storable).
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert (
        client.post(
            "/api/assets", files={"file": ("x.svg", svg, "image/svg+xml")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/assets", files={"file": ("x.png", svg, "image/png")}
        ).status_code
        == 415
    )
