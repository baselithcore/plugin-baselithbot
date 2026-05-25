"""Per-scanner streaming result consumer extracted from ``agent.py``.

Each scanner is processed end-to-end as it completes: post-pipeline,
graph upsert, Postgres insert, WS publish, audit. Fast scanners (nmap,
trivy) deliver findings to the UI minutes before slow ones (zap, nuclei
full template scan) finish. The function still returns only after all
scanners in the iteration are done, so the planner loop sees a complete
batch.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

from core.observability.logging import get_logger
from plugins.red_agent._agent_helpers import (
    run_post_scanner_pipeline,
    scanner_error_finding,
)
from plugins.red_agent.models import Finding

if TYPE_CHECKING:
    from plugins.red_agent.audit import AuditLogger
    from plugins.red_agent.enrichers import (
        AttackMapperEnricher,
        ComplianceMapperEnricher,
        EpssKevEnricher,
        GreyNoiseEnricher,
        OSVEnricher,
        ReachabilityEnricher,
        RiskScoringEnricher,
        VexEnricher,
    )
    from plugins.red_agent.integrations import WebhookNotifier
    from plugins.red_agent.events import ScanEventBus
    from plugins.red_agent.graph import VulnerabilityGraph
    from plugins.red_agent.ml import (
        FPClassifierService,
        LLMTriageService,
        SemanticDedupService,
    )
    from plugins.red_agent.models import ScanRequest
    from plugins.red_agent.persistence import RedAgentPersistence
    from plugins.red_agent.planner import PlannerStep

_logger = get_logger(__name__)


async def consume_scanner_results(
    *,
    pending: dict[asyncio.Task[list[Finding]], str],
    scan_id: UUID,
    request: "ScanRequest",
    step: "PlannerStep",
    audit: "AuditLogger",
    events: "ScanEventBus",
    persistence: "RedAgentPersistence",
    graph: "VulnerabilityGraph",
    fp_classifier: "FPClassifierService | None",
    triage: "LLMTriageService | None",
    dedup: "SemanticDedupService | None",
    epss_kev: "EpssKevEnricher | None",
    attack_mapper: "AttackMapperEnricher | None",
    vex: "VexEnricher | None",
    reachability: "ReachabilityEnricher | None",
    risk_scorer: "RiskScoringEnricher | None",
    compliance: "ComplianceMapperEnricher | None",
    osv: "OSVEnricher | None",
    greynoise: "GreyNoiseEnricher | None",
    webhook: "WebhookNotifier | None",
    validated_only: bool,
    validated_min_cvss: float,
    virustotal: "Any | None" = None,
    shodan: "Any | None" = None,
    censys: "Any | None" = None,
    otx: "Any | None" = None,
    exploit_validator: "Any | None" = None,
) -> list[Finding]:
    """Drive every scanner end-to-end as it completes; return fresh findings."""
    workers = [
        asyncio.create_task(
            _process_scanner(
                task=task,
                scanner_name=name,
                scan_id=scan_id,
                request=request,
                step=step,
                audit=audit,
                events=events,
                persistence=persistence,
                graph=graph,
                fp_classifier=fp_classifier,
                triage=triage,
                dedup=dedup,
                epss_kev=epss_kev,
                attack_mapper=attack_mapper,
                vex=vex,
                reachability=reachability,
                risk_scorer=risk_scorer,
                compliance=compliance,
                osv=osv,
                greynoise=greynoise,
                webhook=webhook,
                validated_only=validated_only,
                validated_min_cvss=validated_min_cvss,
                virustotal=virustotal,
                shodan=shodan,
                censys=censys,
                otx=otx,
                exploit_validator=exploit_validator,
            ),
            name=f"scanner-pipeline:{name}",
        )
        for task, name in pending.items()
    ]
    results = await asyncio.gather(*workers, return_exceptions=True)
    all_fresh: list[Finding] = []
    for r in results:
        if isinstance(r, asyncio.CancelledError):
            raise r
        if isinstance(r, BaseException):
            _logger.warning(
                "red_agent.scanner_pipeline_failed",
                extra={"scan_id": str(scan_id), "err": str(r)},
            )
            continue
        all_fresh.extend(r)
    return all_fresh


async def _process_scanner(
    *,
    task: asyncio.Task[list[Finding]],
    scanner_name: str,
    scan_id: UUID,
    request: "ScanRequest",
    step: "PlannerStep",
    audit: "AuditLogger",
    events: "ScanEventBus",
    persistence: "RedAgentPersistence",
    graph: "VulnerabilityGraph",
    fp_classifier: "FPClassifierService | None",
    triage: "LLMTriageService | None",
    dedup: "SemanticDedupService | None",
    epss_kev: "EpssKevEnricher | None",
    attack_mapper: "AttackMapperEnricher | None",
    vex: "VexEnricher | None",
    reachability: "ReachabilityEnricher | None",
    risk_scorer: "RiskScoringEnricher | None",
    compliance: "ComplianceMapperEnricher | None",
    osv: "OSVEnricher | None",
    greynoise: "GreyNoiseEnricher | None",
    webhook: "WebhookNotifier | None",
    validated_only: bool,
    validated_min_cvss: float,
    virustotal: "Any | None" = None,
    shodan: "Any | None" = None,
    censys: "Any | None" = None,
    otx: "Any | None" = None,
    exploit_validator: "Any | None" = None,
) -> list[Finding]:
    """Full per-scanner pipeline: await task, enrich, persist, publish."""
    try:
        scanner_findings = await task
    except asyncio.CancelledError:
        raise
    except BaseException as err:
        _logger.warning(
            "scanner failure",
            extra={"scanner": scanner_name, "err": str(err)},
        )
        await audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.scanner_failed",
            payload={
                "scanner": scanner_name,
                "error": str(err)[:500],
                "type": type(err).__name__,
            },
        )
        scanner_findings = [
            scanner_error_finding(
                scanner_name=scanner_name,
                target=step.target.value,
                err=err,
            )
        ]

    fresh, dups = await run_post_scanner_pipeline(
        scanner_findings=scanner_findings,
        fp_classifier=fp_classifier,
        triage=triage,
        dedup=dedup,
        audit=audit,
        scan_id=scan_id,
        request=request,
        step=step,
        validated_only=validated_only,
        validated_min_cvss=validated_min_cvss,
        epss_kev=epss_kev,
        attack_mapper=attack_mapper,
        vex=vex,
        reachability=reachability,
        risk_scorer=risk_scorer,
        compliance=compliance,
        osv=osv,
        greynoise=greynoise,
        virustotal=virustotal,
        shodan=shodan,
        censys=censys,
        otx=otx,
        exploit_validator=exploit_validator,
    )

    if fresh:
        await asyncio.gather(
            *(asyncio.to_thread(graph.upsert_finding, scan_id, f) for f in fresh)
        )
        await persistence.insert_findings(scan_id, fresh)
        if webhook is not None and webhook.enabled:
            try:
                await webhook.notify(
                    fresh, scan_id=scan_id, tenant_id=request.tenant_id
                )
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "red_agent.webhook.notify_failed",
                    extra={"scan_id": str(scan_id), "err": str(exc)},
                )

    publish_coros: list[Any] = [
        events.publish(
            scan_id, {"type": "finding", "finding": f.model_dump(mode="json")}
        )
        for f in fresh
    ]
    publish_coros.extend(
        events.publish(
            scan_id,
            {
                "type": "finding_duplicate",
                "duplicate_of": (
                    d.evidence.get("duplicate_of")
                    if isinstance(d.evidence, dict)
                    else None
                ),
                "finding": d.model_dump(mode="json"),
            },
        )
        for d in dups
    )
    publish_coros.append(
        audit.record(
            scan_id=scan_id,
            actor="red_agent",
            event="scan.scanner_finished",
            payload={"scanner": scanner_name, "findings": len(scanner_findings)},
        )
    )
    await asyncio.gather(*publish_coros)
    return fresh
