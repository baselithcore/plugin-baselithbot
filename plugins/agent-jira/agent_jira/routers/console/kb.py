from __future__ import annotations

import filecmp
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from urllib.parse import quote

from fastapi import BackgroundTasks, Form, HTTPException

from agent_jira.cache import TTLCache
from agent_jira.graphdb.core import graph_db
from agent_jira.kb_labels import build_document_label_candidates, build_kb_label
from agent_jira.tenant_context import get_tenant_documents_root
from agent_jira.ui.documents import (
    SUPPORTED_UPLOAD_TYPES,
    list_kb_documents,
    resolve_kb_document,
)
from agent_jira.ui.jira import get_jira_results_for_label, jira_client_ready
from agent_jira.config import (
    DOCUMENTS_ROOT,
    JIRA_BASE_URL,
    JIRA_ISSUE_TYPE,
    JIRA_TESTCASE_ISSUE_TYPE,
)

from . import router
from .common import _run_incremental_index, _validate_temp_path

_KB_COUNTS_CACHE = TTLCache(maxsize=500, ttl=300.0)
_KB_COUNTS_TTL_SECONDS = 300  # Kept for compatibility if referenced elsewhere, though effectively managed by TTLCache

# Graph result cache (maxsize 100 to avoid memory bloat from large graphs)
_GRAPH_CACHE = TTLCache(maxsize=100, ttl=300.0)
_GRAPH_CACHE_TTL_SECONDS = 300
_JIRA_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")

logger = logging.getLogger(__name__)


