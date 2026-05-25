"""Reciprocal Rank Fusion + edizione/version mix annotation."""

from __future__ import annotations

from typing import Any


def merge_hits_rrf(
    per_query_hits: list[list[dict[str, Any]]],
    *,
    limit: int,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion su liste di hits da query multiple.

    Reciprocal Rank Fusion (TREC, k=60 default) combina ranking eterogenei senza
    richiedere che gli score siano comparabili tra liste. Dedup per `point_id`;
    la prima occorrenza vince per i campi `payload`/`score_*`.
    """
    if not per_query_hits:
        return []
    if len(per_query_hits) == 1:
        return per_query_hits[0][:limit]

    fused: dict[Any, dict[str, Any]] = {}
    fused_score: dict[Any, float] = {}

    for hits in per_query_hits:
        for rank, h in enumerate(hits):
            key = h.get("point_id") or h.get("id") or h.get("document_id"), h.get("chunk_index")
            if key[0] is None:
                text_sample = str(h.get("text") or h.get("content") or "")[:200]
                key = ("txt", text_sample)
            fused_score[key] = fused_score.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in fused:
                fused[key] = h

    ranked = sorted(fused.items(), key=lambda kv: fused_score[kv[0]], reverse=True)
    return [h for _, h in ranked[:limit]]


def _extract_edizione(hit: dict[str, Any]) -> str | None:
    """Estrai un'etichetta di edizione dal payload dell'hit per audit mix-versions.

    Cerca in ordine: `edizione-iso` → `edizione` → `edizione-riferimento` → `versione`.
    Ritorna None se nessuno è presente (hit senza info di versioning).
    """
    payload = hit.get("payload") or hit
    for k in ("edizione-iso", "edizione", "edizione-riferimento", "versione"):
        v = payload.get(k)
        if v:
            return str(v)
    return None


def annotate_mix_edizioni(
    hits: list[dict[str, Any]], *, prefer_vigente_applied: bool = False
) -> list[dict[str, Any]]:
    """Annota ogni hit con `edizione_audit`: etichetta edizione + flag mix.

    Se il set di edizioni distinte nei top hits > 1, ogni hit riceve
    `edizione_audit.mix_versions = True`. L'agente RAG, vedendo il flag nel
    payload, segnala l'utente.

    Quando ``prefer_vigente_applied=True`` (il caller ha già escluso a
    livello di retrieval gli stati ``superata``/``abrogata``), il mix
    residuo è composto da edizioni distinte tutte considerate vigenti.
    Lo segnaliamo con ``mix_kind='vigenti_distinti'`` per distinguere il
    caso legittimo (più documenti vigenti che coesistono — es. norme
    speciali vs generali) dal mix sospetto (versioni storiche
    accavallate). L'agente può adattare la wording dell'avviso.
    """
    edizioni = [e for e in (_extract_edizione(h) for h in hits) if e]
    distinct = sorted(set(edizioni))
    mix = len(distinct) > 1
    mix_kind = ""
    if mix:
        mix_kind = "vigenti_distinti" if prefer_vigente_applied else "versioni_diverse"
    for h in hits:
        edz = _extract_edizione(h)
        h["edizione_audit"] = {
            "edizione": edz,
            "mix_versions": mix,
            "mix_kind": mix_kind,
            "prefer_vigente_applied": prefer_vigente_applied,
            "all_distinct": distinct,
        }
    return hits
