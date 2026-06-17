"""Prometheus metrics for the digital twin.

Counters are module-level singletons (the ``prometheus_client`` default registry
is shared process-wide, exactly as ``core/observability/metrics.py`` does), so
importing this module twice never re-registers a collector. Every metric is a
no-op unless ``prometheus_client`` is installed — guarded so the plugin stays
importable with the base dependency set.

Observed signals: drafts produced, governance decisions (auto vs queued vs
human), gateway sends (by result), and webhook deliveries (accepted / rejected /
duplicate). These make the twin's autonomy auditable on a dashboard.
"""

from __future__ import annotations

from typing import Any

_PREFIX = "baselith_twin"


def _noop_factory() -> Any:
    class _Noop:
        def labels(self, *_: Any, **__: Any) -> "_Noop":
            return self

        def inc(self, *_: Any, **__: Any) -> None:
            return None

    return _Noop()


try:  # pragma: no cover - exercised indirectly
    from prometheus_client import Counter

    DRAFTS_TOTAL = Counter(
        f"{_PREFIX}_drafts_total",
        "Reply drafts produced by the twin.",
        ["degraded"],
    )
    DECISIONS_TOTAL = Counter(
        f"{_PREFIX}_decisions_total",
        "Governance decisions for drafted replies.",
        ["decision"],  # auto_send | queue | approved | rejected
    )
    SENDS_TOTAL = Counter(
        f"{_PREFIX}_sends_total",
        "Gateway send attempts by result.",
        ["result"],  # ok | failed
    )
    WEBHOOKS_TOTAL = Counter(
        f"{_PREFIX}_webhooks_total",
        "Inbound webhook deliveries by outcome.",
        ["result"],  # accepted | rejected | duplicate
    )
except Exception:  # noqa: BLE001 — prometheus optional
    DRAFTS_TOTAL = _noop_factory()
    DECISIONS_TOTAL = _noop_factory()
    SENDS_TOTAL = _noop_factory()
    WEBHOOKS_TOTAL = _noop_factory()


__all__ = ["DRAFTS_TOTAL", "DECISIONS_TOTAL", "SENDS_TOTAL", "WEBHOOKS_TOTAL"]
