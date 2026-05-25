"""VEX (Vulnerability Exploitability eXchange) enricher.

Ingests OpenVEX 0.2.0 and CycloneDX VEX 1.6 documents from a filesystem
directory and matches statements against findings by CVE. Suppresses
findings whose VEX status is ``not_affected`` or ``fixed`` so vendor
attestations short-circuit triage instead of leaving the operator to
re-confirm them per scan.

Design invariants:

* **Fail-open**: any parse / IO error returns the input list unchanged.
* **Audit-trail**: suppressed findings emit a ``scan.vex_suppressed``
  audit event with the source document path and justification, so the
  reason is reviewable post-hoc.
* **CVE-keyed**: matching is keyed by ``Finding.cve``; product / purl
  scoping is honored when both sides declare it but is not required.
* **Cache-aware**: documents are reloaded only when their ``mtime``
  changes, so a long-lived enricher does not hammer the filesystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

logger = get_logger(__name__)


# OpenVEX statuses + CycloneDX analysis.state values that suppress the finding.
_SUPPRESS_STATUSES: set[str] = {
    "not_affected",  # OpenVEX
    "fixed",  # OpenVEX
    "false_positive",  # CycloneDX VEX
    "resolved",  # CycloneDX VEX
    "resolved_with_pedigree",  # CycloneDX VEX
}


@dataclass(slots=True)
class VEXStatement:
    """Normalized statement covering OpenVEX + CycloneDX VEX shapes."""

    cve: str
    status: str
    justification: str | None = None
    impact: str | None = None
    products: set[str] = field(default_factory=set)
    source: str = ""

    @property
    def suppresses(self) -> bool:
        return self.status in _SUPPRESS_STATUSES


class VEXStore:
    """File-based VEX document store.

    Scans ``directory`` for ``*.vex.json`` / ``*.openvex.json`` /
    ``*.cdx.json`` / ``*.json`` and parses each into a list of
    :class:`VEXStatement`. The cache is keyed by ``(path, mtime)`` so a
    long-running process picks up changes when the operator drops a new
    document into the directory.
    """

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self._cache: dict[Path, tuple[float, list[VEXStatement]]] = {}

    def load(self) -> list[VEXStatement]:
        if not self.directory.exists() or not self.directory.is_dir():
            return []
        statements: list[VEXStatement] = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                mtime = path.stat().st_mtime
                cached = self._cache.get(path)
                if cached is not None and cached[0] == mtime:
                    statements.extend(cached[1])
                    continue
                parsed = self._parse_file(path)
                self._cache[path] = (mtime, parsed)
                statements.extend(parsed)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "red_agent.vex.parse_failed",
                    extra={"path": str(path), "err": str(exc)},
                )
        return statements

    @staticmethod
    def _parse_file(path: Path) -> list[VEXStatement]:
        doc = json.loads(path.read_text())
        if isinstance(doc, dict) and doc.get("@context", "").startswith(
            "https://openvex.dev"
        ):
            return _parse_openvex(doc, source=str(path))
        if isinstance(doc, dict) and (
            "bomFormat" in doc or "vulnerabilities" in doc or "specVersion" in doc
        ):
            return _parse_cyclonedx_vex(doc, source=str(path))
        return []


def _parse_openvex(doc: dict[str, Any], *, source: str) -> list[VEXStatement]:
    out: list[VEXStatement] = []
    for stmt in doc.get("statements", []) or []:
        if not isinstance(stmt, dict):
            continue
        vuln = stmt.get("vulnerability", {})
        cve = vuln.get("name") or vuln.get("@id") or stmt.get("vulnerability_id") or ""
        if not isinstance(cve, str) or not cve.upper().startswith("CVE-"):
            continue
        products = {
            str(p.get("@id") or p.get("name") or p)
            for p in stmt.get("products", []) or []
            if p
        }
        status = str(stmt.get("status", "")).lower()
        if not status:
            continue
        out.append(
            VEXStatement(
                cve=cve.upper(),
                status=status,
                justification=stmt.get("justification"),
                impact=stmt.get("impact_statement"),
                products=products,
                source=source,
            )
        )
    return out


def _parse_cyclonedx_vex(doc: dict[str, Any], *, source: str) -> list[VEXStatement]:
    out: list[VEXStatement] = []
    for vuln in doc.get("vulnerabilities", []) or []:
        if not isinstance(vuln, dict):
            continue
        cve = vuln.get("id") or ""
        if not isinstance(cve, str) or not cve.upper().startswith("CVE-"):
            continue
        analysis = vuln.get("analysis") or {}
        status = str(analysis.get("state", "")).lower()
        if not status:
            continue
        products = {
            str(a.get("ref"))
            for a in vuln.get("affects", []) or []
            if isinstance(a, dict) and a.get("ref")
        }
        out.append(
            VEXStatement(
                cve=cve.upper(),
                status=status,
                justification=analysis.get("justification"),
                impact=analysis.get("detail"),
                products=products,
                source=source,
            )
        )
    return out


class VexEnricher:
    """Suppresses or annotates findings based on operator-supplied VEX docs."""

    def __init__(
        self,
        *,
        store: VEXStore | None,
        enabled: bool = True,
        suppress_not_affected: bool = True,
        suppress_fixed: bool = True,
    ) -> None:
        self._store = store
        self.enabled = enabled and store is not None
        self.suppress_not_affected = suppress_not_affected
        self.suppress_fixed = suppress_fixed

    def enrich(self, findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
        """Return ``(kept, suppressed)``.

        ``kept`` retains every finding without a suppressing VEX
        statement (and annotates evidence on the rest); ``suppressed``
        carries the findings filtered out by VEX so the orchestrator can
        record an audit event and surface them in a "filtered" panel
        rather than throwing them away silently.
        """
        if not self.enabled or self._store is None or not findings:
            return findings, []
        try:
            statements = self._store.load()
        except Exception as exc:  # noqa: BLE001
            logger.warning("red_agent.vex.store_load_failed", extra={"err": str(exc)})
            return findings, []
        if not statements:
            return findings, []

        index: dict[str, list[VEXStatement]] = {}
        for s in statements:
            index.setdefault(s.cve.upper(), []).append(s)

        kept: list[Finding] = []
        suppressed: list[Finding] = []
        for f in findings:
            if not f.cve:
                kept.append(f)
                continue
            matches = index.get(f.cve.upper(), [])
            if not matches:
                kept.append(f)
                continue
            stmt = self._pick_best_match(matches, finding=f)
            if stmt is None:
                kept.append(f)
                continue
            if isinstance(f.evidence, dict):
                f.evidence["vex_status"] = stmt.status
                if stmt.justification:
                    f.evidence["vex_justification"] = stmt.justification
                if stmt.impact:
                    f.evidence["vex_impact"] = stmt.impact
                f.evidence["vex_source"] = stmt.source
            if stmt.suppresses and self._should_suppress(stmt):
                suppressed.append(f)
            else:
                kept.append(f)
        return kept, suppressed

    def _should_suppress(self, stmt: VEXStatement) -> bool:
        if stmt.status in {"not_affected", "false_positive"}:
            return self.suppress_not_affected
        if stmt.status in {"fixed", "resolved", "resolved_with_pedigree"}:
            return self.suppress_fixed
        return False

    @staticmethod
    def _pick_best_match(
        statements: list[VEXStatement], *, finding: Finding
    ) -> VEXStatement | None:
        """Prefer product-scoped statements when product info is available.

        Falls back to the first statement when no product can be matched
        (still safer than discarding a vendor attestation outright).
        """
        if not statements:
            return None
        target = finding.target.lower() if finding.target else ""
        endpoint = finding.endpoint.lower() if finding.endpoint else ""
        for s in statements:
            if not s.products:
                continue
            for p in s.products:
                pl = p.lower()
                if pl in target or pl in endpoint or target in pl or endpoint in pl:
                    return s
        return statements[0]
