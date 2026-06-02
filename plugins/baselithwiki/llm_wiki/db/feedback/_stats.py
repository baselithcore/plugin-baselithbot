"""KPI aggregates per la dashboard admin feedback.

- ``feedback_stats``: totale, up/down, % positivo, trend bucketed, top
  question, status breakdown, anomaly (24h vs 7d baseline).
- ``feedback_source_stats``: per-document downvote rate — chiude il
  loop con il team che cura ingest/sources (quali documenti scatenano
  feedback negativi).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from llm_wiki import config
from llm_wiki.auth.tenant_context import require_tenant_id
from llm_wiki.db.connection import get_connection


def _empty_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "up": 0,
        "down": 0,
        "positive_rate": 0.0,
        "with_reason": 0,
        "unique_users": 0,
        "trend": [],
        "top_questions": [],
        "status_breakdown": {"open": 0, "triaged": 0, "resolved": 0, "dismissed": 0},
        "anomaly": None,
    }


def _anomaly_signal() -> dict[str, Any] | None:
    """Spike detection deterministica: down_rate 24h vs baseline 7d.

    Ritorna ``None`` se baseline ha pochi sample (< 10) per evitare
    falsi positivi su deploy giovani. Altrimenti ratio 24h / 7d-prev
    con label severity.
    """
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE rating = 'down'
                          AND created_at >= NOW() - INTERVAL '24 hours'
                    ) AS down_24h,
                    COUNT(*) FILTER (
                        WHERE created_at >= NOW() - INTERVAL '24 hours'
                    ) AS total_24h,
                    COUNT(*) FILTER (
                        WHERE rating = 'down'
                          AND created_at < NOW() - INTERVAL '24 hours'
                          AND created_at >= NOW() - INTERVAL '8 days'
                    ) AS down_prev,
                    COUNT(*) FILTER (
                        WHERE created_at < NOW() - INTERVAL '24 hours'
                          AND created_at >= NOW() - INTERVAL '8 days'
                    ) AS total_prev
                FROM feedback
                """
            )
            row = cur.fetchone() or {}
        conn.rollback()

    down_24h = int(row.get("down_24h") or 0)
    total_24h = int(row.get("total_24h") or 0)
    down_prev = int(row.get("down_prev") or 0)
    total_prev = int(row.get("total_prev") or 0)
    # Baseline troppo piccolo → nessun signal.
    if total_prev < 10 or total_24h == 0:
        return None
    rate_24h = down_24h / total_24h
    rate_prev = down_prev / total_prev if total_prev else 0.0
    if rate_prev <= 0:
        return None
    ratio = rate_24h / rate_prev
    if ratio < 1.5:
        return None
    severity = "high" if ratio >= 2.5 else "warning"
    return {
        "severity": severity,
        "down_24h": down_24h,
        "down_rate_24h": round(rate_24h, 4),
        "down_rate_baseline": round(rate_prev, 4),
        "ratio": round(ratio, 2),
        "message": (
            f"Tasso negativo 24h ({round(rate_24h * 100)}%) "
            f"superiore di {round((ratio - 1) * 100)}% al baseline 7gg."
        ),
    }


