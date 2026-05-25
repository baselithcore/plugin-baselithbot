"""AutoRemediationService tests via mocked GitHub Contents API."""

from __future__ import annotations

import base64
import json
from typing import Any
from uuid import uuid4

import httpx
import pytest

from plugins.red_agent.integrations.autopr import (
    AutoRemediationService,
    UnsupportedRemediation,
    _plan_remediation,
    _rewrite_requirement,
)
from plugins.red_agent.models import Finding, Severity


def _sca_finding(**kw: Any) -> Finding:
    base: dict[str, Any] = {
        "scanner": "trivy",
        "title": "demo",
        "description": "vuln",
        "severity": Severity.HIGH,
        "target": "repo://demo",
        "cve": "CVE-2024-1234",
        "evidence": {
            "package": "requests",
            "installed_version": "2.30.0",
            "osv_fixed_in": ["2.32.0"],
            "repo_owner": "acme",
            "repo_name": "demo",
            "default_branch": "main",
        },
    }
    base.update(kw)
    return Finding(**base)


# --- _rewrite_requirement -------------------------------------------


def test_rewrite_requirement_replaces_pinned_version() -> None:
    src = "requests==2.30.0\nfastapi==0.110.0\n"
    out = _rewrite_requirement(src, package="requests", fixed_version="2.32.0")
    assert out is not None
    assert "requests==2.32.0" in out
    assert "fastapi==0.110.0" in out


def test_rewrite_requirement_replaces_range_specifier() -> None:
    src = "requests>=2.30.0\n"
    out = _rewrite_requirement(src, package="requests", fixed_version="2.32.0")
    assert out is not None
    assert "requests==2.32.0" in out


def test_rewrite_requirement_returns_none_when_package_absent() -> None:
    src = "fastapi==0.110.0\n"
    out = _rewrite_requirement(src, package="requests", fixed_version="2.32.0")
    assert out is None


# --- _plan_remediation ----------------------------------------------


def test_plan_unsupported_when_osv_fixed_in_missing() -> None:
    f = _sca_finding(evidence={"package": "requests", "installed_version": "2.30.0"})
    with pytest.raises(UnsupportedRemediation):
        _plan_remediation(f)


def test_plan_unsupported_when_repo_meta_missing() -> None:
    f = _sca_finding(
        evidence={
            "package": "requests",
            "installed_version": "2.30.0",
            "osv_fixed_in": ["2.32.0"],
        }
    )
    with pytest.raises(UnsupportedRemediation):
        _plan_remediation(f)


def test_plan_unsupported_when_no_concrete_fixed_version() -> None:
    f = _sca_finding()
    f.evidence["osv_fixed_in"] = [None]  # type: ignore[list-item]
    with pytest.raises(UnsupportedRemediation):
        _plan_remediation(f)


def test_plan_picks_first_fixed_version() -> None:
    f = _sca_finding()
    f.evidence["osv_fixed_in"] = ["2.32.0", "2.32.1"]
    plan = _plan_remediation(f)
    assert plan.fixed_version == "2.32.0"
    assert plan.owner == "acme"
    assert plan.repo == "demo"
    assert plan.base_branch == "main"


# --- AutoRemediationService end-to-end via MockTransport -----------


def _gh_handler(routes: dict[tuple[str, str], httpx.Response]) -> Any:
    """Map (METHOD, URL-prefix) → response."""

    def handler(request: httpx.Request) -> httpx.Response:
        for (method, prefix), resp in routes.items():
            if request.method == method and str(request.url).startswith(prefix):
                return resp
        return httpx.Response(404, json={"error": "no route", "url": str(request.url)})

    return httpx.MockTransport(handler)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


@pytest.mark.asyncio
async def test_disabled_when_no_token() -> None:
    svc = AutoRemediationService(enabled=True, github_token=None)
    assert svc.enabled is False
    result = await svc.remediate(_sca_finding())
    assert result.success is False
    assert result.error == "auto_pr_disabled"


