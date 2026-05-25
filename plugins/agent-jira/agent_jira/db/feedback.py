from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, List, Optional, Set

from psycopg.rows import dict_row

from agent_jira.graphdb import graph_db
from agent_jira.tenant_context import get_current_tenant_id
from agent_jira.config import (
    ACTIVE_LEARNING_LIMIT,
    ACTIVE_LEARNING_MAX_POSITIVE_RATE,
    ACTIVE_LEARNING_MIN_TOTAL,
    APP_TIMEZONE,
    APP_TIMEZONE_NAME,
)

from .connection import get_connection
from .documents import build_document_stats
from .serializers import deserialize_sources, serialize_sources


def _now_iso() -> str:
    """Restituisce il timestamp corrente in formato ISO 8601 nel fuso configurato."""

    return datetime.datetime.now(APP_TIMEZONE).isoformat()


def _as_iso(value: Any) -> Optional[str]:
    """Converte datetime/str in ISO 8601 omettendo i valori nulli."""

    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=APP_TIMEZONE)
        else:
            value = value.astimezone(APP_TIMEZONE)
        return value.isoformat()
    return str(value)


def insert_feedback(
    query: str,
    answer: str,
    feedback: str,
    *,
    conversation_id: Optional[str] = None,
    sources: Optional[Iterable[Dict[str, Any]]] = None,
    comment: Optional[str] = None,
) -> None:
    """
    Inserisce un nuovo feedback nel database, includendo eventuali metadati aggiuntivi.
    Il tenant_id viene automaticamente letto dal context corrente.
    """

    sanitized_comment = comment.strip() if isinstance(comment, str) else None
    tenant_id = get_current_tenant_id()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feedback (query, answer, feedback, conversation_id, sources, comment, timestamp, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    query,
                    answer,
                    feedback,
                    conversation_id or None,
                    serialize_sources(sources),
                    sanitized_comment,
                    _now_iso(),
                    tenant_id,
                ),
            )
        conn.commit()

    # Aggiorna il grafo con contatori feedback per i documenti coinvolti (se presenti)
    try:
        doc_ids: Set[str] = set()
        for src in sources or []:
            if not isinstance(src, dict):
                continue
            doc_id = src.get("document_id")
            if isinstance(doc_id, str) and doc_id.strip():
                doc_ids.add(doc_id.strip())
        for doc_id in doc_ids:
            graph_db.record_document_feedback(doc_id, feedback, sanitized_comment)
    except Exception:
        # Silenzioso: non blocca la raccolta feedback se il grafo è disabilitato/non raggiungibile
        pass


def _tenant_filter(params: List[Any], *, existing_where: bool = False) -> str:
    """Aggiunge il filtro tenant alla query se presente nel context."""
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return ""
    conjunction = " AND " if existing_where else " WHERE "
    params.append(tenant_id)
    return f"{conjunction}tenant_id = %s"


