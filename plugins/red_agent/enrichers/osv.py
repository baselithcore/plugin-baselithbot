"""OSV.dev enricher — cross-ecosystem vulnerability metadata.

OSV is Google's open-source vulnerability database, aggregating advisory
sources across npm, PyPI, Go, Maven, RubyGems, Cargo, Packagist,
NuGet, Composer, Pub, Debian, Alpine, Linux distros. Free, rate-friendly,
authoritative for SCA findings whose CVE upstream may be sparse.

Behavior:

* For a finding with ``cve``: ``POST /v1/vulns/<id>`` returns the OSV
  record directly.
* For an SCA finding without a CVE (only ``evidence.package`` /
  ``evidence.installed_version``): ``POST /v1/query`` with the package
  + version, returns matching vulns.
* Annotates ``Finding.evidence``:
  * ``osv_id`` — primary OSV identifier (e.g. ``GHSA-...``)
  * ``osv_aliases`` — list of all known IDs (CVE, GHSA, OSV)
  * ``osv_summary`` — one-line summary
  * ``osv_fixed_in`` — list of fixed versions across declared ranges
  * ``osv_references`` — list of advisory URLs

Fail-open: any HTTP / parse error returns the input list unchanged.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

logger = get_logger(__name__)

_ENDPOINT_VULN = "https://api.osv.dev/v1/vulns/{id}"
_ENDPOINT_QUERY = "https://api.osv.dev/v1/query"

# Map common scanner-emitted ecosystem labels to the OSV canonical names.
_ECOSYSTEM_ALIAS: dict[str, str] = {
    "npm": "npm",
    "pypi": "PyPI",
    "python": "PyPI",
    "go": "Go",
    "golang": "Go",
    "maven": "Maven",
    "gem": "RubyGems",
    "rubygems": "RubyGems",
    "cargo": "crates.io",
    "rust": "crates.io",
    "composer": "Packagist",
    "packagist": "Packagist",
    "nuget": "NuGet",
}


class OSVEnricher:
    """Annotate findings with OSV.dev advisory data."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        request_timeout_seconds: float = 10.0,
        max_concurrent_requests: int = 8,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled
        self.request_timeout_seconds = request_timeout_seconds
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_requests))

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        targets = [f for f in findings if _osv_eligible(f)]
        if not targets:
            return findings
        client = await self._get_client()
        try:
            await asyncio.gather(
                *(self._annotate_finding(client, f) for f in targets),
                return_exceptions=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("red_agent.osv.enrich_failed", extra={"err": str(exc)})
        return findings

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
        if self._owned_client is not None:
            return self._owned_client
        async with self._client_lock:
            if self._owned_client is None:
                self._owned_client = httpx.AsyncClient(
                    timeout=self.request_timeout_seconds
                )
            return self._owned_client

    async def _annotate_finding(self, client: httpx.AsyncClient, f: Finding) -> None:
        async with self._semaphore:
            try:
                record = await self._fetch_record(client, f)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "red_agent.osv.lookup_failed",
                    extra={"finding": str(f.id), "err": str(exc)},
                )
                return
        if not record:
            return
        if not isinstance(f.evidence, dict):
            return
        f.evidence["osv_id"] = record.get("id")
        aliases = record.get("aliases") or []
        if isinstance(aliases, list):
            f.evidence["osv_aliases"] = [a for a in aliases if isinstance(a, str)]
        summary = record.get("summary")
        if isinstance(summary, str):
            f.evidence["osv_summary"] = summary
        fixed = _collect_fixed_versions(record)
        if fixed:
            f.evidence["osv_fixed_in"] = fixed
        refs = [
            r.get("url")
            for r in (record.get("references") or [])
            if isinstance(r, dict) and isinstance(r.get("url"), str)
        ]
        if refs:
            f.evidence["osv_references"] = refs[:10]

    async def _fetch_record(
        self, client: httpx.AsyncClient, f: Finding
    ) -> dict[str, Any] | None:
        if f.cve:
            resp = await client.get(_ENDPOINT_VULN.format(id=f.cve))
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        # Package + version query
        ev = f.evidence if isinstance(f.evidence, dict) else {}
        package = ev.get("package")
        version = ev.get("installed_version") or ev.get("version")
        ecosystem = _resolve_ecosystem(f, ev)
        if not (isinstance(package, str) and isinstance(version, str) and ecosystem):
            return None
        body = {
            "package": {"name": package, "ecosystem": ecosystem},
            "version": version,
        }
        resp = await client.post(_ENDPOINT_QUERY, json=body)
        if resp.status_code != 200:
            return None
        doc = resp.json() or {}
        vulns = doc.get("vulns") or []
        if not vulns:
            return None
        # Prefer the entry whose aliases match the finding's CVE; otherwise first.
        first = vulns[0]
        return first if isinstance(first, dict) else None


def _osv_eligible(f: Finding) -> bool:
    if f.cve:
        return True
    if not isinstance(f.evidence, dict):
        return False
    package = f.evidence.get("package")
    version = f.evidence.get("installed_version") or f.evidence.get("version")
    return bool(package and version)


def _resolve_ecosystem(f: Finding, evidence: dict[str, Any]) -> str | None:
    raw = evidence.get("ecosystem") or evidence.get("type")
    if isinstance(raw, str) and raw:
        return _ECOSYSTEM_ALIAS.get(raw.lower(), raw)
    # Heuristic by scanner name when ecosystem missing.
    if f.scanner in {"trivy", "grype", "syft"}:
        purl = evidence.get("purl")
        if isinstance(purl, str) and purl.startswith("pkg:"):
            kind = purl.removeprefix("pkg:").split("/", 1)[0]
            return _ECOSYSTEM_ALIAS.get(kind.lower())
    return None


def _collect_fixed_versions(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    affected = record.get("affected") or []
    if not isinstance(affected, list):
        return out
    for entry in affected:
        if not isinstance(entry, dict):
            continue
        ranges = entry.get("ranges") or []
        for r in ranges if isinstance(ranges, list) else []:
            for ev in (r.get("events") or []) if isinstance(r, dict) else []:
                if isinstance(ev, dict) and isinstance(ev.get("fixed"), str):
                    out.append(ev["fixed"])
    # Stable dedup preserving order.
    return list(dict.fromkeys(out))
