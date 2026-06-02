"""Dataclasses + confidence tiers + canonical id slugger."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Graphify confidence tiers (3-band classifier on a 0..1 score).
TIER_EXTRACTED = "EXTRACTED"  # >= 0.85, explicit quote + structural evidence
TIER_INFERRED = "INFERRED"  # 0.50–0.85, implied by context
TIER_AMBIGUOUS = "AMBIGUOUS"  # < 0.50, weak signal — kept but filtered by default

TIER_THRESHOLDS: list[tuple[float, str]] = [
    (0.85, TIER_EXTRACTED),
    (0.50, TIER_INFERRED),
    (0.0, TIER_AMBIGUOUS),
]


def confidence_to_tier(score: float) -> str:
    """Map a 0..1 confidence score to a graphify-style tier label."""
    s = max(0.0, min(1.0, float(score)))
    for threshold, tier in TIER_THRESHOLDS:
        if s >= threshold:
            return tier
    return TIER_AMBIGUOUS


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def canonical_entity_id(name: str, kind: str) -> str:
    """Deterministic slug for an entity node.

    ``"Unipol Assicurazioni" / "entity"`` → ``"entity:unipol-assicurazioni"``.
    Multiple surface forms with the same slug collapse to one node (handled
    via MERGE in Cypher).
    """
    slug = _SLUG_RE.sub("-", (name or "").strip().lower()).strip("-")
    if not slug:
        slug = "unnamed"
    return f"{kind.lower()}:{slug}"


@dataclass(slots=True)
class EntityRecord:
    id: str
    name: str
    kind: str
    aliases: list[str]


@dataclass(slots=True)
class RelationRecord:
    src_id: str
    dst_id: str
    kind: str
    confidence: float
    tier: str
    evidence: str
    page_id: str | None
