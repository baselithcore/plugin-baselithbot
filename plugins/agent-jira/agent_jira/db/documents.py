from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from psycopg.rows import dict_row

from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.config import APP_TIMEZONE, APP_TIMEZONE_NAME, POSTGRES_ENABLED

from .connection import get_connection
from .serializers import deserialize_sources


def _as_iso(value: Any) -> Optional[str]:
    """Converte datetime/str in ISO 8601 omettendo i valori nulli."""

    if value is None:
        return None
    if hasattr(value, "tzinfo"):
        if value.tzinfo is None:
            value = value.replace(tzinfo=APP_TIMEZONE)
        else:
            value = value.astimezone(APP_TIMEZONE)
        return value.isoformat()
    if hasattr(value, "isoformat"):
        # date objects: usa isoformat diretto (es. 2024-01-31)
        return value.isoformat()
    return str(value)


def determine_primary_key(source: Dict[str, Any]) -> Optional[str]:
    """Restituisce la chiave canonica per una fonte documentale."""

    doc_id = source.get("document_id")
    if isinstance(doc_id, str):
        doc_id = doc_id.strip()
        if doc_id:
            return f"id::{doc_id}"

    path = source.get("path")
    if isinstance(path, str):
        path = path.strip()
        if path:
            return f"path::{path}"

    url = source.get("url")
    if isinstance(url, str):
        url = url.strip()
        if url:
            return f"url::{url}"

    return None


def collect_alias_keys(source: Dict[str, Any]) -> List[str]:
    """Restituisce tutte le chiavi utilizzabili per individuare la fonte."""

    aliases: List[str] = []
    doc_id = source.get("document_id")
    if isinstance(doc_id, str):
        doc_id = doc_id.strip()
        if doc_id:
            aliases.append(f"id::{doc_id}")
    path = source.get("path")
    if isinstance(path, str):
        path = path.strip()
        if path:
            aliases.append(f"path::{path}")
    url = source.get("url")
    if isinstance(url, str):
        url = url.strip()
        if url:
            aliases.append(f"url::{url}")
    return aliases


def build_document_stats(
    rows: Iterable[Mapping[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """
    Aggrega statistiche per documento a partire dai feedback grezzi.

    Restituisce:
        stats: mapping chiave canonica -> aggregato
        aliases: mapping alias -> chiave canonica
    """

    stats: Dict[str, Dict[str, Any]] = {}
    aliases: Dict[str, str] = {}

    for row in rows:
        feedback_value = row.get("feedback")
        timestamp = row.get("timestamp")
        sources = deserialize_sources(row.get("sources"))
        if not sources:
            continue

        for source in sources:
            primary_key = determine_primary_key(source)
            if not primary_key:
                continue

            entry = stats.get(primary_key)
            if entry is None:
                entry = {
                    "document_id": source.get("document_id"),
                    "title": source.get("title"),
                    "path": source.get("path"),
                    "url": source.get("url"),
                    "origin": source.get("origin"),
                    "source_type": source.get("source_type"),
                    "positives": 0,
                    "negatives": 0,
                    "total": 0,
                    "last_timestamp": None,
                }
                stats[primary_key] = entry

            if feedback_value == "positive":
                entry["positives"] += 1
            elif feedback_value == "negative":
                entry["negatives"] += 1
            entry["total"] += 1

            timestamp_iso = _as_iso(timestamp)
            if timestamp_iso:
                previous = entry.get("last_timestamp")
                if previous is None or timestamp_iso > previous:
                    entry["last_timestamp"] = timestamp_iso

            for alias in collect_alias_keys(source):
                aliases[alias] = primary_key

    for primary_key in stats:
        aliases.setdefault(primary_key, primary_key)

    return stats, aliases


def get_document_feedback_summary(
    min_total: int = 0,
) -> Dict[str, Dict[str, Any]]:
    """
    Restituisce statistiche aggregate per ciascun documento citato nei feedback.

    Le chiavi includono sia quella canonica (es. id::abc123) sia gli alias (path::, url::).
    Utilizza aggregazione SQL su colonna jsonb per evitare full table scan in Python.
    """

    if not POSTGRES_ENABLED:
        return {}

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")

            # Aggregazione lato DB: espande l'array jsonb sources e raggruppa per document_id
            having_clause = "HAVING COUNT(*) >= %s" if min_total else ""
            params: List[Any] = [min_total] if min_total else []

            where_parts = ["f.sources IS NOT NULL"]
            tenant_id = get_current_tenant_id()
            if tenant_id is not None:
                where_parts.append("f.tenant_id = %s")
                params.insert(0, tenant_id)

            where_clause = " AND ".join(where_parts)

            cursor.execute(
                f"""
                SELECT
                    COALESCE(src->>'document_id', '') AS document_id,
                    COALESCE(src->>'title', '') AS title,
                    COALESCE(src->>'path', '') AS path,
                    COALESCE(src->>'url', '') AS url,
                    COALESCE(src->>'origin', '') AS origin,
                    COALESCE(src->>'source_type', '') AS source_type,
                    SUM(CASE WHEN f.feedback = 'positive' THEN 1 ELSE 0 END)::int AS positives,
                    SUM(CASE WHEN f.feedback = 'negative' THEN 1 ELSE 0 END)::int AS negatives,
                    COUNT(*)::int AS total,
                    MAX(f.timestamp) AS last_timestamp
                FROM feedback f,
                     jsonb_array_elements(f.sources) AS src
                WHERE {where_clause}
                GROUP BY document_id, title, path, url, origin, source_type
                {having_clause}
                ORDER BY total DESC
                """,
                params,
            )
            rows = cursor.fetchall()
        conn.rollback()

    summary: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        doc_id = row["document_id"]
        total_count = row["total"]

        computed = {
            "document_id": doc_id or None,
            "title": row["title"] or None,
            "path": row["path"] or None,
            "url": row["url"] or None,
            "origin": row["origin"] or None,
            "source_type": row["source_type"] or None,
            "positives": row["positives"],
            "negatives": row["negatives"],
            "total": total_count,
            "positive_rate": (row["positives"] / total_count if total_count else 0.0),
            "negative_rate": (row["negatives"] / total_count if total_count else 0.0),
            "last_timestamp": _as_iso(row.get("last_timestamp")),
        }

        # Genera chiave canonica e alias
        primary_key = determine_primary_key(computed)
        if not primary_key:
            continue
        summary[primary_key] = computed

        for alias in collect_alias_keys(computed):
            summary[alias] = computed

    return summary
