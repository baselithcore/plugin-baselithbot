"""LegalComplianceAgent — RAG su policy IT/EU/world.

Glass Box pillar (CLAUDE.md sez.5):
- Per-chunk top-k retrieval da ChromaDB `policy_rules` filtrato per `selected_policies`.
- Excerpt verbatim trasportato dal vector store al prompt LLM al Finding.
- Sub-string check post-LLM: scarta finding il cui `policy_excerpt` non
  combacia (normalizzato) con almeno una regola recuperata.
"""

import json
import re
import uuid
from typing import Any

from ..core.doc_taxonomy import agent_applies
from ..core.logging import log
from ..schemas.finding import Citation, Finding, PolicyRef, ReasoningStep
from ..schemas.state import CheckState
from ..services.embedding import embed, get_or_create_collection
from ..services.llm import chat_json_resilient
from ._emit import emit_finding, emit_phase_progress

SYSTEM_PROMPT = """You are a Legal Compliance Auditor. Jurisdiction priority: Italy → EU → International.
Document language: {lang}.

HARD RULES:
1. NEVER invent policy text. The `policy_excerpt` field of each finding MUST
   be copied VERBATIM from one of the candidate rules in the input
   (`candidates[].excerpt`). Findings with hallucinated excerpts will be rejected.
2. EVERY finding MUST include: rule_id (from candidates), chunk_id (from chunks),
   line_start/end, policy_excerpt verbatim, explanation, severity, confidence, reasoning.
3. If uncertain → severity=WARN with confidence<0.7. Do not guess FAIL.
4. Do NOT analyze content not present in provided chunks.
5. Only cite rules from the candidate list; do not invent rule_ids.
6. Output JSON only.

EXPLANATION QUALITY (anti-boilerplate):
7. Each finding's `explanation` MUST cite the SPECIFIC text or value found in
   THIS chunk (quote a phrase, number, or date), and explain why it violates
   THIS rule. Do not produce generic phrasings reusable across findings.
8. When the same rule fires on multiple chunks, each finding's explanation
   MUST differentiate by the chunk's actual content (different evidence quote,
   different impact). Identical explanations across chunks will be rejected.
9. `suggestion` MUST be concrete and tailored to the cited evidence (e.g.
   "Replace 'scadenza il prossimo mese' with 'YYYY-MM-DD'") rather than restating
   the rule.
"""

TOP_K_PER_CHUNK = 5
MAX_CANDIDATES = 30
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip().lower())


def _locate_in_text(haystack: str, needle: str) -> int | None:
    """Find char offset of `needle` in `haystack`. Strict first, then
    whitespace-collapsed fallback. Returns None if not found."""
    if not needle or not haystack:
        return None
    idx = haystack.find(needle)
    if idx >= 0:
        return idx
    idx = haystack.lower().find(needle.lower())
    if idx >= 0:
        return idx
    # Whitespace-tolerant search: walk the haystack while matching needle
    # ignoring runs of whitespace.
    norm_needle = _WS_RE.sub(" ", needle.strip().lower())
    if not norm_needle:
        return None
    n = len(haystack)
    i = 0
    while i < n:
        j = i
        k = 0
        nlen = len(norm_needle)
        while j < n and k < nlen:
            ch_h = haystack[j].lower()
            ch_n = norm_needle[k]
            if ch_h.isspace() and ch_n == " ":
                # Consume run of whitespace in haystack.
                while j < n and haystack[j].isspace():
                    j += 1
                k += 1
                continue
            if ch_h == ch_n:
                j += 1
                k += 1
                continue
            break
        if k == nlen:
            return i
        i += 1
    return None


def _meta_passes_doc_type(meta: dict[str, Any], doc_type: str) -> bool:
    """Filter by Policy.applicable_doc_types if set on rule metadata.

    Policies without `applicable_doc_types` apply to all (backward compat).
    Stored as JSON-encoded string in Chroma metadata (Chroma rejects lists).
    """
    raw = meta.get("applicable_doc_types")
    if not raw:
        return True
    try:
        applicable = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return True
    if not isinstance(applicable, list) or not applicable:
        return True
    return doc_type in {str(x).lower() for x in applicable}