def feedback_stats(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    bucket: str = "day",
) -> dict[str, Any]:
    if not config.POSTGRES_ENABLED:
        return _empty_stats()
    from psycopg.rows import dict_row

    require_tenant_id()
    if bucket not in ("hour", "day", "week"):
        bucket = "day"

    where = ["1 = 1"]
    params: list[Any] = []
    if since is not None:
        where.append("created_at >= %s")
        params.append(since)
    if until is not None:
        where.append("created_at <= %s")
        params.append(until)
    where_sql = " AND ".join(where)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE rating = 'up') AS up,
                    COUNT(*) FILTER (WHERE rating = 'down') AS down,
                    COUNT(*) FILTER (WHERE reason IS NOT NULL AND reason <> '') AS with_reason,
                    COUNT(DISTINCT user_id) AS unique_users,
                    COUNT(*) FILTER (WHERE status = 'open') AS s_open,
                    COUNT(*) FILTER (WHERE status = 'triaged') AS s_triaged,
                    COUNT(*) FILTER (WHERE status = 'resolved') AS s_resolved,
                    COUNT(*) FILTER (WHERE status = 'dismissed') AS s_dismissed
                FROM feedback
                WHERE {where_sql}
                """,  # nosec B608
                params,
            )
            agg = cur.fetchone() or {}

            cur.execute(
                f"""
                SELECT
                    date_trunc(%s, created_at) AS bucket,
                    COUNT(*) FILTER (WHERE rating = 'up') AS up,
                    COUNT(*) FILTER (WHERE rating = 'down') AS down
                FROM feedback
                WHERE {where_sql}
                GROUP BY 1
                ORDER BY 1 ASC
                """,  # nosec B608
                [bucket, *params],
            )
            trend_rows = cur.fetchall()

            cur.execute(
                f"""
                SELECT question,
                       COUNT(*) AS n,
                       COUNT(*) FILTER (WHERE rating = 'down') AS down
                FROM feedback
                WHERE {where_sql} AND question IS NOT NULL AND question <> ''
                GROUP BY question
                HAVING COUNT(*) >= 2
                ORDER BY down DESC, n DESC
                LIMIT 10
                """,  # nosec B608
                params,
            )
            top_rows = cur.fetchall()
        conn.rollback()

    total = int(agg.get("total") or 0)
    up = int(agg.get("up") or 0)
    down = int(agg.get("down") or 0)
    positive_rate = (up / total) if total else 0.0
    trend = [
        {
            "bucket": (
                r["bucket"].isoformat()
                if r.get("bucket") and hasattr(r["bucket"], "isoformat")
                else str(r.get("bucket") or "")
            ),
            "up": int(r.get("up") or 0),
            "down": int(r.get("down") or 0),
        }
        for r in trend_rows
    ]
    top_questions = [
        {
            "question": r.get("question") or "",
            "count": int(r.get("n") or 0),
            "down": int(r.get("down") or 0),
        }
        for r in top_rows
    ]
    return {
        "total": total,
        "up": up,
        "down": down,
        "positive_rate": round(positive_rate, 4),
        "with_reason": int(agg.get("with_reason") or 0),
        "unique_users": int(agg.get("unique_users") or 0),
        "trend": trend,
        "top_questions": top_questions,
        "status_breakdown": {
            "open": int(agg.get("s_open") or 0),
            "triaged": int(agg.get("s_triaged") or 0),
            "resolved": int(agg.get("s_resolved") or 0),
            "dismissed": int(agg.get("s_dismissed") or 0),
        },
        "anomaly": _anomaly_signal(),
    }


def feedback_source_stats(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Per-document KPI: quanti feedback positivi / negativi ha generato
    ciascun documento citato. ``sources`` è JSONB array di
    ``{document_id, title, score}`` — espandiamo via ``jsonb_array_elements``
    e aggreghiamo per ``document_id``.
    """
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    require_tenant_id()
    where = ["sources IS NOT NULL", "jsonb_typeof(sources) = 'array'"]
    params: list[Any] = []
    if since is not None:
        where.append("created_at >= %s")
        params.append(since)
    if until is not None:
        where.append("created_at <= %s")
        params.append(until)
    params.append(max(1, min(limit, 200)))
    where_sql = " AND ".join(where)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                WITH expanded AS (
                    SELECT
                        s->>'document_id' AS document_id,
                        COALESCE(s->>'title', s->>'document_id') AS title,
                        f.rating
                    FROM feedback f,
                         LATERAL jsonb_array_elements(f.sources) AS s
                    WHERE {where_sql}
                )
                SELECT document_id,
                       MAX(title) AS title,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE rating = 'up') AS up,
                       COUNT(*) FILTER (WHERE rating = 'down') AS down
                FROM expanded
                WHERE document_id IS NOT NULL AND document_id <> ''
                GROUP BY document_id
                HAVING COUNT(*) >= 2
                ORDER BY down DESC, total DESC
                LIMIT %s
                """,  # nosec B608
                params,
            )
            rows = cur.fetchall()
        conn.rollback()

    out: list[dict[str, Any]] = []
    for r in rows:
        total = int(r.get("total") or 0)
        down = int(r.get("down") or 0)
        out.append(
            {
                "document_id": r.get("document_id") or "",
                "title": r.get("title") or r.get("document_id") or "",
                "total": total,
                "up": int(r.get("up") or 0),
                "down": down,
                "down_rate": round((down / total) if total else 0.0, 4),
            }
        )
    return out


__all__ = ["feedback_stats", "feedback_source_stats"]
