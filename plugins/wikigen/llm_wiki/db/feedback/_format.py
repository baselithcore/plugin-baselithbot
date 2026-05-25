"""Helpers di shaping per i record feedback + costanti di vocabolario.

Tenuti separati dal CRUD per evitare cicli (i moduli ``_crud`` /
``_stats`` importano da qui) e perché il vocabolario (status/tag
allowlist) è policy-level: cambia indipendentemente dal SQL.
"""

from __future__ import annotations

from typing import Any, Final

# Allowlist status (mirror della CHECK constraint mig 018). Manteniamo
# la copia Python così la validation lato app fallisce con un messaggio
# leggibile invece di un raw IntegrityError.
ALLOWED_STATUSES: Final[frozenset[str]] = frozenset(
    {"open", "triaged", "resolved", "dismissed"}
)

# Tag vocabolario suggerito. NON enforced lato DB (la colonna è
# ``TEXT[]`` libero), serve come hint UX + autocomplete FE. Coerente
# con le tassonomie usate da Helicone/Arize per qualifica errori RAG.
SUGGESTED_TAGS: Final[tuple[str, ...]] = (
    "hallucination",
    "missing_citation",
    "stale_doc",
    "out_of_scope",
    "wrong_source",
    "incomplete",
    "tone",
    "formatting",
)


def format_feedback(row: dict[str, Any]) -> dict[str, Any]:
    """Normalizza una riga DB → dict JSON-serializable.

    - UUID → str
    - timestamps → ISO-8601
    - ``tags=None`` → ``[]`` (la colonna DEFAULT empty array; difesa
      per record pre-018 letti da altre code path)
    """
    result = dict(row)
    for key in (
        "id",
        "tenant_id",
        "user_id",
        "message_id",
        "conversation_id",
        "resolved_by_user_id",
    ):
        if key in result and result[key] is not None:
            result[key] = str(result[key])
    for key in ("created_at", "resolved_at"):
        val = result.get(key)
        if val is not None and hasattr(val, "isoformat"):
            result[key] = val.isoformat()
    if result.get("tags") is None:
        result["tags"] = []
    return result


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Lowercase + dedup + slug-friendly. Mai None — UI accetta lista
    vuota = nessun tag, non semantica diversa."""
    if not tags:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in tags:
        if not isinstance(raw, str):
            continue
        t = raw.strip().lower()
        if not t or t in seen:
            continue
        # Tag con caratteri "strani" passano comunque (lasciamo che il
        # caller decida la policy); qui solo guard size sensata.
        if len(t) > 64:
            t = t[:64]
        seen.add(t)
        out.append(t)
    return out


__all__ = [
    "ALLOWED_STATUSES",
    "SUGGESTED_TAGS",
    "format_feedback",
    "normalize_tags",
]
