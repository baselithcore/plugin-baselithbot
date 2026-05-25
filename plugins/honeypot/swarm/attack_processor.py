"""Attack processing mixin for HoneypotSwarmCoordinator.

Handles attack event processing, session management, statistics updates,
and analysis task submission.
"""

import asyncio
from contextlib import nullcontext
from typing import TYPE_CHECKING, Optional, Any, List

from core.observability.logging import get_logger
from core.observability.tracing import get_tracer

from ..models import AttackEvent, AttackSeverity
from .utils import geo, sensibility, analysis, session, stats

logger = get_logger(__name__)
tracer = get_tracer(__name__)


if TYPE_CHECKING:
    from .coordinator import HoneypotSwarmCoordinator


class AttackProcessorMixin:
    """Mixin providing attack event processing capabilities."""

    async def _process_attack_with_honeypot(
        self: "HoneypotSwarmCoordinator", event: AttackEvent, honeypot_id: str
    ) -> None:
        """Process attack event with honeypot ID tracking."""
        event.honeypot_id = honeypot_id
        await self.process_attack(event)

    @tracer.traced(name="process_attack_batch")
    async def process_batch(self, batch: List[Any]):
        """Process a batch of attack events."""
        # This method is a placeholder for batch processing logic.
        # Actual implementation would iterate through the batch and process each event.
        for item in batch:
            logger.debug(f"Processing batch item: {item}")
        pass  # Placeholder for actual batch processing logic

    async def process_attack(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Process an incoming attack event.

        Args:
            event: Attack event to process
        """
        print(
            f"[DEBUG] AttackProcessor.process_attack called for event: {event.event_id}",
            flush=True,
        )

        # Add to tracing span if observability enabled
        tracer = self._get_tracer()
        with tracer.start_span("honeypot.process_attack") if tracer else nullcontext():
            # Store event (deque handles maxlen automatically)
            self._events.append(event)

            # HoneyDOC: Feed event to CaptorManager for unified data capture
            self._captor_manager.data_capture.capture_network_event(event)

            # Update session - moved to background for non-blocking processing
            # This reduces fast-path latency from ~20ms to <1ms
            asyncio.create_task(self._update_session(event))

            # Fast Path: Broadcast raw event immediately for terminal/UI responsiveness
            try:
                from ..stream import get_stream_manager

                stream_manager = get_stream_manager()
                # Broadcast raw event (no Geo yet)
                # Frontend handles updates via checking event ID
                asyncio.create_task(stream_manager.broadcast(event))
            except Exception as e:
                logger.error(f"Failed to broadcast fast-path event: {e}")

            # Slow Path: Background heavy enrichment and processing
            asyncio.create_task(self._process_heavy_attack_tasks(event))

    async def _process_heavy_attack_tasks(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Process heavy tasks (Geo, AI, Persistence) in background."""
        try:
            from ..events import AttackEventData, HoneypotEvents, emit_honeypot_event

            # Enrich event with geo data for visualization (External API calls)
            await self._enrich_event_with_geo(event)

            # CVE Correlation: Enrich events with CVE tags from honeypot definitions
            # This applies CVE tags (e.g., "cve-2024-21762") from the honeypot's YAML config
            await self._correlate_event_cves(event)

            # HoneyDOC Sensibility: Classify traffic and determine flow action
            flow_action = await self._apply_sensibility(event)

            # Handle flow action (per HoneyDOC Section IV-C2)
            if flow_action == "drop":
                logger.info(f"Dropping event {event.event_id} per classification")
                self._add_discovery_log(
                    f"[DROPPED] Traffic from {event.source_ip} dropped by rule",
                    is_alert=True,
                )
                return  # Stop processing

            elif flow_action == "redirect":
                # Redirect session to HIH or another honeypot
                target_honeypot = self.config.redirect_hih_honeypot or "hih-ubuntu"
                self._captor_manager.flow_controller.redirect_session(
                    session_id=event.session_id,
                    from_honeypot=event.honeypot_id or "unknown",
                    to_honeypot=target_honeypot,
                    reason="Redirecting per classification rule",
                )
                logger.info(
                    f"Redirected session {event.session_id} to {target_honeypot}"
                )
                # HoneyDOC: Continue processing to log the event, but marked as redirected
                event.honeypot_id = target_honeypot

            elif flow_action == "contain":
                # Contain session (restrict outbound)
                self._captor_manager.flow_controller.contain_session(
                    session_id=event.session_id,
                    reason="Containment per classification rule",
                )
                logger.info(f"Contained session {event.session_id}")

            # Parallelize independent post-processing tasks
            tasks = []

            # 1. Update IP reputation
            if self._memory:
                tasks.append(
                    self._memory.update_ip_reputation(
                        ip=event.source_ip,
                        event_count=1,
                        severity=event.severity.value,
                        categories=[event.category.value] if event.category else None,
                    )
                )

            # 2. Emit attack event (Internal EventBus)
            tasks.append(
                emit_honeypot_event(
                    HoneypotEvents.ATTACK_DETECTED,
                    AttackEventData(
                        event_id=event.event_id,
                        session_id=event.session_id,
                        honeypot_id=event.honeypot_id,
                        protocol=event.protocol.value,
                        source_ip=event.source_ip,
                        source_port=event.source_port,
                        category=event.category.value,
                        severity=event.severity.value,
                        detected_patterns=event.detected_patterns,
                        raw_data=event.raw_data,
                        command=event.command,
                        http_path=event.http_path,
                        geo=event.geo.model_dump() if event.geo else {},
                    ).to_dict(),
                )
            )

            # 3. Submit analysis task (if high severity AND auto-analysis enabled)
            if (
                event.severity in (AttackSeverity.HIGH, AttackSeverity.CRITICAL)
                and self.config.auto_analyze_critical_events
            ):
                tasks.append(self._submit_analysis_task(event))

            # 4. Deposit pheromone (if high activity)
            try:
                if self._is_high_activity_ip(event.source_ip) and self._colony:
                    # Use PheromoneSystem via colony.pheromones
                    agent = self._agent_profiles.get("decoy_manager")
                    agent_id = agent.agent_id if agent else "coordinator"

                    self._colony.pheromones.deposit(
                        ptype="honeypot.attack_hotspot",
                        location=event.source_ip,
                        intensity=0.8,
                        agent_id=agent_id,
                    )
            except Exception as e:
                logger.error(
                    f"Failed to check high activity IP or deposit pheromone: {e}"
                )

            # 5. Broadcast to stream (ENRICHED update)
            try:
                from ..stream import get_stream_manager

                stream_manager = get_stream_manager()
                tasks.append(stream_manager.broadcast(event))
            except Exception:
                pass  # nosec B110

            # 6. Persist to DB using batch service (5-10x more efficient)
            try:
                from ..persistence import save_event_batched

                tasks.append(save_event_batched(event))
            except Exception as e:
                logger.error(
                    f"Failed to schedule event persistence for {event.event_id}: {e}"
                )
                # nosec B110

            # Execute all tasks concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Log any exceptions from background tasks
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Background task {i} failed for event {event.event_id}: {result}"
                        )

            # Update statistics (sync)
            self._update_stats(event)

            # Log discovery with normalized IP display
            from ..utils import normalize_ip_display

            display_ip = normalize_ip_display(event.source_ip)
            country_code = event.geo.country_code if event.geo else None
            self._add_discovery_log(
                f"[{event.protocol.value.upper()}] Attack from {display_ip}: "
                f"{event.category.value} ({event.severity.value})",
                is_alert=event.severity
                in (AttackSeverity.HIGH, AttackSeverity.CRITICAL),
                country_code=country_code,
                source_ip=event.source_ip,
            )

        except Exception as e:
            logger.error(f"Error in background attack processing: {e}")

    async def _update_session(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Update or create session for event."""
        await session.update_session(self, event)

    def _is_high_activity_ip(self: "HoneypotSwarmCoordinator", ip: str) -> bool:
        """Check if IP has high recent activity."""
        return stats.is_high_activity_ip(self, ip)

    async def _submit_analysis_task(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Submit analysis task to colony."""
        await analysis.submit_analysis_task(self, event)

    def _update_stats(self: "HoneypotSwarmCoordinator", event: AttackEvent) -> None:
        """Update statistics from event."""
        stats.update_stats(self, event)

    def _add_discovery_log(
        self: "HoneypotSwarmCoordinator",
        message: str,
        is_alert: bool = False,
        is_error: bool = False,
        country_code: str = None,
        source_ip: str = None,
    ) -> None:
        """Add a discovery log entry."""
        stats.add_discovery_log(
            self, message, is_alert, is_error, country_code, source_ip
        )

    def _get_tracer(self: "HoneypotSwarmCoordinator"):
        """Get observability tracer if available."""
        try:
            from core.observability import get_tracer

            return get_tracer("honeypot")
        except Exception:
            return None

    async def _enrich_event_with_geo(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Enrich attack event with geographic location data."""
        await geo.enrich_event_with_geo(event)

    async def _apply_sensibility(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> str:
        """Apply HoneyDOC Sensibility classification to event."""
        return await sensibility.apply_sensibility(self, event)

    async def _check_auto_block(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Check if IP should be auto-blocked based on activity."""
        await sensibility.check_auto_block(self, event)

    async def analyze_event(
        self: "HoneypotSwarmCoordinator", event_id: str
    ) -> Optional[dict]:
        """Analyze attack event on demand using AI."""
        return await analysis.analyze_event(self, event_id)

    async def _correlate_event_cves(
        self: "HoneypotSwarmCoordinator", event: AttackEvent
    ) -> None:
        """Correlate attack event with CVEs based on honeypot tags.

        This enriches events with matched CVEs by:
        1. Fetching the honeypot definition to get CVE tags (e.g., "cve-2024-21762")
        2. Calling the CVE correlator with those tags
        3. Updating the event with matched CVEs and CWEs

        This ensures that ANY event from a CVE-tagged honeypot gets the CVE correlation,
        not just events that match specific exploit patterns.
        """
        # Skip if event already has CVEs (set by custom handlers)
        if event.matched_cves:
            logger.debug(
                f"Event {event.event_id} already has CVEs: {event.matched_cves}"
            )
            return

        # Skip if CVE correlation is disabled
        if not self.config.enable_cve_correlation:
            return

        # Skip if no honeypot_id
        if not event.honeypot_id:
            return

        try:
            # Get honeypot definition to fetch CVE tags
            honeypot = await self.get_honeypot(event.honeypot_id)
            if not honeypot:
                logger.debug(f"Honeypot {event.honeypot_id} not found in registry")
                return

            # Extract CVE tags (format: "cve-2024-21762")
            cve_tags = [
                tag for tag in (honeypot.tags or []) if tag.lower().startswith("cve-")
            ]

            if not cve_tags:
                logger.debug(f"Honeypot {event.honeypot_id} has no CVE tags")
                return

            # Call correlator with honeypot tags
            correlation = await self._cve_correlator.correlate_attack(
                event_id=event.event_id,
                category=event.category.value if event.category else "unknown",
                patterns=list(event.detected_patterns)
                if event.detected_patterns
                else [],
                source_ip=event.source_ip,
                honeypot_tags=cve_tags,
            )

            if correlation:
                # Update event with matched CVEs
                event.matched_cves = correlation.get("matched_cves", [])
                event.matched_cwes = correlation.get("matched_cwes", [])
                logger.info(
                    f"CVE correlation for {event.event_id}: {event.matched_cves} "
                    f"(honeypot: {event.honeypot_id})"
                )

        except Exception as e:
            logger.error(f"CVE correlation failed for {event.event_id}: {e}")