def _normalize_issue_type(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _issue_type_aliases(
    configured: Optional[str], fallback: str, *aliases: str
) -> set[str]:
    values = {
        _normalize_issue_type(configured),
        _normalize_issue_type(fallback),
        *(_normalize_issue_type(alias) for alias in aliases),
    }
    values.discard("")
    return values


def _count_jira_activity_for_label(label: str) -> Dict[str, int]:
    story_types = _issue_type_aliases(
        JIRA_ISSUE_TYPE,
        "Story",
        "User Story",
        "UserStory",
    )
    test_types = _issue_type_aliases(
        JIRA_TESTCASE_ISSUE_TYPE,
        "Test Case",
        "TestCase",
        "Test",
    )

    seen_keys: set[str] = set()
    try:
        results = get_jira_results_for_label(label, limit=200)
    except Exception:
        results = []

    story_count = 0
    test_count = 0
    for r in results:
        key = r.get("key")
        if isinstance(key, str):
            if key in seen_keys:
                continue
            seen_keys.add(key)
        issue_type_raw = (
            r.get("issue_type")
            or r.get("issuetype")
            or r.get("issueType")
            or r.get("type")
            or ""
        )
        issue_type = _normalize_issue_type(issue_type_raw)
        if issue_type in story_types or (
            "story" in issue_type
            and "test" not in issue_type
            and "epic" not in issue_type
        ):
            story_count += 1
        elif issue_type in test_types or "test" in issue_type:
            test_count += 1

    return {"stories": story_count, "test_cases": test_count}


def _kb_activity_counts() -> Dict[str, Dict[str, int]]:
    """
    Recupera conteggi Jira per label KB usando la label nome-file-hash.
    Usa una cache in-memory (TTL 5 minuti) per evitare chiamate ripetute a Jira e velocizzare il tab KB.
    """
    if not jira_client_ready():
        return {}

    activity: Dict[str, Dict[str, int]] = {}

    from agent_jira.tenant_context import get_current_tenant_id

    tenant_id = get_current_tenant_id() or "_default"

    for item in list_kb_documents():
        try:
            path_obj = resolve_kb_document(item)
            label = build_kb_label(path_obj)
        except Exception:
            continue
        if not label:
            continue

        cache_key = f"{tenant_id}::{label}"
        cached_counts = _KB_COUNTS_CACHE.get(cache_key)
        if cached_counts is not None:
            activity[item] = cached_counts
            continue

        counts = _count_jira_activity_for_label(label)
        _KB_COUNTS_CACHE.set(cache_key, counts)
        activity[item] = counts
    return activity


def _filter_graph_jira_nodes_for_label(
    graph: Dict[str, object], labels: Sequence[str]
) -> Dict[str, object]:
    normalized_labels = [label for label in labels if label]
    if not graph or not normalized_labels or not jira_client_ready():
        return graph

    try:
        jira_results: List[Dict[str, object]] = []
        seen_keys: set[str] = set()
        for label in normalized_labels:
            for item in get_jira_results_for_label(label, limit=200):
                issue_key = str(item.get("key", "")).strip().upper()
                if not issue_key or issue_key in seen_keys:
                    continue
                seen_keys.add(issue_key)
                jira_results.append(item)
    except Exception:
        return graph

    allowed_issue_keys = {
        str(item.get("key", "")).strip().upper()
        for item in jira_results
        if str(item.get("key", "")).strip()
    }

    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        return graph

    kept_ids: set[str] = set()
    filtered_nodes: List[Dict[str, object]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        group = str(node.get("group", "")).strip()
        is_jira_issue_node = group in {"Story", "TestCase", "JiraIssue"} and bool(
            _JIRA_KEY_RE.fullmatch(node_id.upper())
        )
        if is_jira_issue_node and node_id.upper() not in allowed_issue_keys:
            continue
        filtered_nodes.append(node)
        if node_id:
            kept_ids.add(node_id)

    filtered_links = [
        link
        for link in graph.get("links", [])
        if isinstance(link, dict)
        and str(link.get("source", "")) in kept_ids
        and str(link.get("target", "")) in kept_ids
    ]

    return {
        **graph,
        "nodes": filtered_nodes,
        "links": filtered_links,
    }


@router.get("/kb/counts")
def kb_counts(label: str, _t: Optional[str] = None) -> Dict[str, object]:
    """
    Recupera conteggi Story/Bug per una singola label KB, riutilizzando la cache.
    """
    if not jira_client_ready():
        raise HTTPException(
            status_code=503,
            detail="Integrazione Jira non configurata o disabilitata.",
        )
    if not label:
        raise HTTPException(status_code=400, detail="Specificare la label KB.")

    bypass_cache = bool(_t)
    cached_counts = None if bypass_cache else _KB_COUNTS_CACHE.get(label)
    if cached_counts is not None:
        return cached_counts

    counts = _count_jira_activity_for_label(label)
    _KB_COUNTS_CACHE.set(label, counts)
    return counts


@router.get("/kb/graph")
def kb_graph(path: str, _t: Optional[str] = None) -> Dict[str, object]:
    """
    Recupera il sottografo (nodi e link) per un documento specificato dal path.
    Utilizza cache in-memory (TTL 5 minuti) per migliorare le performance.
    """
    try:
        if not path:
            raise HTTPException(status_code=400, detail="Path del file richiesto.")

        if not graph_db.is_enabled():
            logger.warning("[kb_graph] GraphDB is DISABLED in config.")
            return {"nodes": [], "links": []}

        # Check cache first
        now = time.time()
        bypass_cache = bool(_t)
        cached = None if bypass_cache else _GRAPH_CACHE.get(path)
        if cached:
            ts, result = cached
            try:
                path_obj = resolve_kb_document(path)
                file_mtime = path_obj.stat().st_mtime
                if file_mtime <= ts:
                    logger.info(f"[kb_graph] Cache HIT for {path}")
                    return result
                else:
                    logger.info(f"[kb_graph] Cache STALE for {path} (file modified)")
            except Exception as e:
                logger.warning(f"[kb_graph] Cache validation failed: {e}")

        # Cache miss or stale - fetch from database
        logger.info(f"[kb_graph] Cache MISS for {path} - fetching from database")
        path_obj = resolve_kb_document(path)

        label_candidates = build_document_label_candidates(path_obj)
        primary_id = (
            label_candidates[0] if label_candidates else build_kb_label(path_obj)
        )

        result = graph_db.get_document_subgraph(primary_id)
        if result["nodes"]:
            result = _filter_graph_jira_nodes_for_label(result, label_candidates)
            _GRAPH_CACHE.set(path, (now, result))
            return result

        fallback_id = path_obj.name
        if fallback_id != primary_id:
            result_fallback = graph_db.get_document_subgraph(fallback_id)
            if result_fallback["nodes"]:
                result_fallback = _filter_graph_jira_nodes_for_label(
                    result_fallback, label_candidates
                )
                _GRAPH_CACHE.set(path, (now, result_fallback))
                return result_fallback

        stem_id = path_obj.stem
        if stem_id != primary_id and stem_id != fallback_id:
            result_stem = graph_db.get_document_subgraph(stem_id)
            if result_stem["nodes"]:
                result_stem = _filter_graph_jira_nodes_for_label(
                    result_stem, label_candidates
                )
                _GRAPH_CACHE.set(path, (now, result_stem))
                return result_stem

        found_id = graph_db.search_node("path", path_obj.name)
        if found_id:
            result_found = graph_db.get_document_subgraph(found_id)
            result_found = _filter_graph_jira_nodes_for_label(
                result_found, label_candidates
            )
            _GRAPH_CACHE.set(path, (now, result_found))
            return result_found

        found_id = graph_db.search_node("name", path_obj.name)
        if found_id:
            result_found = graph_db.get_document_subgraph(found_id)
            result_found = _filter_graph_jira_nodes_for_label(
                result_found, label_candidates
            )
            _GRAPH_CACHE.set(path, (now, result_found))
            return result_found

        _GRAPH_CACHE.set(path, (now, result))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Graph Search Failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Errore durante la ricerca nel grafo: {str(exc)}"
        )


@router.get("/kb/documents")
def kb_documents() -> Dict[str, object]:
    activity = {}  # Skip counter calculation for performance - load on-demand via /kb/counts
    entries: List[Dict[str, Optional[str]]] = []

    def _issue_type(value: Optional[str], fallback: str) -> str:
        if value and isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
        return fallback

    story_type_cfg = _issue_type(JIRA_ISSUE_TYPE, "Story")
    test_type_cfg = _issue_type(JIRA_TESTCASE_ISSUE_TYPE, "Bug")

    for item in list_kb_documents():
        try:
            path_obj = resolve_kb_document(item)
            label = build_kb_label(path_obj)
        except Exception:
            label = None
        counts = activity.get(item, {})
        search_url = None
        story_url = None
        test_url = None
        uploaded_at = None
        if label and JIRA_BASE_URL:
            base_clause = f'labels = "{label}"'
            search_url = f"{JIRA_BASE_URL}/issues/?jql={quote(base_clause)}"
            story_clause = f'{base_clause} AND issuetype = "{story_type_cfg}"'
            test_clause = f'{base_clause} AND issuetype = "{test_type_cfg}"'
            story_url = f"{JIRA_BASE_URL}/issues/?jql={quote(story_clause)}"
            test_url = f"{JIRA_BASE_URL}/issues/?jql={quote(test_clause)}"
        try:
            stat = path_obj.stat()
            uploaded_at = datetime.fromtimestamp(stat.st_mtime).date().isoformat()
        except Exception:
            uploaded_at = None
        entries.append(
            {
                "path": item,
                "label": label,
                "stories": counts.get("stories", 0),
                "test_cases": counts.get("test_cases", 0),
                "jira_search_url": search_url,
                "jira_story_url": story_url,
                "jira_test_url": test_url,
                "uploaded_at": uploaded_at,
            }
        )
    return {"documents": entries, "supported_upload_types": SUPPORTED_UPLOAD_TYPES}


@router.post("/kb/store")
async def store_in_kb(
    background_tasks: BackgroundTasks,
    file_path: str = Form(...),
    original_name: Optional[str] = Form(None),
    analysis_json: Optional[str] = Form(None),
) -> Dict[str, object]:
    logger.info(
        f"kb/store request: file_path={file_path!r} original_name={original_name!r} "
        f"analysis_json_len={len(analysis_json) if analysis_json else 0}"
    )
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="Nessun file disponibile: analizza un documento prima di copiarlo nella KB.",
        )
    try:
        temp_path = _validate_temp_path(file_path)
    except HTTPException as exc:
        logger.warning(
            f"kb/store _validate_temp_path failed for {file_path!r}: {exc.detail}"
        )
        raise

    # Sprint 12: hard quota enforcement (storage MB + numero documenti).
    # Non blocca in single-tenant o se il tenant non ha piano (safe default).
    try:
        from agent_jira.db.tenants import get_tenant_by_id
        from agent_jira.quotas import quota_tracker
        from agent_jira.tenant_context import get_current_tenant_id

        tid = get_current_tenant_id()
        if tid:
            tenant = get_tenant_by_id(tid)
            plan = (tenant or {}).get("plan", "free")
            incoming_bytes = temp_path.stat().st_size
            quota_tracker.check_upload_quota(plan, incoming_bytes, tenant_id=tid)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"kb/store quota check skipped: {exc}")

    safe_original = None
    if original_name:
        try:
            safe_original = Path(original_name).name
        except Exception:
            safe_original = None

    docs_root = get_tenant_documents_root(DOCUMENTS_ROOT)
    docs_root.mkdir(parents=True, exist_ok=True)
    target_name = safe_original or temp_path.name
    if safe_original and not Path(safe_original).suffix and temp_path.suffix:
        target_name = f"{safe_original}{temp_path.suffix}"
    target = docs_root / target_name

    if target.exists():
        try:
            if filecmp.cmp(temp_path, target, shallow=False):
                return {
                    "status": "ok",
                    "message": (
                        f"Documento già presente nella knowledge base come {target.name}; "
                        "nessuna nuova indicizzazione eseguita."
                    ),
                    "kb_path": target.name,
                    "indexed": 0,
                }
        except OSError:
            pass
        counter = 1
        base_stem = target.stem
        suffix = target.suffix
        while target.exists():
            target = docs_root / f"{base_stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(temp_path, target)

    # Save analysis result to disk if provided
    if analysis_json:
        try:
            analysis_file = target.with_suffix(target.suffix + ".analysis.json")
            analysis_file.write_text(analysis_json, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save analysis JSON for {target.name}: {e}")

    # Run indexing in background to return immediate response to user
    background_tasks.add_task(_run_incremental_index)

    message = (
        f"Documento aggiunto alla knowledge base come {target.name}; "
        "indicizzazione avviata in background."
    )
    return {
        "status": "ok",
        "message": message,
        "kb_path": target.name,
        "indexed": -1,  # -1 indicates background processing
        "analysis_saved": bool(analysis_json),
    }


@router.delete("/kb/delete")
async def delete_kb_document(file_path: str) -> Dict[str, object]:
    """Elimina un documento dalla KB e i relativi indici (Qdrant/GraphDB)."""

    if not file_path:
        raise HTTPException(status_code=400, detail="Path del file richiesto.")

    safe_name = Path(file_path).name
    docs_root = get_tenant_documents_root(DOCUMENTS_ROOT)
    target = docs_root / safe_name

    if not target.exists():
        # Potrebbe essere già stato cancellato, o path errato
        # Proviamo a re-indicizzare comunque per pulire eventuali residui
        await _run_incremental_index()
        return {
            "status": "ok",
            "message": f"Documento {safe_name} non trovato su disco. Indici aggiornati.",
        }

    try:
        target.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Errore eliminando il file: {exc}")

    # Re-indicizzazione: rileverà il file mancante come 'stale' e pulirà Qdrant/GraphDB
    await _run_incremental_index()

    return {
        "status": "ok",
        "message": f"Documento {safe_name} eliminato correttamente.",
    }