def get_feedbacks(
    feedback: Optional[str] = None,
    *,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Recupera feedback dal database, filtrati per tenant corrente.
    Se `feedback` è specificato ('positive' o 'negative'), restituisce solo quelli filtrati.
    È possibile limitare il numero di record restituiti con `limit`.
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            query = (
                "SELECT id, query, answer, feedback, conversation_id, sources, comment, timestamp "
                "FROM feedback"
            )
            params: List[Any] = []
            has_where = False
            if feedback:
                query += " WHERE feedback = %s"
                params.append(feedback)
                has_where = True
            query += _tenant_filter(params, existing_where=has_where)
            query += " ORDER BY timestamp DESC"

            if limit is not None and limit > 0:
                query += " LIMIT %s"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
        conn.rollback()

    results: List[Dict[str, Any]] = []
    for row in rows:
        timestamp_value = _as_iso(row.get("timestamp"))
        entry: Dict[str, Any] = {
            "id": row["id"],
            "query": row["query"],
            "answer": row["answer"],
            "feedback": row["feedback"],
            "timestamp": timestamp_value,
        }
        conversation_id = row.get("conversation_id")
        if conversation_id:
            entry["conversation_id"] = conversation_id
        comment_value = row.get("comment")
        if comment_value:
            entry["comment"] = comment_value
        sources = deserialize_sources(row.get("sources"))
        if sources:
            entry["sources"] = sources
        results.append(entry)
    return results


def get_feedback_analytics(
    *,
    days: Optional[int] = None,
    recent_limit: int = 20,
    top_limit: int = 10,
) -> Dict[str, Any]:
    """
    Restituisce un riepilogo dei feedback con:
    - conteggi aggregati
    - serie temporale giornaliera
    - ultimi feedback ricevuti
    - query più frequenti
    - documenti/fonti più citati nelle risposte con feedback
    """

    total = 0
    positives = 0
    negatives = 0
    since_iso: Optional[str] = None
    timeseries: List[Dict[str, Any]] = []
    recent: List[Dict[str, Any]] = []
    top_queries: List[Dict[str, Any]] = []
    doc_rows: List[Dict[str, Any]] = []
    learning_rows: List[Dict[str, Any]] = []

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SET TIME ZONE '{APP_TIMEZONE_NAME}'")
            params: List[Any] = []
            where_parts: List[str] = []

            if days is not None:
                since = datetime.datetime.now(APP_TIMEZONE) - datetime.timedelta(
                    days=max(1, days)
                )
                since_iso = since.isoformat()
                where_parts.append("timestamp >= %s")
                params.append(since)

            # Filtro tenant
            tenant_id = get_current_tenant_id()
            if tenant_id is not None:
                where_parts.append("tenant_id = %s")
                params.append(tenant_id)

            where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
            base_params = tuple(params)

            totals_query = (
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN feedback='positive' THEN 1 ELSE 0 END) AS positives, "
                "SUM(CASE WHEN feedback='negative' THEN 1 ELSE 0 END) AS negatives "
                f"FROM feedback {where_clause}"
            )
            cursor.execute(totals_query, base_params)
            totals_row = cursor.fetchone() or {}
            total = int(totals_row.get("total") or 0)
            positives = int(totals_row.get("positives") or 0)
            negatives = int(totals_row.get("negatives") or 0)

            timeseries_query = (
                "SELECT DATE(timestamp) AS day, "
                "SUM(CASE WHEN feedback='positive' THEN 1 ELSE 0 END) AS positives, "
                "SUM(CASE WHEN feedback='negative' THEN 1 ELSE 0 END) AS negatives, "
                "COUNT(*) AS total "
                f"FROM feedback {where_clause} "
                "GROUP BY day "
                "ORDER BY day ASC"
            )
            cursor.execute(timeseries_query, base_params)
            for row in cursor.fetchall():
                day_value = row.get("day")
                if hasattr(day_value, "isoformat"):
                    day_str = day_value.isoformat()
                else:
                    day_str = str(day_value)
                timeseries.append(
                    {
                        "date": day_str,
                        "total": int(row.get("total") or 0),
                        "positives": int(row.get("positives") or 0),
                        "negatives": int(row.get("negatives") or 0),
                    }
                )

            recent_query = (
                "SELECT id, query, answer, feedback, conversation_id, sources, comment, timestamp "
                f"FROM feedback {where_clause} "
                "ORDER BY timestamp DESC "
                "LIMIT %s"
            )
            recent_params = list(base_params)
            recent_params.append(max(1, recent_limit))
            cursor.execute(recent_query, recent_params)
            for row in cursor.fetchall():
                entry: Dict[str, Any] = {
                    "id": row["id"],
                    "query": row["query"],
                    "answer": row["answer"],
                    "feedback": row["feedback"],
                    "timestamp": _as_iso(row.get("timestamp")),
                }
                if row.get("conversation_id"):
                    entry["conversation_id"] = row["conversation_id"]
                comment_value = row.get("comment")
                if comment_value:
                    entry["comment"] = comment_value
                sources = deserialize_sources(row.get("sources"))
                if sources:
                    entry["sources"] = sources
                recent.append(entry)

            top_queries_query = (
                "SELECT query, "
                "SUM(CASE WHEN feedback='positive' THEN 1 ELSE 0 END) AS positives, "
                "SUM(CASE WHEN feedback='negative' THEN 1 ELSE 0 END) AS negatives, "
                "COUNT(*) AS total, "
                "MAX(timestamp) AS last_timestamp "
                f"FROM feedback {where_clause} "
                "GROUP BY query "
                "HAVING COUNT(*) > 0 "
                "ORDER BY total DESC, last_timestamp DESC "
                "LIMIT %s"
            )
            top_queries_params = list(base_params)
            top_queries_params.append(max(1, top_limit))
            cursor.execute(top_queries_query, top_queries_params)
            for row in cursor.fetchall():
                total_count = int(row.get("total") or 0)
                positive_count = int(row.get("positives") or 0)
                negative_count = int(row.get("negatives") or 0)
                top_queries.append(
                    {
                        "query": row["query"],
                        "total": total_count,
                        "positives": positive_count,
                        "negatives": negative_count,
                        "positive_rate": (positive_count / total_count)
                        if total_count
                        else 0.0,
                        "last_timestamp": _as_iso(row.get("last_timestamp")),
                    }
                )

            if where_clause:
                doc_query = (
                    "SELECT feedback, sources, timestamp FROM feedback "
                    f"{where_clause} AND sources IS NOT NULL"
                )
                doc_params = base_params
            else:
                doc_query = (
                    "SELECT feedback, sources, timestamp FROM feedback "
                    "WHERE sources IS NOT NULL"
                )
                doc_params = ()
            cursor.execute(doc_query, doc_params)
            doc_rows = cursor.fetchall()

            learning_query = (
                "SELECT query, "
                "SUM(CASE WHEN feedback='positive' THEN 1 ELSE 0 END) AS positives, "
                "SUM(CASE WHEN feedback='negative' THEN 1 ELSE 0 END) AS negatives, "
                "COUNT(*) AS total, "
                "MAX(timestamp) AS last_timestamp "
                f"FROM feedback {where_clause} "
                "GROUP BY query "
                "HAVING COUNT(*) >= %s "
                "ORDER BY negatives DESC, total DESC, last_timestamp DESC "
                "LIMIT %s"
            )
            learning_params = list(base_params)
            learning_params.append(max(1, ACTIVE_LEARNING_MIN_TOTAL))
            learning_params.append(max(1, ACTIVE_LEARNING_LIMIT))
            cursor.execute(learning_query, learning_params)
            learning_rows = cursor.fetchall()
        conn.rollback()

    document_stats, _ = build_document_stats(doc_rows)

    top_documents = sorted(
        document_stats.values(),
        key=lambda item: item["total"],
        reverse=True,
    )[: max(1, top_limit)]

    for entry in top_documents:
        total_count = entry["total"] or 0
        if total_count:
            entry["positive_rate"] = entry["positives"] / total_count
            entry["negative_rate"] = entry["negatives"] / total_count
        else:
            entry["positive_rate"] = 0.0
            entry["negative_rate"] = 0.0
        entry["last_timestamp"] = _as_iso(entry.get("last_timestamp"))

    learning_candidates: List[Dict[str, Any]] = []
    for row in learning_rows:
        total_count = int(row["total"] or 0)
        if total_count <= 0:
            continue
        positive_count = int(row["positives"] or 0)
        negative_count = int(row["negatives"] or 0)
        positive_rate = positive_count / total_count if total_count else 0.0
        if (
            positive_rate > ACTIVE_LEARNING_MAX_POSITIVE_RATE
            and negative_count <= positive_count
        ):
            continue
        learning_candidates.append(
            {
                "query": row["query"],
                "total": total_count,
                "positives": positive_count,
                "negatives": negative_count,
                "positive_rate": positive_rate,
                "negative_rate": (negative_count / total_count if total_count else 0.0),
                "last_timestamp": _as_iso(row.get("last_timestamp")),
            }
        )

    return {
        "total_feedbacks": total,
        "positives": positives,
        "negatives": negatives,
        "positive_rate": (positives / total) if total else 0.0,
        "negative_rate": (negatives / total) if total else 0.0,
        "timeseries": timeseries,
        "recent": recent,
        "top_queries": top_queries,
        "top_documents": top_documents,
        "learning_candidates": learning_candidates,
        "window": {"days": days, "since": since_iso},
    }
