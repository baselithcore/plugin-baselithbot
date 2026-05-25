from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from fastapi import File, Form, HTTPException, UploadFile

from agent_jira.agents.metadata_agent import MetadataAgent
from agent_jira.cost_control import BudgetExceededError
from agent_jira.kb_labels import build_document_label_candidates, build_kb_label
from agent_jira.project_manager import ProjectPlan
from agent_jira.project_manager.story_count import parse_requested_story_count
from agent_jira.ui.constants import DEFAULT_KB_STATUS, KB_ALREADY_PRESENT_STATUS
from agent_jira.ui.documents import (
    append_kb_label_to_plan,
    load_uploaded_document,
    resolve_kb_document,
)
from agent_jira.ui.jira import (
    build_jira_status,
    coerce_project_plan,
    get_jira_results_for_label,
    has_user_stories,
    jira_client_ready,
)
from agent_jira.ui.renderers import render_project_plan
from agent_jira.ui.reporting import build_project_plan_html, render_report_html, slugify
from agent_jira.ui.services import chat_service
from agent_jira.config import AGENT_MAX_TOKENS, DOCUMENTS_ROOT, MULTI_TENANT_ENABLED

from . import router
from .common import (
    _cache_key_from_metadata,
    _doc_type_label,
    _get_analysis_cache,
    _get_project_planner,
    _human_size_from_kb,
    _persist_upload,
    _prompt_fingerprint,
    logger,
)

_PLANNING_SIGNAL_KEYWORDS = (
    "obiettivo",
    "obiettivi",
    "modulo",
    "moduli",
    "funzional",
    "requisit",
    "vincol",
    "risch",
    "stakeholder",
    "integraz",
    "timeline",
    "milestone",
    "dipenden",
    "attore",
    "flusso",
    "processo",
    "jira",
    "api",
    "deadline",
    "scope",
)
_LIST_PREFIX_RE = re.compile(r"^(\d+[\.\)]\s+|[-*•]\s+|[A-Z][\.\)]\s+)")


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // 4


def _is_signal_line(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in _PLANNING_SIGNAL_KEYWORDS)


def _extract_structural_highlights(text: str, *, max_lines: int = 40) -> List[str]:
    highlights: List[str] = []
    seen: set[str] = set()

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()
        if len(line) < 4 or len(line) > 220:
            continue

        is_heading = line.endswith(":") or line.startswith("#") or line.isupper()
        is_list_item = bool(_LIST_PREFIX_RE.match(line))
        if not (is_heading or is_list_item or _is_signal_line(line)):
            continue

        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        highlights.append(line)
        if len(highlights) >= max_lines:
            break

    return highlights


