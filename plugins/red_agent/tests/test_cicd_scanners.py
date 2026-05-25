"""CI/CD red-team scanner unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from plugins.red_agent.models import Severity, Target, TargetType
from plugins.red_agent.scanners.dependency_confusion import (
    DependencyConfusionScanner,
)
from plugins.red_agent.scanners.gato import GatoScanner
from plugins.red_agent.scanners.workflow_audit import WorkflowAuditScanner


# --- workflow_audit ---


def _wf_target(repo_path: Path) -> Target:
    return Target(
        type=TargetType.REPO,
        value=str(repo_path),
        metadata={"repo_path": str(repo_path)},
    )


def _write_workflow(repo: Path, name: str, body: str) -> None:
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / name).write_text(body, encoding="utf-8")


@pytest.mark.asyncio
async def test_workflow_audit_flags_pwn_request(tmp_path: Path) -> None:
    body = """
on:
  pull_request_target:
    types: [opened, synchronize]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}
      - run: npm test
"""
    _write_workflow(tmp_path, "ci.yml", body)
    sc = WorkflowAuditScanner()

    findings = await sc.run(_wf_target(tmp_path), intensity=None)  # type: ignore[arg-type]

    titles = [f.title for f in findings]
    assert any("pull_request_target" in t for t in titles)
    pwn = [f for f in findings if "pull_request_target" in f.title][0]
    assert pwn.severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_workflow_audit_flags_event_interpolation(tmp_path: Path) -> None:
    body = """
on: pull_request
jobs:
  greet:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Hi ${{ github.event.pull_request.title }}"
"""
    _write_workflow(tmp_path, "greet.yml", body)
    sc = WorkflowAuditScanner()

    findings = await sc.run(_wf_target(tmp_path), intensity=None)  # type: ignore[arg-type]
    assert any("Untrusted github.event" in f.title for f in findings)


@pytest.mark.asyncio
async def test_workflow_audit_flags_unpinned_third_party(tmp_path: Path) -> None:
    body = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: thirdparty/scary-action@main
      - uses: actions/checkout@v4
"""
    _write_workflow(tmp_path, "deps.yml", body)
    sc = WorkflowAuditScanner()

    findings = await sc.run(_wf_target(tmp_path), intensity=None)  # type: ignore[arg-type]
    titles = [f.title for f in findings]
    assert any("thirdparty/scary-action" in t for t in titles)
    # actions/checkout is first-party; must NOT be flagged.
    assert not any("actions/checkout" in t for t in titles)


@pytest.mark.asyncio
async def test_workflow_audit_flags_secret_in_run(tmp_path: Path) -> None:
    body = """
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: 'curl -H "Auth ${{ secrets.MY_TOKEN }}" https://example'
"""
    _write_workflow(tmp_path, "leak.yml", body)
    sc = WorkflowAuditScanner()

    findings = await sc.run(_wf_target(tmp_path), intensity=None)  # type: ignore[arg-type]
    assert any("Secret echoed" in f.title for f in findings)


@pytest.mark.asyncio
async def test_workflow_audit_skips_when_workflows_dir_missing(tmp_path: Path) -> None:
    sc = WorkflowAuditScanner()
    findings = await sc.run(_wf_target(tmp_path), intensity=None)  # type: ignore[arg-type]
    assert findings == []


# --- dependency_confusion ---


def _dc_target(repo: Path) -> Target:
    return Target(
        type=TargetType.REPO,
        value=str(repo),
        metadata={
            "repo_path": str(repo),
            "internal_package_namespaces": ["@acme/", "acme_"],
        },
    )


class _MockTransport(httpx.MockTransport):
    pass


@pytest.mark.asyncio
async def test_dependency_confusion_flags_missing_internal_npm(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "@acme/internal-utils": "1.0.0",
                    "lodash": "4.17.0",
                }
            }
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(
            "/@acme%2Finternal-utils"
        ) or request.url.path.endswith("/@acme/internal-utils"):
            return httpx.Response(404)
        return httpx.Response(200, json={"name": "lodash"})

    sc = DependencyConfusionScanner(
        sandbox=None, request_timeout_seconds=5.0, max_concurrent_requests=4
    )

    real_async_client = httpx.AsyncClient

    def _factory(*_a, **_k):
        return real_async_client(transport=httpx.MockTransport(handler))

    import plugins.red_agent.scanners.dependency_confusion as dc_mod

    original = dc_mod.httpx.AsyncClient
    dc_mod.httpx.AsyncClient = _factory  # type: ignore[assignment]
    try:
        findings = await sc.run(_dc_target(tmp_path), intensity=None)  # type: ignore[arg-type]
    finally:
        dc_mod.httpx.AsyncClient = original  # type: ignore[assignment]

    assert any("@acme/internal-utils" in f.title for f in findings)
    assert all(f.severity == Severity.HIGH for f in findings)


@pytest.mark.asyncio
async def test_dependency_confusion_no_namespaces_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"@acme/x": "1.0.0"}})
    )
    target = Target(
        type=TargetType.REPO,
        value=str(tmp_path),
        metadata={"repo_path": str(tmp_path)},
    )
    sc = DependencyConfusionScanner(sandbox=None)

    findings = await sc.run(target, intensity=None)  # type: ignore[arg-type]
    assert findings == []


def test_dependency_confusion_collects_npm_pkgs(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"a": "1", "@acme/b": "1"},
                "devDependencies": {"c": "1"},
                "peerDependencies": {"d": "1"},
            }
        )
    )
    sc = DependencyConfusionScanner(sandbox=None)
    pkgs = sc._collect_npm(tmp_path)  # type: ignore[attr-defined]
    assert pkgs == ["@acme/b", "a", "c", "d"]


def test_dependency_confusion_collects_pypi_pkgs(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "# comment\nrequests>=2.0\nacme_internal==1.0\n-r other.txt\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["foo>=1.0", "acme_other"]\n'
    )
    sc = DependencyConfusionScanner(sandbox=None)
    pkgs = sc._collect_pypi(tmp_path)  # type: ignore[attr-defined]
    assert "requests" in pkgs
    assert "acme_internal" in pkgs
    assert "foo" in pkgs
    assert "acme_other" in pkgs


# --- gato ---


def test_gato_parses_known_categories() -> None:
    sc = GatoScanner.__new__(GatoScanner)
    sc.name = "gato"
    blob = json.dumps(
        {
            "self_hosted_runner": [
                {
                    "repository": "acme/web",
                    "title": "Org-wide self-hosted runner",
                    "description": "Reachable from forked PRs.",
                    "workflow": ".github/workflows/build.yml",
                }
            ],
            "pwn_request": [
                {
                    "repository": "acme/web",
                    "title": "checkout PR head + run",
                    "workflow": ".github/workflows/ci.yml",
                }
            ],
            "ignored_category": [{"x": 1}],
        }
    )
    target = Target(type=TargetType.REPO, value="acme/web")

    findings = sc._parse(blob, target)  # type: ignore[attr-defined]

    severities = {(f.title.split(":")[0]).strip(): f.severity for f in findings}
    assert severities["Gato self_hosted_runner"] == Severity.HIGH
    assert severities["Gato pwn_request"] == Severity.CRITICAL
    assert all(f.scanner == "gato" for f in findings)
