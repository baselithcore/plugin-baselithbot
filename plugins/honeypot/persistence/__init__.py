"""
Honeypot Persistence Layer.

Handles saving events and sessions to the dedicated Analytics PostgreSQL database.
Manages its own connection logic to avoid modifying the core.

Refactored into a modular package structure.
"""

from .schema import ensure_schema
from .events import (
    save_event,
    get_events,
    get_event_by_id,
    get_recent_events,
    delete_events_by_ip,
    delete_event_by_id,
)
from .batch_service import (
    save_event_batched,
    get_batcher,
    shutdown_batcher,
)
from .optimization import (
    optimize_for_scale,
    archive_old_events,
    get_table_stats,
    create_archive_table,
    optimize_indexes,
)
from .attackers import (
    get_unique_attackers,
    get_attackers_count,
    AttackerInfo,
)
from .sessions import (
    save_session,
    get_sessions,
    get_session_by_id,
    delete_sessions_by_ip,
    delete_session_by_id,
)
from .stats import get_stats
from .database import init_pool, get_connection, close_pool
from .retention import apply_retention_policy, get_retention_status
from .timeseries import get_timeseries, get_trends
from .aggregations import get_top_attackers, get_attack_heatmap, get_cve_trends


from .discovery import save_discovery_result, get_latest_discovery_result


class HoneypotDAO:
    """Data Access Object for Honeypot analytics.

    Acts as a facade for the modularized persistence layer.
    """

    ensure_schema = staticmethod(ensure_schema)
    save_event = staticmethod(save_event)
    save_event_batched = staticmethod(save_event_batched)
    get_events = staticmethod(get_events)
    get_event_by_id = staticmethod(get_event_by_id)
    get_recent_events = staticmethod(get_recent_events)
    delete_events_by_ip = staticmethod(delete_events_by_ip)
    delete_event_by_id = staticmethod(delete_event_by_id)
    save_session = staticmethod(save_session)
    get_sessions = staticmethod(get_sessions)
    get_session_by_id = staticmethod(get_session_by_id)
    delete_sessions_by_ip = staticmethod(delete_sessions_by_ip)
    delete_session_by_id = staticmethod(delete_session_by_id)
    get_unique_attackers = staticmethod(get_unique_attackers)
    get_attackers_count = staticmethod(get_attackers_count)
    get_stats = staticmethod(get_stats)
    init_pool = staticmethod(init_pool)
    get_connection = staticmethod(get_connection)
    close_pool = staticmethod(close_pool)
    save_discovery_result = staticmethod(save_discovery_result)
    get_latest_discovery_result = staticmethod(get_latest_discovery_result)
    shutdown_batcher = staticmethod(shutdown_batcher)
    optimize_for_scale = staticmethod(optimize_for_scale)
    archive_old_events = staticmethod(archive_old_events)
    get_table_stats = staticmethod(get_table_stats)
    apply_retention_policy = staticmethod(apply_retention_policy)
    get_retention_status = staticmethod(get_retention_status)
    get_timeseries = staticmethod(get_timeseries)
    get_trends = staticmethod(get_trends)
    get_top_attackers = staticmethod(get_top_attackers)
    get_attack_heatmap = staticmethod(get_attack_heatmap)
    get_cve_trends = staticmethod(get_cve_trends)


__all__ = [
    "HoneypotDAO",
    "ensure_schema",
    "save_event",
    "save_event_batched",
    "get_events",
    "get_event_by_id",
    "get_recent_events",
    "delete_events_by_ip",
    "delete_event_by_id",
    "get_unique_attackers",
    "get_attackers_count",
    "AttackerInfo",
    "save_session",
    "get_sessions",
    "get_session_by_id",
    "delete_sessions_by_ip",
    "delete_session_by_id",
    "get_stats",
    "init_pool",
    "get_connection",
    "close_pool",
    "save_discovery_result",
    "get_latest_discovery_result",
    "get_batcher",
    "shutdown_batcher",
    "optimize_for_scale",
    "archive_old_events",
    "get_table_stats",
    "create_archive_table",
    "optimize_indexes",
    "apply_retention_policy",
    "get_retention_status",
    "get_timeseries",
    "get_trends",
    "get_top_attackers",
    "get_attack_heatmap",
    "get_cve_trends",
]
