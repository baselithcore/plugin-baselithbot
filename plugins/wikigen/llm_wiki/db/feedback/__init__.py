"""Feedback persistence package.

Split del legacy ``llm_wiki/db/feedback.py`` lungo seam funzionali per
restare entro il cap 500 LOC dopo l'aggiunta del workflow triage
(mig 018) e del source-correlation KPI:

- :mod:`._format` — shaping + costanti di vocabolario (status, tag).
- :mod:`._crud`   — write/list/get/delete + update_triage.
- :mod:`._stats`  — aggregati dashboard (KPI, trend, anomaly,
  per-source breakdown).

API pubblica re-esportata qui per backward-compat: tutti i call site
esistenti (router feedback, router feedback_admin, conftest fixtures)
importano da ``llm_wiki.db.feedback`` senza modifiche.
"""

from __future__ import annotations

from ._crud import (
    delete_feedback,
    get_feedback_by_id,
    list_feedback,
    list_feedback_admin,
    update_triage,
    write_feedback,
)
from ._format import ALLOWED_STATUSES, SUGGESTED_TAGS, format_feedback, normalize_tags
from ._stats import feedback_source_stats, feedback_stats

__all__ = [
    "ALLOWED_STATUSES",
    "SUGGESTED_TAGS",
    "delete_feedback",
    "feedback_source_stats",
    "feedback_stats",
    "format_feedback",
    "get_feedback_by_id",
    "list_feedback",
    "list_feedback_admin",
    "normalize_tags",
    "update_triage",
    "write_feedback",
]
