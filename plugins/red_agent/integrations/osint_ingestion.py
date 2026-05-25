"""OSINT discovery ingestion.

Pulls together the per-scan output of the OSINT scanners
(``subfinder``, ``crtsh``) and any externally configured
:class:`EASMConnector`, deduplicates against the configured scope,
and — when ``osint_auto_promote_to_targets`` is set — produces
``red_agent_targets`` candidate records for operator review.

Auto-promotion is intentionally narrow: a discovery only becomes a
target candidate when

1. the master OSINT toggle is on,
2. ``osint_auto_promote_to_targets`` is on, **and**
3. the host matches the engagement's scope policy (allowlist regex
   or bug-bounty program).

The ingestion path never auto-launches a scan. Operators must
review the ``state=discovered`` records in the Targets tab and
explicitly approve them; this is the same control plane the
manual-target wizard uses today.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from core.observability.logging import get_logger
from plugins.red_agent.integrations.easm import DiscoveredAsset, EASMConnector
from plugins.red_agent.models import Finding

logger = get_logger(__name__)


@dataclass(frozen=True)
class OSINTIngestionResult:
    """Aggregate of a single ingestion pass."""

    discovered: list[DiscoveredAsset]
    promoted: list[DiscoveredAsset]
    skipped_out_of_scope: list[str]
    skipped_already_known: list[str]


def findings_to_assets(
    findings: Iterable[Finding], *, apex: str
) -> list[DiscoveredAsset]:
    """Lift OSINT findings (subfinder/crtsh) into DiscoveredAsset records.

    The two built-in scanners write the discovered host into
    ``finding.endpoint``; non-OSINT findings are ignored.
    """

    out: list[DiscoveredAsset] = []
    seen: set[tuple[str, str]] = set()
    for f in findings:
        if f.scanner not in {"subfinder", "crtsh"}:
            continue
        host = (f.endpoint or "").strip().lower()
        if not host:
            continue
        key = (host, f.scanner)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            DiscoveredAsset(
                host=host,
                source=f.scanner,
                discovered_at=f.discovered_at,
                apex=apex,
                metadata=dict(f.evidence) if isinstance(f.evidence, dict) else {},
            )
        )
    return out


async def merge_external(
    *,
    connector: EASMConnector,
    apex: str,
    builtin: list[DiscoveredAsset],
) -> list[DiscoveredAsset]:
    """Append connector output to the built-in scanner results.

    Fail-open at the connector boundary. Dedup is host+source; an
    asset surfaced by both a built-in scanner and an external EASM
    is preserved twice on purpose so the operator sees the
    independent corroboration.
    """

    try:
        external = await connector.discover(apex=apex)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "red_agent.osint.connector_failed",
            extra={"apex": apex, "connector": connector.name, "err": str(exc)},
        )
        external = []
    seen: set[tuple[str, str]] = {(a.host, a.source) for a in builtin}
    merged: list[DiscoveredAsset] = list(builtin)
    for a in external:
        key = (a.host, a.source)
        if key in seen:
            continue
        seen.add(key)
        merged.append(a)
    return merged


def select_for_promotion(
    assets: list[DiscoveredAsset],
    *,
    auto_promote: bool,
    in_scope: Callable[[str], bool],
    known_hosts: set[str],
    max_results: int,
) -> OSINTIngestionResult:
    """Apply scope/dedup/cap filters and return the ingestion outcome.

    ``in_scope(host)`` is an injected predicate so this function
    stays pure: callers wire it to the engagement's scope policy
    (allowlist regex / bug-bounty program). ``known_hosts`` carries
    the lowercase set of hostnames already present as targets.
    """

    promoted: list[DiscoveredAsset] = []
    out_of_scope: list[str] = []
    already_known: list[str] = []

    for asset in assets:
        host = asset.host.lower()
        if host in known_hosts:
            already_known.append(host)
            continue
        if not auto_promote:
            continue
        try:
            ok = bool(in_scope(host))
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            out_of_scope.append(host)
            continue
        promoted.append(asset)
        known_hosts.add(host)
        if len(promoted) >= max_results:
            break

    return OSINTIngestionResult(
        discovered=assets,
        promoted=promoted,
        skipped_out_of_scope=out_of_scope,
        skipped_already_known=already_known,
    )
