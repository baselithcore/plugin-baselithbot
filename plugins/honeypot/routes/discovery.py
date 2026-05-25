"""Discovery API Routes.

Endpoints for botnet detection and network discovery analysis.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import AuthRole
from plugins.auth.dependencies import require_roles

from ..discovery import DiscoveryService
from ..discovery.models import (
    BotnetCluster,
    DiscoveryGraphData,
    DiscoveryResult,
    HubNode,
    NetworkAnomaly,
    convert_numpy,
)
from ..persistence import HoneypotDAO
from ..discovery.rdns import (
    RDNSEnrichmentResponse,
    get_rdns_resolver,
)
from ..persistence.attackers import get_unique_attackers

router = APIRouter(
    prefix="/discovery",
    tags=["discovery"],
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.USER))],
)

# Service instance (will be properly initialized with DI in production)
_service: Optional[DiscoveryService] = None


def get_service() -> DiscoveryService:
    """Get or create discovery service instance."""
    global _service
    if _service is None:
        dao = HoneypotDAO()
        _service = DiscoveryService(dao=dao)
    return _service


@router.post("/analyze", response_model=DiscoveryResult)
async def run_discovery_analysis(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
    time_window_hours: int = Query(
        168, ge=1, le=168, description="Time window in hours"
    ),
    min_cluster_size: int = Query(2, ge=2, le=10, description="Minimum cluster size"),
    resolution: float = Query(1.0, ge=0.1, le=3.0, description="Louvain resolution"),
) -> DiscoveryResult:
    """Run full discovery analysis.

    Analyzes attack data to detect botnets, C&C servers, and network anomalies.
    """
    try:
        service = get_service()
        result = await service.run_full_analysis(
            honeypot_id=honeypot_id,
            time_window_hours=time_window_hours,
            min_cluster_size=min_cluster_size,
            resolution=resolution,
        )
        return result
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Discovery service unavailable: {str(e)}. Install networkx and python-louvain.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/result", response_model=DiscoveryResult)
async def get_discovery_result(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
) -> DiscoveryResult:
    """Get cached discovery result without running new analysis.

    Returns the last analysis result from memory or database cache.
    Use this for fast loading; use POST /analyze to trigger fresh analysis.
    """
    try:
        service = get_service()
        result = await service.get_last_result(honeypot_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="No analysis available. Run POST /analyze first.",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/botnets", response_model=list[BotnetCluster])
async def get_detected_botnets(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
) -> list[BotnetCluster]:
    """Get detected botnet clusters.

    Returns cached results if available, otherwise runs new analysis.
    """
    try:
        service = get_service()
        botnets = await service.detect_botnets(honeypot_id=honeypot_id)
        return botnets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hubs", response_model=list[HubNode])
async def get_hub_nodes(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
) -> list[HubNode]:
    """Get potential C&C servers (hub nodes).

    Returns nodes with high centrality that may be command-and-control servers.
    """
    try:
        service = get_service()
        hubs = await service.find_hub_nodes(honeypot_id=honeypot_id)
        return hubs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_graph_data(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
) -> Optional[DiscoveryGraphData]:
    """Get network graph data for visualization.

    Returns nodes and edges with cluster assignments for rendering.
    """
    try:
        service = get_service()
        graph_data = await service.get_network_graph_data(honeypot_id=honeypot_id)
        return graph_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies", response_model=list[NetworkAnomaly])
async def get_anomalies(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
) -> list[NetworkAnomaly]:
    """Get detected network anomalies.

    Returns unusual patterns like geographic clustering or timing synchronization.
    """
    try:
        service = get_service()
        result = await service.run_full_analysis(honeypot_id=honeypot_id)
        return result.anomalies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_analysis_summary(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
) -> dict:
    """Get summary of last discovery analysis.

    Provides quick stats without running new analysis.
    """
    service = get_service()
    last_result = await service.get_last_result(honeypot_id)

    if last_result is None:
        return {
            "status": "no_analysis",
            "message": "No analysis has been run yet. Call POST /analyze first.",
        }

    # Apply convert_numpy to ensure all numpy types are serializable
    return convert_numpy(
        {
            "status": "available",
            "analysis_id": last_result.analysis_id,
            "analyzed_at": last_result.analyzed_at.isoformat(),
            "honeypot_id": last_result.honeypot_id,
            **last_result.summary,
        }
    )


# ============================================================================
# Honeypot Suggestion Endpoints
# ============================================================================


@router.get("/suggestions")
async def get_suggestions(
    include_dismissed: bool = Query(False, description="Include dismissed suggestions"),
) -> dict:
    """Get honeypot suggestions from last analysis.

    Returns suggestions for custom honeypots based on detected attack patterns.
    """
    service = get_service()
    last_result = await service.get_last_result()

    if last_result is None:
        return {
            "suggestions": [],
            "total": 0,
            "message": "No analysis has been run yet. Run analysis first.",
        }

    suggestions = last_result.suggestions or []

    # Filter dismissed if not requested
    if not include_dismissed:
        suggestions = [s for s in suggestions if not s.get("dismissed", False)]

    # Calculate summary stats
    by_priority = {}
    by_type = {}
    for s in suggestions:
        priority = s.get("priority", "medium")
        stype = s.get("suggestion_type", "unknown")
        by_priority[priority] = by_priority.get(priority, 0) + 1
        by_type[stype] = by_type.get(stype, 0) + 1

    return convert_numpy(
        {
            "suggestions": suggestions,
            "total": len(suggestions),
            "by_priority": by_priority,
            "by_type": by_type,
        }
    )


@router.get("/suggestions/{suggestion_id}")
async def get_suggestion_by_id(suggestion_id: str) -> dict:
    """Get a specific suggestion by ID."""
    service = get_service()
    last_result = await service.get_last_result()

    if last_result is None or not last_result.suggestions:
        raise HTTPException(status_code=404, detail="No suggestions available")

    for suggestion in last_result.suggestions:
        if suggestion.get("id") == suggestion_id:
            return convert_numpy(suggestion)

    raise HTTPException(status_code=404, detail="Suggestion not found")


@router.get("/suggestions/{suggestion_id}/yaml")
async def get_suggestion_yaml(suggestion_id: str) -> dict:
    """Get YAML configuration for a suggestion.

    Returns the honeypot YAML definition that would be created from this suggestion.
    """
    import yaml

    service = get_service()
    last_result = await service.get_last_result()

    if last_result is None or not last_result.suggestions:
        raise HTTPException(status_code=404, detail="No suggestions available")

    for suggestion in last_result.suggestions:
        if suggestion.get("id") == suggestion_id:
            # Build YAML config from suggestion
            title = suggestion.get("title", "Suggested Honeypot")
            slug = title.lower().replace(" ", "-")[:50]

            config = {
                "id": f"suggested-{slug}",
                "name": title,
                "description": suggestion.get("description", ""),
                "protocol": suggestion.get("suggested_protocol", "http"),
                "port": suggestion.get("suggested_port", 8080),
                "bind_address": "0.0.0.0",  # nosec B104
                "handler_type": "auto",
                "enabled": True,
                "priority": 5,
                "tags": suggestion.get("tags", ["suggested", "auto-generated"]),
                "detection": {
                    "log_all_requests": True,
                    "custom_patterns": suggestion.get("detection_patterns", []),
                },
                "response_mode": "static",
            }

            yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)

            return {
                "suggestion_id": suggestion_id,
                "yaml": yaml_content,
                "config": convert_numpy(config),
            }

    raise HTTPException(status_code=404, detail="Suggestion not found")


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(suggestion_id: str) -> dict:
    """Dismiss a suggestion.

    Marks a suggestion as dismissed so it won't appear in future listings.
    """
    service = get_service()
    last_result = await service.get_last_result()

    if last_result is None or not last_result.suggestions:
        raise HTTPException(status_code=404, detail="No suggestions available")

    for suggestion in last_result.suggestions:
        if suggestion.get("id") == suggestion_id:
            suggestion["dismissed"] = True
            return {"status": "dismissed", "suggestion_id": suggestion_id}

    raise HTTPException(status_code=404, detail="Suggestion not found")


@router.get("/rdns", response_model=RDNSEnrichmentResponse)
async def get_rdns_enrichment(
    honeypot_id: Optional[str] = Query(None, description="Filter by honeypot ID"),
    min_importance: str = Query(
        "low", description="Minimum importance level (high, medium, low)"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results to return"),
) -> RDNSEnrichmentResponse:
    """Get RDNS-enriched IP data with significance filtering.

    Resolves hostnames for intercepted IPs and scores their significance
    based on event count, ASN reputation, and exploit attempts.

    This endpoint is non-blocking and uses cached results when available.

    Args:
        honeypot_id: Optional filter by specific honeypot.
        min_importance: Minimum importance level to include (high, medium, low).
        limit: Maximum number of results to return.

    Returns:
        RDNSEnrichmentResponse with enriched IP data.
    """
    import time

    start_time = time.time()

    try:
        # Get unique attackers from database
        attackers = await get_unique_attackers(
            honeypot_id=honeypot_id,
            limit=limit * 2,  # Fetch extra to filter by importance
        )

        if not attackers:
            return RDNSEnrichmentResponse(
                results=[],
                total=0,
                resolved_count=0,
                cached_count=0,
                processing_time_ms=0,
            )

        # Get RDNS resolver
        resolver = get_rdns_resolver()

        # Filter valid IPs and prepare for batch resolution
        # Import validation function from rdns module
        from ..discovery.rdns import validate_ip_address

        valid_attackers = [a for a in attackers if validate_ip_address(a.ip)]
        invalid_attackers = [a for a in attackers if not validate_ip_address(a.ip)]

        # Log invalid IPs for debugging (common case: "unknown" IPs)
        if invalid_attackers:
            from core.observability.logging import get_logger

            get_logger(__name__).debug(
                f"Filtered out {len(invalid_attackers)} invalid IPs from RDNS resolution"
            )

        # Resolve valid IPs in batch
        ips = [a.ip for a in valid_attackers]
        rdns_results = await resolver.resolve_batch(ips) if ips else []

        # Build attacker lookup for enrichment
        attacker_map = {a.ip: a for a in valid_attackers}

        # Enrich results with significance scoring
        enriched_results = []
        cached_count = 0

        for rdns in rdns_results:
            if rdns.cached:
                cached_count += 1

            attacker = attacker_map.get(rdns.ip)
            if attacker:
                # Check for exploit attempts based on severity
                has_exploit = attacker.max_severity in ("critical", "high")

                enriched = resolver.enrich_result(
                    rdns_result=rdns,
                    event_count=attacker.event_count,
                    has_exploit_attempt=has_exploit,
                    asn=None,  # Could be fetched from geo data if available
                    org=None,
                    is_datacenter=False,
                    is_vpn=False,
                    is_proxy=False,
                )
                enriched_results.append(enriched)
            else:
                enriched_results.append(rdns)

        # Filter by minimum importance
        importance_order = {"high": 3, "medium": 2, "low": 1, "none": 0}
        min_level = importance_order.get(min_importance.lower(), 1)

        filtered_results = [
            r
            for r in enriched_results
            if importance_order.get(r.importance, 0) >= min_level
        ]

        # Sort by importance (high first) then by hostname presence
        filtered_results.sort(
            key=lambda r: (
                -importance_order.get(r.importance, 0),
                r.hostname is None,
            )
        )

        # Apply limit
        final_results = filtered_results[:limit]

        processing_time_ms = (time.time() - start_time) * 1000

        return RDNSEnrichmentResponse(
            results=final_results,
            total=len(filtered_results),
            resolved_count=sum(1 for r in final_results if r.hostname),
            cached_count=cached_count,
            processing_time_ms=round(processing_time_ms, 2),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RDNS enrichment failed: {str(e)}",
        )