@pytest.mark.asyncio
async def test_full_round_trip_opens_pr() -> None:
    requirements = "requests==2.30.0\nfastapi==0.110.0\n"
    routes = {
        (
            "GET",
            "https://api.github.com/repos/acme/demo/git/ref/heads/main",
        ): httpx.Response(200, json={"object": {"sha": "abc123"}}),
        (
            "GET",
            "https://api.github.com/repos/acme/demo/contents/requirements.txt",
        ): httpx.Response(200, json={"sha": "filesha", "content": _b64(requirements)}),
        ("POST", "https://api.github.com/repos/acme/demo/git/refs"): httpx.Response(
            201, json={"ref": "refs/heads/red-agent/x"}
        ),
        (
            "PUT",
            "https://api.github.com/repos/acme/demo/contents/requirements.txt",
        ): httpx.Response(201, json={"commit": {"sha": "newsha"}}),
        ("POST", "https://api.github.com/repos/acme/demo/pulls"): httpx.Response(
            201,
            json={"html_url": "https://github.com/acme/demo/pull/42"},
        ),
    }
    client = httpx.AsyncClient(transport=_gh_handler(routes))
    svc = AutoRemediationService(enabled=True, github_token="ghp_xxx", client=client)
    f = _sca_finding(id=uuid4())
    result = await svc.remediate(f)
    assert result.success is True
    assert result.pr_url == "https://github.com/acme/demo/pull/42"
    assert result.fixed_version == "2.32.0"
    assert result.branch is not None
    await client.aclose()


@pytest.mark.asyncio
async def test_branch_creation_failure_aborts_pr() -> None:
    requirements = "requests==2.30.0\n"
    routes = {
        (
            "GET",
            "https://api.github.com/repos/acme/demo/git/ref/heads/main",
        ): httpx.Response(200, json={"object": {"sha": "abc"}}),
        (
            "GET",
            "https://api.github.com/repos/acme/demo/contents/requirements.txt",
        ): httpx.Response(200, json={"sha": "fs", "content": _b64(requirements)}),
        ("POST", "https://api.github.com/repos/acme/demo/git/refs"): httpx.Response(
            422, json={"message": "branch exists"}
        ),
    }
    client = httpx.AsyncClient(transport=_gh_handler(routes))
    svc = AutoRemediationService(enabled=True, github_token="ghp_xxx", client=client)
    result = await svc.remediate(_sca_finding())
    assert result.success is False
    assert result.error is not None and "create_branch_failed" in result.error
    await client.aclose()


@pytest.mark.asyncio
async def test_package_not_in_requirements_aborts() -> None:
    requirements = "fastapi==0.110.0\n"  # no `requests`
    routes = {
        (
            "GET",
            "https://api.github.com/repos/acme/demo/git/ref/heads/main",
        ): httpx.Response(200, json={"object": {"sha": "abc"}}),
        (
            "GET",
            "https://api.github.com/repos/acme/demo/contents/requirements.txt",
        ): httpx.Response(200, json={"sha": "fs", "content": _b64(requirements)}),
    }
    client = httpx.AsyncClient(transport=_gh_handler(routes))
    svc = AutoRemediationService(enabled=True, github_token="ghp_xxx", client=client)
    result = await svc.remediate(_sca_finding())
    assert result.success is False
    assert result.error is not None and "package_not_found" in result.error
    await client.aclose()


@pytest.mark.asyncio
async def test_unsupported_finding_returns_failure_without_http() -> None:
    """No HTTP requests when finding lacks osv_fixed_in."""
    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    svc = AutoRemediationService(enabled=True, github_token="ghp_xxx", client=client)
    f = _sca_finding(evidence={"package": "requests", "installed_version": "2.30.0"})
    result = await svc.remediate(f)
    assert result.success is False
    assert captured == []  # short-circuit before any GitHub call
    await client.aclose()


@pytest.mark.asyncio
async def test_commit_message_carries_cve_and_versions() -> None:
    """Spot-check the PUT contents call to ensure the commit message is correct."""
    requirements = "requests==2.30.0\n"
    captured: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "GET" and "git/ref/heads/main" in url:
            return httpx.Response(200, json={"object": {"sha": "abc"}})
        if request.method == "GET" and "contents/requirements.txt" in url:
            return httpx.Response(
                200, json={"sha": "fs", "content": _b64(requirements)}
            )
        if request.method == "POST" and "git/refs" in url:
            return httpx.Response(201, json={})
        if request.method == "PUT" and "contents/requirements.txt" in url:
            captured.append(json.loads(request.content.decode()))
            return httpx.Response(201, json={})
        if request.method == "POST" and "/pulls" in url:
            return httpx.Response(
                201, json={"html_url": "https://github.com/acme/demo/pull/9"}
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    svc = AutoRemediationService(enabled=True, github_token="ghp_xxx", client=client)
    await svc.remediate(_sca_finding())
    assert captured
    msg = captured[0]["message"]
    assert "requests" in msg
    assert "2.30.0" in msg and "2.32.0" in msg
    assert "CVE-2024-1234" in msg
    await client.aclose()