def _compact_document_for_planning(content: str, *, aggressive: bool = False) -> str:
    normalized = content.strip()
    if not normalized:
        return normalized

    target_tokens = AGENT_MAX_TOKENS // (6 if aggressive else 4)
    target_tokens = max(1200 if aggressive else 1800, target_tokens)
    target_tokens = min(1600 if aggressive else 2500, target_tokens)
    max_chars = target_tokens * 4

    if len(normalized) <= max_chars:
        return normalized

    highlights = _extract_structural_highlights(
        normalized, max_lines=25 if aggressive else 40
    )
    highlight_block = ""
    if highlights:
        highlight_block = "### Evidenze strutturali\n" + "\n".join(
            f"- {line}" for line in highlights
        )

    excerpt_chars = max(1200, (max_chars - len(highlight_block) - 400) // 3)
    excerpt_chars = min(excerpt_chars, 3200 if aggressive else 4200)

    middle_start = max(0, len(normalized) // 2 - excerpt_chars // 2)
    middle_end = min(len(normalized), middle_start + excerpt_chars)

    parts = [
        "### Nota\nContenuto compattato automaticamente per rientrare nel limite token del planner.",
    ]
    if highlight_block:
        parts.append(highlight_block)
    parts.extend(
        [
            "### Inizio documento\n" + normalized[:excerpt_chars].strip(),
            "### Sezione centrale\n" + normalized[middle_start:middle_end].strip(),
            "### Fine documento\n" + normalized[-excerpt_chars:].strip(),
        ]
    )

    compacted = "\n\n".join(part for part in parts if part.strip()).strip()
    if len(compacted) <= max_chars:
        return compacted

    return compacted[: max_chars - 1].rstrip() + "…"


def _refresh_cached_upload_path(
    cached: Dict[str, object],
    stored_file_path: Optional[str],
    resolved_from_kb: bool,
) -> Dict[str, object]:
    """Sovrascrivi upload_path nel risultato cached con il temp file appena
    creato: il path originale potrebbe non esistere più (pulizia tmp, riavvio).
    """
    if resolved_from_kb or not stored_file_path:
        return cached
    refreshed: Dict[str, Any] = dict(cached)
    raw_kb = refreshed.get("kb")
    kb_block: Dict[str, Any] = dict(raw_kb) if isinstance(raw_kb, dict) else {}
    if kb_block.get("from_kb"):
        return cached
    kb_block["upload_path"] = stored_file_path
    kb_block["can_store"] = True
    refreshed["kb"] = kb_block
    return refreshed


@router.post("/analyze")
async def analyze_document(
    prompt: Optional[str] = Form(None),
    kb_document: Optional[str] = Form(None),
    file: UploadFile | None = File(None),
) -> Dict[str, object]:
    try:
        start_time = time.perf_counter()
        from_kb = bool(kb_document)
        resolved_from_kb = from_kb
        if not from_kb and file is None:
            raise HTTPException(
                status_code=400,
                detail="Carica un file supportato oppure seleziona un documento dalla KB.",
            )

        unified_label: Optional[str] = None
        context_label: Optional[str] = None
        category_label: Optional[str] = None
        kb_override_path: Optional[Path] = None
        stored_file_path: Optional[str] = None
        original_name: Optional[str] = file.filename if file is not None else None
        try:
            if from_kb:
                path_obj = resolve_kb_document(kb_document or "")
            else:
                if file is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Carica un file supportato per procedere con l'analisi.",
                    )
                path_obj = await _persist_upload(file)
                stored_file_path = str(path_obj)
                candidate_names = [path_obj.name]
                if original_name:
                    candidate_names.insert(0, Path(original_name).name)
                for candidate in dict.fromkeys(candidate_names):
                    matches = [
                        p for p in DOCUMENTS_ROOT.rglob(candidate) if p.is_file()
                    ]
                    if len(matches) == 1:
                        kb_override_path = matches[0]
                        resolved_from_kb = True
                        stored_file_path = None
                        break
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            content, metadata = load_uploaded_document(str(path_obj))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if original_name:
            metadata["original_name"] = original_name
            metadata.setdefault("file_name", original_name)
            metadata.setdefault("filename", original_name)
        else:
            metadata.setdefault("file_name", metadata.get("display_name"))
            metadata.setdefault("filename", metadata.get("display_name"))

        label_candidates: List[str] = []
        if resolved_from_kb or kb_override_path:
            kb_source = kb_override_path or path_obj
            unified_label = build_kb_label(kb_source)
            label_candidates = build_document_label_candidates(kb_source)
            metadata["source"] = "knowledge_base"
            try:
                kb_relative = kb_source.relative_to(DOCUMENTS_ROOT).as_posix()
                metadata["kb_path"] = kb_relative
            except Exception:
                pass
            category_label = "knowledge-base"
        else:
            metadata["source"] = "analysis"
            category_label = "analysis"
            label_source_name = (
                metadata.get("original_name") or path_obj.stem or "document"
            )
            label_source = Path(label_source_name)
            unified_label = build_kb_label(label_source)
            label_candidates = build_document_label_candidates(label_source)

        metadata["kb_label"] = unified_label
        metadata["jira_label"] = unified_label
        metadata["doc_label"] = unified_label
        metadata["jira_label_aliases"] = label_candidates or (
            [unified_label] if unified_label else []
        )
        context_label = unified_label

        if unified_label:
            try:
                doc_type = (metadata.get("extension") or "file").replace(".", "")
                doc_path = (
                    str(kb_override_path)
                    if kb_override_path
                    else (stored_file_path or str(path_obj))
                )
                from agent_jira.agents.graph_agent import GraphAgent
                from agent_jira.graphdb import graph_db

                if graph_db.is_enabled():
                    ga = GraphAgent(graph_db)
                    safe_props = {
                        k: v
                        for k, v in metadata.items()
                        if isinstance(v, (str, int, float, bool))
                    }

                    ga.upsert_document(
                        doc_id=unified_label,
                        doc_type=doc_type,
                        path=doc_path,
                        category="analysis",
                        properties=safe_props,
                    )
            except Exception:
                logger.warning(
                    "Analysis: failed to upsert document to graph", exc_info=True
                )

        prompt_fp = _prompt_fingerprint(prompt)

        cache = _get_analysis_cache()
        cache_key = _cache_key_from_metadata(metadata, prompt)
        if cache and cache_key:
            cached = cache.get(cache_key)
            if cached:
                logger.info("Cache hit per analisi documento: %s", cache_key)
                return _refresh_cached_upload_path(
                    cached, stored_file_path, resolved_from_kb
                )

        # Se il documento è in KB, controlla se esiste un'analisi salvata su disco
        # (distinta per brief del planner, così brief diversi non si sovrascrivono).
        if resolved_from_kb or kb_override_path:
            kb_source = kb_override_path or path_obj
            analysis_suffix = (
                ".analysis.json"
                if prompt_fp == "noprompt"
                else f".analysis.{prompt_fp}.json"
            )
            analysis_file = kb_source.with_suffix(kb_source.suffix + analysis_suffix)
            if analysis_file.exists():
                try:
                    disk_cached = json.loads(analysis_file.read_text(encoding="utf-8"))
                    logger.info(
                        "Recuperata analisi da persistenza su disco per: %s",
                        kb_source.name,
                    )
                    # Aggiorna anche la cache in-memory/redis per velocizzare accessi futuri
                    if cache and cache_key:
                        cache.set(cache_key, disk_cached)
                    return _refresh_cached_upload_path(
                        disk_cached, stored_file_path, resolved_from_kb
                    )
                except Exception as e:
                    logger.warning(
                        "Errore caricamento analisi da disco per %s: %s",
                        kb_source.name,
                        e,
                    )

        planner = _get_project_planner()
        default_query = (
            f"Analizza il documento '{metadata.get('display_name', 'selezionato')}' e proponi user "
            "story prioritarie. Includi acceptance criteria chiari, identifica gli attori "
            "principali, gli obiettivi di business, i risultati attesi, oltre a evidenziare "
            "eventuali rischi o dipendenze."
        )
        planner_guidance = (
            "Linee guida output planner:\n"
            "- Per ogni user story, business_value deve contenere 3 punti sintetici e concreti, "
            'diversi dalla frase "Come <ruolo> voglio <goal> così da <benefit>".\n'
            "- I punti di business value non devono ripetere goal/benefit: esprimi outcome "
            "misurabili, benefici per stakeholder o impatti su processo/tempo/costi/qualità.\n"
            "- Mantieni business_value come array di 3 stringhe brevi."
        )
        user_brief = (prompt or "").strip()
        query = "\n\n".join(
            filter(None, [user_brief or default_query, planner_guidance])
        )

        max_stories = None
        if prompt:
            max_stories = parse_requested_story_count(prompt, default=None)
            if max_stories is not None:
                logger.info(f"Analysis: user requested {max_stories} stories.")

        metadata_brief = None
        try:
            extracted_context = MetadataAgent().analyze_document(
                content,
                doc_id=unified_label or metadata.get("display_name", ""),
                enrich=False,
            )
            metadata_brief = extracted_context.to_planning_brief()
            if extracted_context.domain:
                metadata.setdefault("domain", extracted_context.domain)
        except Exception:
            logger.warning("Analysis: metadata extraction failed", exc_info=True)

        planning_context = _compact_document_for_planning(content)
        context_mode = "full" if planning_context == content else "condensed"
        metadata["analysis_context_mode"] = context_mode
        metadata["analysis_context_chars"] = len(planning_context)
        metadata["analysis_context_tokens_estimate"] = _estimate_tokens(
            planning_context
        )
        if context_mode != "full":
            logger.info(
                "Analysis: compacted planning context for %s (%s -> %s chars, ~%s tokens)",
                metadata.get("display_name"),
                len(content),
                len(planning_context),
                _estimate_tokens(planning_context),
            )

        try:
            plan: ProjectPlan = planner.generate_plan(
                query=query,
                context=planning_context,
                history_text="",
                max_stories=max_stories,
                metadata_brief=metadata_brief,
            )
        except BudgetExceededError:
            retry_context = _compact_document_for_planning(content, aggressive=True)
            if retry_context == planning_context:
                raise

            metadata["analysis_context_mode"] = "aggressive"
            metadata["analysis_context_chars"] = len(retry_context)
            metadata["analysis_context_tokens_estimate"] = _estimate_tokens(
                retry_context
            )
            logger.warning(
                "Analysis: retrying planner with aggressive context compaction for %s (%s chars, ~%s tokens)",
                metadata.get("display_name"),
                len(retry_context),
                _estimate_tokens(retry_context),
            )
            plan = planner.generate_plan(
                query=query,
                context=retry_context,
                history_text="",
                max_stories=max_stories,
                metadata_brief=metadata_brief,
            )
        if context_label:
            append_kb_label_to_plan(plan, context_label)
        if category_label:
            append_kb_label_to_plan(plan, category_label)

        if plan.structured_requirements and unified_label:
            try:
                from agent_jira.agents.graph_agent import GraphAgent
                from agent_jira.graphdb import graph_db

                if graph_db.is_enabled():
                    ga_req = GraphAgent(graph_db)
                    for req in plan.structured_requirements:
                        ga_req.upsert_requirement(
                            req_id=req.req_id,
                            text=req.text,
                            source_doc_id=unified_label,
                        )
            except Exception:
                logger.warning(
                    "Analysis: failed to persist requirements", exc_info=True
                )

        plan_payload = plan.to_dict()
        plan_markdown = render_project_plan(plan)
        plan_has_stories = has_user_stories(plan)

        size_human = metadata.get("size_human") or _human_size_from_kb(
            metadata.get("size_kb")
        )
        if size_human:
            metadata.setdefault("size_human", size_human)
        if "char_count" in metadata:
            metadata.setdefault("chars", metadata["char_count"])
            metadata.setdefault("characters", metadata["char_count"])
        doc_type_label_val = _doc_type_label(
            metadata.get("doc_type"), metadata.get("extension")
        )
        metadata["type"] = doc_type_label_val
        if category_label:
            metadata.setdefault("category", category_label)
        if context_label:
            metadata.setdefault("jira_label", context_label)

        info_lines: List[str] = []
        preview = metadata.get("preview")
        if isinstance(preview, str) and preview.strip():
            info_lines.append("Introduzione")
            info_lines.append(preview.strip())

        def _collect_jira_results(labels: Sequence[str]) -> List[Dict[str, Any]]:
            collected: List[Dict[str, Any]] = []
            seen: set[str] = set()
            for lbl in labels:
                hits = get_jira_results_for_label(lbl, limit=50)
                for entry in hits:
                    key = entry.get("key") or entry.get("summary")
                    key_str = str(key or "")
                    if not key_str or key_str in seen:
                        continue
                    seen.add(key_str)
                    collected.append(entry)
            return collected

        labels_to_query = list(
            dict.fromkeys(
                label
                for label in (
                    [context_label] + list(metadata.get("jira_label_aliases", []))
                )
                if label
            )
        )
        logger.debug(
            "Ricerca Jira per KB: labels=%s (label=%s, stories=%s)",
            labels_to_query,
            unified_label,
            len(plan_payload.get("user_stories", []) or []),
        )
        existing_jira_results = (
            _collect_jira_results(labels_to_query) if jira_client_ready() else []
        )
        logger.info(
            "Analisi documento %s: recuperate %d issue Jira su label %s",
            metadata.get("display_name"),
            len(existing_jira_results),
            labels_to_query,
        )
        manual_required = bool(getattr(chat_service, "jira_manual_approval", False))
        # In multi-tenant mode, manual approval is always required: each tenant
        # owns its Jira workspace and must explicitly approve story creation
        # from the UI, regardless of the global env flag.
        if MULTI_TENANT_ENABLED:
            manual_required = True
        jira_status = build_jira_status(
            manual_required, plan_has_stories, bool(existing_jira_results)
        )

        response_payload = {
            "metadata": metadata,
            "summary": "\n".join(info_lines),
            "plan_markdown": plan_markdown,
            "plan": plan_payload,
            "jira": {
                "status": jira_status,
                "results": existing_jira_results,
                "manual_required": manual_required,
                "can_manual_sync": manual_required
                and jira_client_ready()
                and plan_has_stories,
            },
            "kb": {
                "from_kb": resolved_from_kb or bool(kb_override_path),
                "label": unified_label,
                "status": KB_ALREADY_PRESENT_STATUS
                if (resolved_from_kb or kb_override_path)
                else DEFAULT_KB_STATUS,
                "can_store": (not resolved_from_kb) and stored_file_path is not None,
                "upload_path": stored_file_path,
            },
            "duration": time.perf_counter() - start_time,
        }

        if cache and cache_key:
            try:
                cache.set(cache_key, response_payload)
            except Exception as exc:
                logger.warning("Cache set fallita per %s: %s", cache_key, exc)

        return response_payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Analysis Failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante l'analisi del documento: {str(exc)}",
        )


@router.post("/report")
def generate_report(payload: Dict[str, Any]) -> Dict[str, object]:
    plan = payload.get("plan")
    metadata = payload.get("metadata") or {}
    summary = payload.get("summary") or ""
    jira_results = payload.get("jira_results") or payload.get("jira") or []

    if not plan:
        raise HTTPException(
            status_code=400,
            detail="Nessun project plan disponibile per generare il report.",
        )

    try:
        plan_obj = coerce_project_plan(plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    doc_name = (
        metadata.get("original_name")
        or metadata.get("display_name")
        or metadata.get("file_name")
        or metadata.get("filename")
        or metadata.get("name")
        or "project-plan"
    )
    filename = f"{slugify(doc_name)}-report.pdf"
    body_html = build_project_plan_html(
        plan_obj,
        metadata=metadata,
        summary=summary,
        jira_results=jira_results,
    )
    html = render_report_html(body_html, title=doc_name)
    return {"html": html, "filename": filename}
