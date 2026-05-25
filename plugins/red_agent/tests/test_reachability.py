"""Reachability enricher tests (Python AST + JS imports + suppression)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plugins.red_agent.enrichers.reachability import ReachabilityEnricher
from plugins.red_agent.models import Finding, Severity


def _sca_finding(
    *,
    package: str,
    severity: Severity = Severity.MEDIUM,
    cve: str = "CVE-2024-9999",
    scanner: str = "trivy",
    evidence: dict | None = None,
) -> Finding:
    base_evidence = {"package": package}
    if evidence:
        base_evidence.update(evidence)
    return Finding(
        scanner=scanner,
        title=f"{cve} in {package}",
        description="vulnerable dependency",
        severity=severity,
        cve=cve,
        target="repo://demo",
        evidence=base_evidence,
    )


def _make_python_repo(root: Path, *, imports: list[str], deps: list[str]) -> None:
    src = root / "src"
    src.mkdir()
    code = "\n".join([f"import {m}" for m in imports])
    (src / "main.py").write_text(code or "x = 1\n")
    if deps:
        (root / "requirements.txt").write_text("\n".join(deps))


def _make_js_repo(root: Path, *, imports: list[str], deps: list[str]) -> None:
    src = root / "src"
    src.mkdir()
    body = "\n".join([f"import x from '{name}';" for name in imports])
    (src / "index.js").write_text(body or "const x = 1;\n")
    pkg = {"name": "demo", "dependencies": {n: "*" for n in deps}}
    (root / "package.json").write_text(json.dumps(pkg))


# --- Disabled / no-op paths ------------------------------------------


def test_disabled_passthrough(tmp_path: Path) -> None:
    enricher = ReachabilityEnricher(enabled=False)
    f = _sca_finding(package="requests")
    kept, suppressed = enricher.enrich([f], repo_root=tmp_path)
    assert kept == [f]
    assert suppressed == []


def test_missing_repo_root_passthrough() -> None:
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="requests")
    kept, suppressed = enricher.enrich([f], repo_root="/path/that/does/not/exist")
    assert kept == [f]
    assert suppressed == []


def test_non_sca_scanner_skipped(tmp_path: Path) -> None:
    _make_python_repo(tmp_path, imports=[], deps=[])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="requests", scanner="nuclei")
    kept, suppressed = enricher.enrich([f], repo_root=tmp_path)
    assert len(kept) == 1
    assert kept[0].evidence["reachability_method"] == "skipped"


# --- Python -----------------------------------------------------------


def test_python_imported_dependency_marks_reachable(tmp_path: Path) -> None:
    _make_python_repo(tmp_path, imports=["requests"], deps=["requests==2.30.0"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="requests")
    kept, suppressed = enricher.enrich([f], repo_root=tmp_path)
    assert kept[0].evidence["reachable"] is True
    assert kept[0].evidence["reachability_method"] == "python_ast"
    assert suppressed == []


def test_python_declared_but_not_imported_marks_unreachable(tmp_path: Path) -> None:
    _make_python_repo(
        tmp_path, imports=["requests"], deps=["requests==2.30.0", "lxml==5.1.0"]
    )
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="lxml")
    kept, suppressed = enricher.enrich([f], repo_root=tmp_path)
    assert kept[0].evidence["reachable"] is False


def test_python_alias_pyyaml(tmp_path: Path) -> None:
    _make_python_repo(tmp_path, imports=["yaml"], deps=["pyyaml==6.0"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="pyyaml")
    kept, _ = enricher.enrich([f], repo_root=tmp_path)
    assert kept[0].evidence["reachable"] is True


def test_python_unknown_when_not_in_dist(tmp_path: Path) -> None:
    _make_python_repo(tmp_path, imports=["requests"], deps=["requests==2.30.0"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="some-package-not-in-repo")
    kept, _ = enricher.enrich([f], repo_root=tmp_path)
    assert "reachable" not in kept[0].evidence
    assert kept[0].evidence["reachability_method"] == "skipped"


def test_drop_unreachable_below_threshold(tmp_path: Path) -> None:
    _make_python_repo(
        tmp_path, imports=["requests"], deps=["requests==2.30.0", "lxml==5.1.0"]
    )
    enricher = ReachabilityEnricher(
        enabled=True,
        drop_unreachable=True,
        drop_unreachable_max_severity=Severity.MEDIUM,
    )
    low = _sca_finding(package="lxml", severity=Severity.LOW)
    high = _sca_finding(package="lxml", severity=Severity.HIGH)
    kept, suppressed = enricher.enrich([low, high], repo_root=tmp_path)
    assert len(suppressed) == 1
    assert suppressed[0].severity == Severity.LOW
    assert len(kept) == 1
    assert kept[0].severity == Severity.HIGH


def test_kev_listed_never_dropped(tmp_path: Path) -> None:
    _make_python_repo(
        tmp_path, imports=["requests"], deps=["requests==2.30.0", "lxml==5.1.0"]
    )
    enricher = ReachabilityEnricher(
        enabled=True,
        drop_unreachable=True,
        drop_unreachable_max_severity=Severity.MEDIUM,
    )
    f = _sca_finding(
        package="lxml",
        severity=Severity.LOW,
        evidence={"kev_listed": True},
    )
    kept, suppressed = enricher.enrich([f], repo_root=tmp_path)
    assert kept == [f]
    assert suppressed == []


# --- JavaScript -------------------------------------------------------


def test_js_imported_dependency_marks_reachable(tmp_path: Path) -> None:
    _make_js_repo(tmp_path, imports=["lodash", "react"], deps=["lodash", "react"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="lodash")
    kept, _ = enricher.enrich([f], repo_root=tmp_path)
    assert kept[0].evidence["reachable"] is True
    assert kept[0].evidence["reachability_method"] == "npm_imports"


def test_js_declared_only_marks_unreachable(tmp_path: Path) -> None:
    _make_js_repo(tmp_path, imports=["lodash"], deps=["lodash", "moment"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="moment")
    kept, _ = enricher.enrich([f], repo_root=tmp_path)
    assert kept[0].evidence["reachable"] is False


def test_js_scoped_package_resolution(tmp_path: Path) -> None:
    _make_js_repo(tmp_path, imports=["@babel/core"], deps=["@babel/core"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="@babel/core")
    kept, _ = enricher.enrich([f], repo_root=tmp_path)
    assert kept[0].evidence["reachable"] is True


# --- Cache ------------------------------------------------------------


def test_index_cached_per_root(tmp_path: Path) -> None:
    _make_python_repo(tmp_path, imports=["requests"], deps=["requests==2.30.0"])
    enricher = ReachabilityEnricher(enabled=True)
    f = _sca_finding(package="requests")
    enricher.enrich([f], repo_root=tmp_path)
    enricher.enrich([f], repo_root=tmp_path)
    assert tmp_path in enricher._cache


# --- run_reachability helper -----------------------------------------


@pytest.mark.asyncio
async def test_run_reachability_audits_suppressed(tmp_path: Path) -> None:
    from plugins.red_agent._post_pipeline import run_reachability
    from plugins.red_agent.models import ScanRequest, Target, TargetType
    from uuid import uuid4

    _make_python_repo(
        tmp_path, imports=["requests"], deps=["requests==2.30.0", "lxml==5.1.0"]
    )
    enricher = ReachabilityEnricher(
        enabled=True,
        drop_unreachable=True,
        drop_unreachable_max_severity=Severity.HIGH,
    )

    audited: list[dict] = []

    class _AuditStub:
        async def record(self, **kwargs: object) -> None:
            audited.append(kwargs)

    request = ScanRequest(
        target=Target(type=TargetType.REPO, value=str(tmp_path)),
        requested_by="op",
    )
    f = _sca_finding(package="lxml", severity=Severity.LOW)
    kept = await run_reachability(
        reachability=enricher,
        audit=_AuditStub(),  # type: ignore[arg-type]
        scan_id=uuid4(),
        findings=[f],
        request=request,
    )
    assert kept == []
    assert len(audited) == 1
    assert audited[0]["payload"]["suppressed"] == 1
    assert "lxml" in audited[0]["payload"]["packages"]
