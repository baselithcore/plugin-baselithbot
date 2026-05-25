"""Dependency-confusion scanner.

Reads package manifests under a ``REPO`` checkout and checks each
declared dependency against the relevant public registry. A package
that the repo *thinks* is internal but that does **not** exist on
the public registry is a confusion vector — an attacker can register
the name and (for build configurations that resolve public ahead of
internal) get arbitrary code execution at install time.

Two ecosystems ship today:

- ``npm`` — reads ``package.json`` (``dependencies`` +
  ``devDependencies``).
- ``pypi`` — reads ``requirements.txt`` and ``pyproject.toml``
  (PEP 621 ``[project]`` and Poetry ``[tool.poetry.dependencies]``).

The scanner queries the public registry's JSON metadata endpoint
(``https://registry.npmjs.org/<pkg>``,
``https://pypi.org/pypi/<pkg>/json``). A 404 is the smoking-gun
signal; 5xx and timeouts are folded into a low-confidence "registry
lookup failed" path so a flaky upstream never produces a false
high-severity finding.

Operators *must* configure the internal-package allowlist via
``Target.metadata['internal_package_namespaces']`` (e.g.
``["@acme/", "acme_"]``) — without it, the scanner has no way to
distinguish a typo from an intentional internal reference and
returns nothing.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import httpx
import tomllib

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
    TargetType,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

logger = get_logger(__name__)


_NPM_REGISTRY = "https://registry.npmjs.org"
_PYPI_REGISTRY = "https://pypi.org/pypi"

_REQ_LINE = re.compile(r"^([A-Za-z0-9_.\-]+)")


class DependencyConfusionScanner(Scanner):
    name = "dependency_confusion"
    kind = ScannerKind.SCA
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
        ScanIntensity.INTRUSIVE,
    )
    requires_network = True
    default_timeout = 300

    def __init__(
        self,
        sandbox: Any = None,
        timeout: int | None = None,
        *,
        request_timeout_seconds: float = 15.0,
        max_concurrent_requests: int = 8,
    ) -> None:
        super().__init__(sandbox, timeout=timeout)  # type: ignore[arg-type]
        self._timeout = request_timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        if target.type not in (TargetType.REPO, TargetType.IAC):
            return []
        repo_path = self._resolve_repo(target)
        if repo_path is None:
            return []
        namespaces = self._namespaces(target)
        if not namespaces:
            logger.info(
                "red_agent.dependency_confusion.no_namespaces",
                extra={"target": target.value},
            )
            return []

        npm_pkgs = self._collect_npm(repo_path)
        pypi_pkgs = self._collect_pypi(repo_path)
        candidates_npm = [p for p in npm_pkgs if self._is_internal(p, namespaces)]
        candidates_pypi = [p for p in pypi_pkgs if self._is_internal(p, namespaces)]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            findings = await self._check_all(
                client, target, candidates_npm, candidates_pypi
            )
        return findings

    def _resolve_repo(self, target: Target) -> Path | None:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        explicit = meta.get("repo_path")
        if isinstance(explicit, str) and explicit:
            return Path(explicit)
        candidate = Path(target.value)
        if candidate.is_dir():
            return candidate
        return None

    def _namespaces(self, target: Target) -> list[str]:
        meta = target.metadata if isinstance(target.metadata, dict) else {}
        ns = meta.get("internal_package_namespaces")
        if isinstance(ns, list):
            return [str(x) for x in ns if isinstance(x, str) and x]
        return []

    def _is_internal(self, pkg: str, namespaces: list[str]) -> bool:
        return any(pkg.startswith(ns) for ns in namespaces)

    def _collect_npm(self, repo: Path) -> list[str]:
        path = repo / "package.json"
        if not path.is_file():
            return []
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        out: set[str] = set()
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            block = doc.get(key) if isinstance(doc, dict) else None
            if isinstance(block, dict):
                out.update(str(k) for k in block.keys())
        return sorted(out)

    def _collect_pypi(self, repo: Path) -> list[str]:
        out: set[str] = set()
        for fname in ("requirements.txt", "requirements-dev.txt"):
            path = repo / fname
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "-r ", "-e ")):
                    continue
                m = _REQ_LINE.match(line)
                if m:
                    out.add(m.group(1).lower())
        pyproject = repo / "pyproject.toml"
        if pyproject.is_file():
            try:
                doc = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                doc = {}
            project = doc.get("project") or {}
            for dep in project.get("dependencies") or []:
                if isinstance(dep, str):
                    m = _REQ_LINE.match(dep.strip())
                    if m:
                        out.add(m.group(1).lower())
            poetry = (doc.get("tool") or {}).get("poetry") or {}
            for k in poetry.get("dependencies") or {}:
                if isinstance(k, str) and k.lower() != "python":
                    out.add(k.lower())
        return sorted(out)

    async def _check_all(
        self,
        client: httpx.AsyncClient,
        target: Target,
        npm_pkgs: list[str],
        pypi_pkgs: list[str],
    ) -> list[Finding]:
        async def _npm(pkg: str) -> Finding | None:
            return await self._check_pkg(
                client,
                pkg=pkg,
                ecosystem="npm",
                url=f"{_NPM_REGISTRY}/{pkg}",
                target=target,
            )

        async def _pypi(pkg: str) -> Finding | None:
            return await self._check_pkg(
                client,
                pkg=pkg,
                ecosystem="pypi",
                url=f"{_PYPI_REGISTRY}/{pkg}/json",
                target=target,
            )

        tasks: list[Any] = [_npm(p) for p in npm_pkgs] + [_pypi(p) for p in pypi_pkgs]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return [r for r in results if r is not None]

    async def _check_pkg(
        self,
        client: httpx.AsyncClient,
        *,
        pkg: str,
        ecosystem: str,
        url: str,
        target: Target,
    ) -> Finding | None:
        async with self._semaphore:
            try:
                resp = await client.get(url)
            except httpx.HTTPError as exc:
                logger.warning(
                    "red_agent.dependency_confusion.lookup_failed",
                    extra={"pkg": pkg, "ecosystem": ecosystem, "err": str(exc)},
                )
                return None
        if resp.status_code == 404:
            return Finding(
                scanner=self.name,
                title=f"Dependency confusion vector ({ecosystem}): {pkg}",
                description=(
                    f"Package ``{pkg}`` is declared in this repo's "
                    f"{ecosystem} manifest but does not exist on the "
                    "public registry. An attacker who registers the "
                    "name can hijack installations on any build that "
                    "resolves public ahead of internal."
                ),
                severity=Severity.HIGH,
                target=target.value,
                endpoint=pkg,
                evidence={"ecosystem": ecosystem, "registry_status": 404},
                cwe="CWE-829",
                remediation=(
                    "Register the name on the public registry (claim) "
                    "or pin the resolver to your internal index "
                    "(``--index-url`` / ``.npmrc`` ``registry``)."
                ),
            )
        return None
