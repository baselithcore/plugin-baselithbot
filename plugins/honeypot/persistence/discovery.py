"""
Discovery persistence logic.
"""

import json
from core.observability.logging import get_logger
from typing import Optional

from plugins.honeypot.discovery.models import DiscoveryResult
from .database import get_connection

logger = get_logger(__name__)


async def save_discovery_result(result: DiscoveryResult) -> None:
    """Save a discovery analysis result."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO discovery_results (
                        analysis_id, honeypot_id, analyzed_at, result_json
                    ) VALUES (
                        %(analysis_id)s, %(honeypot_id)s, %(analyzed_at)s, %(result_json)s
                    )
                    ON CONFLICT (analysis_id) DO UPDATE SET
                        analyzed_at = EXCLUDED.analyzed_at,
                        result_json = EXCLUDED.result_json
                    """,
                    {
                        "analysis_id": result.analysis_id,
                        "honeypot_id": result.honeypot_id,
                        "analyzed_at": result.analyzed_at,
                        "result_json": json.dumps(result.model_dump(mode="json")),
                    },
                )
    except Exception as e:
        logger.error(f"Failed to save discovery result {result.analysis_id}: {e}")


async def get_latest_discovery_result(
    honeypot_id: Optional[str] = None,
) -> Optional[DiscoveryResult]:
    """Get the latest discovery result, optionally filtered by honeypot_id."""
    try:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                conditions = []
                params = {}

                if honeypot_id:
                    conditions.append("honeypot_id = %(honeypot_id)s")
                    params["honeypot_id"] = honeypot_id

                # If no honeypot_id specified, we prefer global analysis (honeypot_id IS NULL)
                # or just the latest overall if we don't strictly separate them.
                # Use strict matching if honeypot_id is None to find global results?
                # Or just allow any?
                # Let's assume if honeypot_id is None, we want any latest result or global result.
                # For now, simplistic approach: simple filter if provided.

                query_parts = ["SELECT result_json", "FROM discovery_results"]
                if conditions:
                    query_parts.append("WHERE " + " AND ".join(conditions))
                query_parts.append("ORDER BY analyzed_at DESC")
                query_parts.append("LIMIT 1")

                query = "\n".join(query_parts)

                await cur.execute(query, params)
                row = await cur.fetchone()

                if not row:
                    return None

                result_json = row[0]
                # Ensure date strings are parsed back to datetime if needed,
                # but Pydantic model validation should handle it from dict/json.
                return DiscoveryResult(**result_json)

    except Exception as e:
        logger.error(f"Failed to get latest discovery result: {e}")
        return None
