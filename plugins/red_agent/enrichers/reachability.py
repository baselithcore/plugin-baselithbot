"""Reachability enricher — drop SCA noise that the codebase never invokes.

A ``Finding`` from an SCA tool (Trivy / Grype / Syft / Checkov) flags a
vulnerable package present in the dependency graph. The dominant noise
source is *unreachable* vulnerabilities: the dependency is installed
but no code in the project's source tree references the vulnerable
import surface, so the runtime behavior is unaffected. Snyk Reachable
Vulnerability Mgmt and Endor Labs Reachable Risk are the commercial
products built on this insight.

This MVP enricher trades depth for portability:

* **Python**: walks ``*.py`` files under the repo root, parses each
  with the stdlib :mod:`ast`, and collects the top-level packages
  appearing in ``Import`` / ``ImportFrom`` statements.
* **JavaScript / TypeScript**: parses ``package.json`` to enumerate
  declared dependencies and greps source files for ``import`` /
  ``require()`` references to those packages.
* **Other ecosystems** (Java/Go/.NET): not analyzed — we never claim
  ``reachable=false`` outside the supported languages, so callers stay
  on the safe side.

Outputs annotate ``Finding.evidence``:

* ``reachable``: ``True`` / ``False`` / ``None`` (unknown)
* ``reachability_confidence``: ``"high" | "medium" | "low"``
* ``reachability_method``: ``"python_ast" | "npm_imports" | "skipped"``

Suppression is opt-in via the ``drop_unreachable`` flag: when enabled,
``reachable=False`` findings under the configured severity ceiling are
dropped from the scan result. KEV-listed CVEs are *never* dropped
regardless of reachability — known exploited vulnerabilities stay
visible by definition.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, Severity

logger = get_logger(__name__)

# Common name remaps where the import name differs from the distribution
# name. Keep the list intentionally short — operators add to it via
# ``RED_AGENT_REACHABILITY_PYTHON_ALIASES`` when they encounter the rare
# remap that is not already covered.
_PYTHON_DIST_TO_IMPORT: dict[str, set[str]] = {
    "pyyaml": {"yaml"},
    "beautifulsoup4": {"bs4"},
    "pillow": {"PIL"},
    "scikit-learn": {"sklearn"},
    "python-dateutil": {"dateutil"},
    "pyjwt": {"jwt"},
    "msgpack-python": {"msgpack"},
    "opencv-python": {"cv2"},
    "protobuf": {"google.protobuf"},
}

_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

_REACHABLE_SCANNERS: set[str] = {"trivy", "grype", "syft"}

_JS_IMPORT_RE = re.compile(
    r"""(?:from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)