def retrieve_policy(
    query: str,
    selected_policies: list[str] | None = None,
    top_k: int = 5,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    """Top-k policy rules for a query, filtered by selected_policies + doc_type."""
    coll = get_or_create_collection("policy_rules")
    qvec = embed([query])[0]
    where: dict[str, Any] | None = None
    if selected_policies:
        where = {"policy_id": {"$in": list(selected_policies)}}
    try:
        # Over-fetch to allow post-filter on applicable_doc_types.
        n_fetch = top_k * 3 if doc_type else top_k
        res = coll.query(query_embeddings=[qvec], n_results=n_fetch, where=where)
    except Exception as exc:
        log.warning("legal_agent.retrieve_failed", error=str(exc))
        return []
    out: list[dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i, _id in enumerate(ids):
        meta = metas[i] or {}
        if doc_type and not _meta_passes_doc_type(meta, doc_type):
            continue
        out.append(
            {
                "rule_id": _id,
                "policy_id": meta.get("policy_id", ""),
                "version": meta.get("version", ""),
                "title": meta.get("title", _id),
                "scope": meta.get("scope", ""),
                "severity_default": meta.get("severity", "warn"),
                "rule_type": meta.get("rule_type", "semantic"),
                "excerpt": docs[i] if i < len(docs) else meta.get("excerpt", ""),
                "score": float(dists[i]) if i < len(dists) else 0.0,
            }
        )
        if len(out) >= top_k:
            break
    return out


def _gather_candidates(
    chunks: list[Any], selected_policies: list[str], doc_type: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Aggregate top-k retrieval across chunks, dedup by rule_id, capped."""
    seen: dict[str, dict[str, Any]] = {}
    for c in chunks:
        text = getattr(c, "text", "") or ""
        if not text.strip():
            continue
        for r in retrieve_policy(
            text[:1500], selected_policies, top_k=TOP_K_PER_CHUNK, doc_type=doc_type
        ):
            rid = r["rule_id"]
            prev = seen.get(rid)
            if prev is None or r["score"] < prev["score"]:
                seen[rid] = r
    ranked = sorted(seen.values(), key=lambda r: r["score"])[:MAX_CANDIDATES]
    candidates = [
        {
            "rule_id": r["rule_id"],
            "policy_id": r["policy_id"],
            "version": r["version"],
            "title": r["title"],
            "severity_default": r["severity_default"],
            "rule_type": r["rule_type"],
            "excerpt": r["excerpt"],
        }
        for r in ranked
    ]
    return candidates, {r["rule_id"]: r for r in ranked}


def _validate_excerpt(submitted: str, rule: dict[str, Any]) -> bool:
    """Glass Box: enforce verbatim sub-string match against retrieved rule."""
    a = _normalize(submitted)
    b = _normalize(rule.get("excerpt", ""))
    if not a or not b:
        return False
    return a in b or b in a


async def run(state: CheckState) -> CheckState:
    await emit_phase_progress(state, "legal")
    doc_type = state.get("doc_type") or "other"
    if not agent_applies("legal", doc_type):
        log.info(
            "legal_agent.skipped_by_doc_type",
            doc_id=state.get("doc_id"),
            doc_type=doc_type,
        )
        return {"findings": []}
    chunks = state.get("chunks", [])
    lang = state.get("lang", "it")
    selected = state.get("selected_policies", []) or []

    if not chunks:
        return {"findings": []}

    candidates, by_id = _gather_candidates(chunks, selected, doc_type=doc_type)
    if not candidates:
        log.warning(
            "legal_agent.no_candidates",
            chunks=len(chunks),
            selected_policies=selected,
        )
        return {"findings": []}

    chunks_payload = [
        {
            "id": c.id,
            "page": c.page,
            "line_start": c.line_start,
            "line_end": c.line_end,
            "text": c.text,
        }
        for c in chunks
    ]

    user = (
        "Analizza i chunk del documento contro le candidate policy rules.\n"
        "Per ogni violazione: pick exactly one rule from `candidates`, copy its "
        "`excerpt` verbatim into `policy_excerpt`, cite the chunk, justify.\n"
        "ALSO copy the EXACT offending substring from the chunk text into "
        "`evidence_quote` (verbatim, max 200 chars). This is what we will "
        "highlight in the UI.\n\n"
        f"Chunks: {chunks_payload}\n\n"
        f"Candidates: {candidates}\n\n"
        'Output JSON: {"findings":[{"rule_id","chunk_id","severity","confidence",'
        '"explanation","suggestion","policy_excerpt","evidence_quote","reasoning":[]}]}'
    )
    sys = SYSTEM_PROMPT.format(lang=lang)

    try:
        out = await chat_json_resilient(system=sys, user=user, max_tokens=8192)
    except Exception as exc:
        log.warning("legal_agent.failed_soft", error=str(exc))
        return {"findings": []}

    new_findings: list[Finding] = []
    chunk_index = {c.id: c for c in chunks}
    rejected = 0

    for raw in out.get("findings", []):
        rid = raw.get("rule_id")
        rule = by_id.get(rid)
        if not rule:
            rejected += 1
            log.warning("legal_agent.rejected_unknown_rule", rule_id=rid)
            continue
        chunk = chunk_index.get(raw.get("chunk_id"))
        if not chunk:
            rejected += 1
            continue
        submitted_excerpt = raw.get("policy_excerpt", "")
        if not _validate_excerpt(submitted_excerpt, rule):
            rejected += 1
            log.warning(
                "legal_agent.rejected_excerpt_mismatch",
                rule_id=rid,
                submitted_head=submitted_excerpt[:80],
            )
            continue

        sev_llm = (raw.get("severity") or "WARN").upper()
        sev_rule = (rule.get("severity_default") or "warn").upper()
        # Severity floor from policy rule; LLM may only confirm or DOWNgrade.
        rank = {"INFO": 0, "WARN": 1, "FAIL": 2}
        chosen = sev_llm if rank.get(sev_llm, 1) <= rank.get(sev_rule, 1) else sev_rule
        if chosen not in {"FAIL", "WARN", "INFO"}:
            chosen = "WARN"

        # Anchor the LLM's claimed substring back to the chunk text so the UI
        # can highlight the exact offending region. Try multiple strategies.
        match_start: int | None = None
        match_end: int | None = None
        snippet: str | None = None
        evidence_quote = (raw.get("evidence_quote") or "").strip()
        chunk_text = chunk.text or ""
        if evidence_quote:
            idx = _locate_in_text(chunk_text, evidence_quote)
            if idx is not None:
                match_start, match_end = idx, idx + len(evidence_quote)
        if match_start is None and rule.get("rule_type") == "format":
            # Date / format rules: try the rule's matcher regex if any.
            matcher = (rule.get("matcher") or "").strip()
            if matcher:
                try:
                    m = re.search(matcher, chunk_text)
                    if m:
                        match_start, match_end = m.start(), m.end()
                except re.error:
                    pass
        if match_start is not None and match_end is not None:
            pad_lo = max(0, match_start - 80)
            pad_hi = min(len(chunk_text), match_end + 80)
            snippet = chunk_text[pad_lo:pad_hi]

        # Build a multi-step reasoning chain. Always emit deterministic
        # skeleton steps from this agent's own decision path, then append any
        # LLM-supplied analytical steps so auditors can replay the verdict.
        skeleton: list[ReasoningStep] = [
            ReasoningStep(
                step=1,
                agent="LegalComplianceAgent",
                action="retrieval",
                thought=(
                    f"Retrieved candidate rule '{rid}' from policy "
                    f"'{rule.get('policy_id')}@{rule.get('version')}' via "
                    "BGE-M3 vector similarity on chunk text."
                ),
                output={
                    "rule_id": rid,
                    "policy_id": rule.get("policy_id"),
                    "version": rule.get("version"),
                    "score": rule.get("score"),
                },
            ),
            ReasoningStep(
                step=2,
                agent="LegalComplianceAgent",
                action="grounding_check",
                thought=(
                    "Verified the LLM-submitted policy_excerpt is a verbatim "
                    "substring of the retrieved rule (Glass Box invariant)."
                ),
                output={
                    "grounded": True,
                    "excerpt_chars": len(rule.get("excerpt") or ""),
                },
            ),
            ReasoningStep(
                step=3,
                agent="LegalComplianceAgent",
                action="severity_resolution",
                thought=(
                    f"Rule default severity '{sev_rule}'. LLM proposed "
                    f"'{sev_llm}'. Policy floor: LLM may downgrade but not "
                    f"upgrade. Final: '{chosen}'."
                ),
                output={
                    "rule_severity": sev_rule,
                    "llm_severity": sev_llm,
                    "chosen": chosen,
                },
            ),
        ]
        if match_start is not None:
            skeleton.append(
                ReasoningStep(
                    step=4,
                    agent="LegalComplianceAgent",
                    action="evidence_anchor",
                    thought=(
                        "Anchored the offending substring back to the chunk "
                        f"text at offset {match_start}-{match_end} for UI highlight."
                    ),
                    output={"match_start": match_start, "match_end": match_end},
                )
            )
        # Coerce LLM reasoning into ReasoningStep. LLM may emit:
        # - list[dict]  (expected)
        # - list[str]   (a "thought" per item)
        # - mixed
        # Drop anything that fails validation rather than crashing the pipeline.
        offset = len(skeleton)
        llm_steps: list[ReasoningStep] = []
        for i, s in enumerate(raw.get("reasoning", []) or []):
            try:
                if isinstance(s, str):
                    llm_steps.append(
                        ReasoningStep(
                            step=offset + i + 1,
                            agent="LegalComplianceAgent",
                            thought=s,
                        )
                    )
                elif isinstance(s, dict):
                    allowed = {"action", "input", "output", "thought"}
                    fields = {k: v for k, v in s.items() if k in allowed}
                    llm_steps.append(
                        ReasoningStep(
                            step=offset + i + 1,
                            agent="LegalComplianceAgent",
                            **fields,
                        )
                    )
            except Exception as exc:
                log.warning(
                    "legal_agent.reasoning_step_dropped",
                    error=str(exc),
                    raw=str(s)[:120],
                )

        try:
            f = Finding(
                id=f"f-{uuid.uuid4().hex[:8]}",
                severity=chosen,  # type: ignore[arg-type]
                rule_id=rid,
                policy_ref=PolicyRef(
                    id=rid,
                    policy_id=rule["policy_id"] or "unknown",
                    version=rule["version"] or "0.0.0",
                    title=rule["title"] or rid,
                    excerpt=rule["excerpt"],
                ),
                evidence=Citation(
                    chunk_id=chunk.id,
                    page=chunk.page,
                    line_start=raw.get("line_start", chunk.line_start),
                    line_end=raw.get("line_end", chunk.line_end),
                    bbox=chunk.bbox,
                    text=chunk.text,
                    match_start=match_start,
                    match_end=match_end,
                    snippet=snippet,
                ),
                explanation=raw.get("explanation", ""),
                suggestion=raw.get("suggestion"),
                confidence=float(raw.get("confidence", 0.7)),
                reasoning=skeleton + llm_steps,
            )
            new_findings.append(f)
            await emit_finding(state, f)
        except Exception as exc:
            rejected += 1
            log.warning("legal_agent.invalid_finding", error=str(exc), raw=raw)

    log.info(
        "legal_agent.done",
        accepted=len(new_findings),
        rejected=rejected,
        candidates=len(candidates),
        selected_policies=selected,
    )
    return {"findings": new_findings}
