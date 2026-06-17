"""Sequential analysis (Kill Chain) mixin for ReportDataAggregator."""

from datetime import datetime, timezone
from typing import List, Optional

from ..models import AttackSessionAnalysis, AttackStep

from core.observability.logging import get_logger

logger = get_logger(__name__)


class SequentialAnalysisMixin:
    """Mixin providing build_sequential_analysis method."""

    async def build_sequential_analysis(
        self,
        honeypot_id: Optional[str],
        time_start: datetime,
        limit: int = 5,
    ) -> List[AttackSessionAnalysis]:
        """Build sequential analysis (Kill Chain) for top critical sessions.

        Args:
            honeypot_id: Optional honeypot filter
            time_start: Time range start
            limit: Max number of sessions to analyze (strict limit for performance)

        Returns:
            List of AttackSessionAnalysis

        Security:
            Payloads are sanitized using sanitize_for_llm.
        """
        try:
            from ..security import sanitize_for_llm

            # 1. Get top critical/high sessions
            # We want sessions that are "interesting" - likely those with payloads or many events
            sessions, _ = await self.dao.get_sessions(
                honeypot_id=honeypot_id,
                page_size=limit,
                active_only=False,
            )
            # Filter specifically for sessions with high severity actions if getting generic sessions
            # But get_sessions default sort is by time.
            # Ideally we want sessions with severity='critical' or 'high'
            # The get_sessions doesn't support severity filter directly yet, but we can filter in memory or fetch by events.
            # A better approach (for v1) -> fetch top critical events, pick unique session_ids, fetch those sessions.

            # Re-strategy: Get critical events first to find interesting session IDs
            critical_events, _ = await self.dao.get_events(
                honeypot_id=honeypot_id,
                page_size=50,
                severity="critical",
            )

            interesting_session_ids = list(
                set([e.session_id for e in critical_events])
            )[:limit]

            # If no critical, try high
            if not interesting_session_ids:
                high_events, _ = await self.dao.get_events(
                    honeypot_id=honeypot_id,
                    page_size=50,
                    severity="high",
                )
                interesting_session_ids = list(
                    set([e.session_id for e in high_events])
                )[:limit]

            # If still nothing, fallback to recent sessions
            if not interesting_session_ids:
                sessions, _ = await self.dao.get_sessions(
                    honeypot_id=honeypot_id, page_size=limit
                )
                interesting_session_ids = [s.session_id for s in sessions]

            results = []

            for session_id in interesting_session_ids:
                # Get session details
                session = await self.dao.get_session_by_id(session_id)
                if not session:
                    continue

                # Get ALL events for this session, ordered by time
                # We need a method in DAO to get events by session_id, or use get_events with filter
                # get_events doesn't have session_id filter.
                # Adding a direct query here or using existing filters if possible.
                # Actually, the DAO's get_events is generic. Let's add session_id support if missing or query directly.
                # Checking DAO signature... get_events arguments are limited.
                # However, we can use the `get_session_by_id` which might link events, or just query events table directly here
                # to avoid modifying DAO for now (Project Rule: Modular > Refactor).

                async with self.dao.get_connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            SELECT timestamp, event_type, category, severity, raw_data, ai_classification
                            FROM honeypot_events
                            WHERE session_id = %(session_id)s
                            ORDER BY timestamp ASC
                            LIMIT 100
                            """,  # Limit steps to prevent context overflow
                            {"session_id": session_id},
                        )
                        events = await cur.fetchall()

                steps = []
                for row in events:
                    ts, evt_type, cat, sev, raw, ai_class = row

                    # Determine phase based on category/type
                    phase = "Execution"  # Default
                    if cat == "reconnaissance" or evt_type == "connection":
                        phase = "Reconnaissance"
                    elif cat == "auth_attempt" or evt_type == "auth":
                        phase = "Initial Access"
                    elif cat in ["command_injection", "rce"]:
                        phase = "Exploitation"

                    # Sanitize payload if present
                    payload_snippet = None
                    if raw and len(raw) > 3:
                        payload_snippet = sanitize_for_llm(
                            raw[:200],  # Keep it short for the step list
                            max_length=200,
                            replacement="[FILTERED]",
                        )

                    desc = ai_class or f"Executed {evt_type}"
                    if raw and not ai_class:
                        desc = f"{evt_type}: {raw[:50]}..."

                    steps.append(
                        AttackStep(
                            timestamp=ts
                            if ts.tzinfo
                            else ts.replace(tzinfo=timezone.utc),
                            phase=phase,
                            description=desc,
                            payload_snippet=payload_snippet,
                            severity=str(sev),
                        )
                    )

                if steps:
                    results.append(
                        AttackSessionAnalysis(
                            session_id=session_id,
                            attacker_ip=session.source_ip,
                            steps=steps,
                            narrative=None,  # To be filled by LLM
                        )
                    )

            return results

        except Exception as e:
            logger.error(f"Failed to build sequential analysis: {e}")
            return []