class ReachabilityEnricher:
    """Annotate (and optionally drop) SCA findings by source-tree reachability."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        drop_unreachable: bool = False,
        drop_unreachable_max_severity: Severity = Severity.MEDIUM,
        max_files_scanned: int = 5000,
        python_aliases: dict[str, set[str]] | None = None,
    ) -> None:
        self.enabled = enabled
        self.drop_unreachable = drop_unreachable
        self.drop_unreachable_max_severity = drop_unreachable_max_severity
        self.max_files_scanned = max_files_scanned
        merged_aliases = dict(_PYTHON_DIST_TO_IMPORT)
        if python_aliases:
            for k, v in python_aliases.items():
                merged_aliases.setdefault(k.lower(), set()).update(v)
        self.python_aliases = merged_aliases
        self._cache: dict[Path, _RepoIndex] = {}

    def enrich(
        self,
        findings: list[Finding],
        *,
        repo_root: Path | str | None,
    ) -> tuple[list[Finding], list[Finding]]:
        """Return ``(kept, suppressed)``.

        ``suppressed`` only carries findings that the configured drop
        policy explicitly removes; otherwise every input finding lands
        in ``kept`` (annotated when applicable).
        """
        if not self.enabled or not findings:
            return findings, []
        if repo_root is None:
            return findings, []
        root = Path(repo_root)
        if not root.exists() or not root.is_dir():
            return findings, []

        try:
            index = self._cache.get(root)
            if index is None:
                index = _build_repo_index(root, max_files=self.max_files_scanned)
                self._cache[root] = index
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.reachability.index_failed",
                extra={"root": str(root), "err": str(exc)},
            )
            return findings, []

        kept: list[Finding] = []
        suppressed: list[Finding] = []
        for f in findings:
            verdict = self._verdict(f, index)
            self._annotate(f, verdict)
            if (
                self.drop_unreachable
                and verdict.reachable is False
                and not _kev_listed(f)
                and _SEVERITY_ORDER[f.severity]
                <= _SEVERITY_ORDER[self.drop_unreachable_max_severity]
            ):
                suppressed.append(f)
            else:
                kept.append(f)
        return kept, suppressed

    def _verdict(self, f: Finding, index: _RepoIndex) -> _Verdict:
        if f.scanner not in _REACHABLE_SCANNERS:
            return _Verdict(reachable=None, confidence="low", method="skipped")
        package = (
            (f.evidence or {}).get("package") if isinstance(f.evidence, dict) else None
        )
        if not isinstance(package, str) or not package:
            return _Verdict(reachable=None, confidence="low", method="skipped")
        package_lower = package.lower()
        # Python first
        for cand in self._python_candidates(package_lower):
            if cand in index.python_modules:
                return _Verdict(
                    reachable=True, confidence="medium", method="python_ast"
                )
        if index.python_files > 0 and package_lower in index.python_dist_names:
            # We saw this distribution declared (e.g. requirements.txt) but
            # no import statement referenced it.
            return _Verdict(reachable=False, confidence="medium", method="python_ast")
        # JS / TS
        if package_lower in index.js_imports:
            return _Verdict(reachable=True, confidence="medium", method="npm_imports")
        if package_lower in index.js_declared_deps:
            return _Verdict(reachable=False, confidence="medium", method="npm_imports")
        return _Verdict(reachable=None, confidence="low", method="skipped")

    def _python_candidates(self, package_lower: str) -> set[str]:
        """Return the set of import names that may correspond to ``package``."""
        candidates: set[str] = {package_lower.replace("-", "_")}
        candidates.update(self.python_aliases.get(package_lower, set()))
        return candidates

    @staticmethod
    def _annotate(f: Finding, verdict: _Verdict) -> None:
        if not isinstance(f.evidence, dict):
            return
        if verdict.reachable is not None:
            f.evidence["reachable"] = verdict.reachable
        f.evidence["reachability_confidence"] = verdict.confidence
        f.evidence["reachability_method"] = verdict.method


# --- internals ---------------------------------------------------------


class _Verdict:
    __slots__ = ("reachable", "confidence", "method")

    def __init__(self, *, reachable: bool | None, confidence: str, method: str) -> None:
        self.reachable = reachable
        self.confidence = confidence
        self.method = method


class _RepoIndex:
    __slots__ = (
        "python_modules",
        "python_files",
        "python_dist_names",
        "js_imports",
        "js_declared_deps",
    )

    def __init__(self) -> None:
        self.python_modules: set[str] = set()
        self.python_files: int = 0
        self.python_dist_names: set[str] = set()
        self.js_imports: set[str] = set()
        self.js_declared_deps: set[str] = set()


_SKIP_DIRS: set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "target",
}


def _build_repo_index(root: Path, *, max_files: int) -> _RepoIndex:
    """Walk ``root`` and produce a lightweight import/dependency index."""
    idx = _RepoIndex()
    seen = 0
    for path in root.rglob("*"):
        if seen >= max_files:
            break
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == ".py":
                _collect_python_imports(path, idx)
                idx.python_files += 1
                seen += 1
            elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                _collect_js_imports(path, idx)
                seen += 1
            elif path.name == "package.json":
                _collect_js_declared_deps(path, idx)
            elif path.name in {"requirements.txt", "requirements-dev.txt"}:
                _collect_python_dist_names(path, idx)
            elif path.name == "pyproject.toml":
                _collect_pyproject_deps(path, idx)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "red_agent.reachability.parse_skipped",
                extra={"path": str(path), "err": str(exc)},
            )
    return idx


def _collect_python_imports(path: Path, idx: _RepoIndex) -> None:
    src = path.read_text(errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                idx.python_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                idx.python_modules.add(node.module.split(".")[0])


def _collect_python_dist_names(path: Path, idx: _RepoIndex) -> None:
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # strip extras + version specifiers
        name = re.split(r"[<>=!~;\[]", line, maxsplit=1)[0].strip()
        if name:
            idx.python_dist_names.add(name.lower())


def _collect_pyproject_deps(path: Path, idx: _RepoIndex) -> None:
    try:
        import tomllib
    except ImportError:  # pragma: no cover — py<3.11
        return
    try:
        doc = tomllib.loads(path.read_text(errors="replace"))
    except Exception:  # noqa: BLE001
        return
    deps_seen: list[str] = []
    proj = doc.get("project", {}) if isinstance(doc, dict) else {}
    deps_seen.extend(proj.get("dependencies", []) or [])
    optional = proj.get("optional-dependencies", {}) or {}
    if isinstance(optional, dict):
        for v in optional.values():
            deps_seen.extend(v or [])
    for dep in deps_seen:
        if not isinstance(dep, str):
            continue
        name = re.split(r"[<>=!~;\[]", dep, maxsplit=1)[0].strip()
        if name:
            idx.python_dist_names.add(name.lower())


def _collect_js_imports(path: Path, idx: _RepoIndex) -> None:
    src = path.read_text(errors="replace")
    for match in _JS_IMPORT_RE.finditer(src):
        spec = match.group(1) or match.group(2) or ""
        if not spec or spec.startswith("."):
            continue
        # Bare specifier — first segment is the package name; @scope/name handled.
        if spec.startswith("@"):
            parts = spec.split("/", 2)
            if len(parts) >= 2:
                idx.js_imports.add(f"{parts[0]}/{parts[1]}".lower())
        else:
            idx.js_imports.add(spec.split("/", 1)[0].lower())


def _collect_js_declared_deps(path: Path, idx: _RepoIndex) -> None:
    try:
        doc = json.loads(path.read_text(errors="replace"))
    except (json.JSONDecodeError, OSError):
        return
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        section = doc.get(key) if isinstance(doc, dict) else None
        if isinstance(section, dict):
            for name in section.keys():
                if isinstance(name, str):
                    idx.js_declared_deps.add(name.lower())


def _kev_listed(f: Finding) -> bool:
    return isinstance(f.evidence, dict) and bool(f.evidence.get("kev_listed"))
