"""Auto-remediation pull-request generator.

Operator-triggered: given a Finding flagged by an SCA scanner, opens a
fix PR on the upstream Git repository that bumps the vulnerable
package to a version listed in ``Finding.evidence['osv_fixed_in']``.
The flow is intentionally narrow for the MVP:

* Only Python ``requirements.txt`` rewrites are supported. Other
  ecosystems (npm ``package.json``, Cargo ``Cargo.toml``, etc.) are
  TODO and currently return ``UnsupportedRemediation``.
* Only acts on findings that already carry ``osv_fixed_in`` data — the
  OSV.dev enricher must have run upstream.
* Repository identification comes from operator-controlled
  ``Target.metadata`` (``repo_owner``, ``repo_name``, ``default_branch``)
  to avoid any guessing from the target value.

GitHub Contents API is used (no git binary required):

1. ``GET /repos/{owner}/{repo}/contents/{path}?ref={branch}`` → load
   current file + sha.
2. ``GET /repos/{owner}/{repo}/git/ref/heads/{branch}`` → resolve
   default-branch HEAD sha.
3. ``POST /repos/{owner}/{repo}/git/refs`` → create branch
   ``red-agent/{finding_id}``.
4. ``PUT /repos/{owner}/{repo}/contents/{path}`` → commit the bumped
   file on the new branch.
5. ``POST /repos/{owner}/{repo}/pulls`` → open the PR.

Fail-open at every step: any HTTP error returns a structured failure
the caller surfaces in the audit log; nothing in the finding state is
mutated unless the PR succeeds.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

logger = get_logger(__name__)

_GITHUB_API = "https://api.github.com"
_REQUIREMENTS_DEFAULT_PATH = "requirements.txt"
_BRANCH_PREFIX = "red-agent"


class UnsupportedRemediation(Exception):
    """Raised when a finding cannot be remediated automatically."""


@dataclass(slots=True)
class RemediationResult:
    success: bool
    pr_url: str | None = None
    branch: str | None = None
    fixed_version: str | None = None
    error: str | None = None


class AutoRemediationService:
    """Open dependency-bump PRs from SCA findings."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        github_token: str | None = None,
        request_timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled and bool(github_token)
        self.github_token = github_token
        self.request_timeout_seconds = request_timeout_seconds
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None

    async def remediate(self, finding: Finding) -> RemediationResult:
        if not self.enabled:
            return RemediationResult(success=False, error="auto_pr_disabled")
        try:
            plan = _plan_remediation(finding)
        except UnsupportedRemediation as exc:
            return RemediationResult(success=False, error=str(exc))
        client = await self._get_client()
        try:
            return await _open_pr(client, plan, token=self.github_token or "")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.autopr.failed",
                extra={"finding_id": str(finding.id), "err": str(exc)},
            )
            return RemediationResult(success=False, error=str(exc))

    async def aclose(self) -> None:
        client = self._owned_client
        self._owned_client = None
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(
                timeout=self.request_timeout_seconds,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
        return self._owned_client


@dataclass(slots=True)
class _Plan:
    finding_id: str
    owner: str
    repo: str
    base_branch: str
    file_path: str
    package: str
    current_version: str
    fixed_version: str
    cve: str | None


def _plan_remediation(f: Finding) -> _Plan:
    """Validate finding inputs and assemble the file-rewrite plan."""
    ev = f.evidence if isinstance(f.evidence, dict) else {}
    package = ev.get("package")
    current_version = ev.get("installed_version") or ev.get("version")
    fixed_versions = ev.get("osv_fixed_in")
    if not (
        isinstance(package, str)
        and isinstance(current_version, str)
        and isinstance(fixed_versions, list)
        and fixed_versions
    ):
        raise UnsupportedRemediation("missing package / version / osv_fixed_in")

    fixed_version = next((v for v in fixed_versions if isinstance(v, str)), None)
    if not fixed_version:
        raise UnsupportedRemediation("no concrete fixed version in osv_fixed_in")

    repo_meta = ev.get("repo") or {}
    owner = repo_meta.get("owner") or ev.get("repo_owner")
    repo = repo_meta.get("name") or ev.get("repo_name")
    base_branch = repo_meta.get("default_branch") or ev.get("default_branch") or "main"
    if not (isinstance(owner, str) and isinstance(repo, str)):
        raise UnsupportedRemediation(
            "finding.evidence.repo_owner + repo_name required for auto-PR"
        )

    file_path = ev.get("requirements_path") or _REQUIREMENTS_DEFAULT_PATH
    return _Plan(
        finding_id=str(f.id),
        owner=owner,
        repo=repo,
        base_branch=str(base_branch),
        file_path=str(file_path),
        package=package,
        current_version=current_version,
        fixed_version=fixed_version,
        cve=f.cve,
    )


async def _open_pr(
    client: httpx.AsyncClient, plan: _Plan, *, token: str
) -> RemediationResult:
    auth = {"Authorization": f"Bearer {token}"}
    base = f"{_GITHUB_API}/repos/{plan.owner}/{plan.repo}"
    branch = f"{_BRANCH_PREFIX}/{plan.finding_id}"

    # 1) Resolve base branch HEAD sha.
    resp = await client.get(f"{base}/git/ref/heads/{plan.base_branch}", headers=auth)
    if resp.status_code != 200:
        return RemediationResult(
            success=False, error=f"resolve_base_branch_failed:{resp.status_code}"
        )
    base_sha = (resp.json() or {}).get("object", {}).get("sha")
    if not isinstance(base_sha, str):
        return RemediationResult(success=False, error="missing_base_sha")

    # 2) Load current file content + sha at base branch.
    resp = await client.get(
        f"{base}/contents/{plan.file_path}",
        headers=auth,
        params={"ref": plan.base_branch},
    )
    if resp.status_code != 200:
        return RemediationResult(
            success=False, error=f"load_file_failed:{resp.status_code}"
        )
    file_doc = resp.json() or {}
    file_sha = file_doc.get("sha")
    encoded = file_doc.get("content", "")
    try:
        original = base64.b64decode(encoded).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return RemediationResult(success=False, error=f"decode_failed:{exc}")

    bumped = _rewrite_requirement(
        original, package=plan.package, fixed_version=plan.fixed_version
    )
    if bumped is None:
        return RemediationResult(
            success=False, error=f"package_not_found:{plan.package}"
        )

    # 3) Create branch from base sha.
    resp = await client.post(
        f"{base}/git/refs",
        headers=auth,
        json={"ref": f"refs/heads/{branch}", "sha": base_sha},
    )
    if resp.status_code not in (200, 201):
        return RemediationResult(
            success=False, error=f"create_branch_failed:{resp.status_code}"
        )

    # 4) Commit the bumped file on the new branch.
    new_content_b64 = base64.b64encode(bumped.encode()).decode()
    cve_tag = f" ({plan.cve})" if plan.cve else ""
    commit_message = (
        f"fix(deps): bump {plan.package} {plan.current_version} -> "
        f"{plan.fixed_version}{cve_tag}"
    )
    resp = await client.put(
        f"{base}/contents/{plan.file_path}",
        headers=auth,
        json={
            "message": commit_message,
            "content": new_content_b64,
            "sha": file_sha,
            "branch": branch,
        },
    )
    if resp.status_code not in (200, 201):
        return RemediationResult(
            success=False, error=f"commit_failed:{resp.status_code}"
        )

    # 5) Open PR.
    pr_body = (
        f"Auto-generated by red-agent for finding `{plan.finding_id}`.\n\n"
        f"* Package: `{plan.package}`\n"
        f"* Current version: `{plan.current_version}`\n"
        f"* Fixed version: `{plan.fixed_version}`\n"
        + (f"* CVE: `{plan.cve}`\n" if plan.cve else "")
        + "\nMerge after CI + manual review."
    )
    resp = await client.post(
        f"{base}/pulls",
        headers=auth,
        json={
            "title": commit_message,
            "head": branch,
            "base": plan.base_branch,
            "body": pr_body,
        },
    )
    if resp.status_code not in (200, 201):
        return RemediationResult(
            success=False, error=f"open_pr_failed:{resp.status_code}"
        )
    pr_url = (resp.json() or {}).get("html_url")
    return RemediationResult(
        success=True,
        pr_url=pr_url if isinstance(pr_url, str) else None,
        branch=branch,
        fixed_version=plan.fixed_version,
    )


def _rewrite_requirement(src: str, *, package: str, fixed_version: str) -> str | None:
    """Rewrite ``package==X`` (or ``>=`` / ``~=`` / ``>`` / ``<``) in requirements.txt.

    Returns ``None`` when the package is not present in the file so the
    caller can short-circuit the PR.
    """
    pattern = re.compile(
        rf"(?im)^(?P<pre>\s*{re.escape(package)}\s*)"
        r"(?P<op>==|>=|<=|~=|>|<)?"
        r"(?P<ver>[A-Za-z0-9_.\-]+)?"
        r"(?P<rest>.*)$"
    )
    found = False

    def _sub(m: re.Match[str]) -> str:
        nonlocal found
        found = True
        return f"{m.group('pre').rstrip()}=={fixed_version}{m.group('rest')}"

    new = pattern.sub(_sub, src, count=1)
    return new if found else None
