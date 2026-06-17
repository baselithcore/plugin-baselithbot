"""CLI bridge services: surface ``baselith`` CLI capabilities in the dashboard.

The framework CLI's importable functions and ``core`` getters are reused here
and re-shaped onto the wire DTOs in :mod:`plugins.baselithcontrol.cli_models`.
"""

from __future__ import annotations

from .diagnostics import config_report, doctor, info, verify
from .infra import cache_clear, cache_stats, db_reset, db_status, queue_status
from .jobs import JobManager, get_job_manager

__all__ = [
    "doctor",
    "verify",
    "info",
    "config_report",
    "db_status",
    "cache_stats",
    "cache_clear",
    "db_reset",
    "queue_status",
    "JobManager",
    "get_job_manager",
]
