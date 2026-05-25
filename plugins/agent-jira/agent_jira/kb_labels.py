from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Union

# Canonical Jira document label: <nomedocumento>-<hashdocumento>
DOCUMENT_LABEL_PREFIX = "doc"
DOCUMENT_LABEL_HASH_LENGTH = 6
DOCUMENT_LABEL_MAX_LENGTH = 30
DOCUMENT_LABEL_MAX_SLUG_LENGTH = (
    DOCUMENT_LABEL_MAX_LENGTH - DOCUMENT_LABEL_HASH_LENGTH - 1
)

# Backward-compatible aliases kept for older graph/Jira data already produced.
KB_LABEL_PREFIX = DOCUMENT_LABEL_PREFIX
KB_LABEL_MAX_LENGTH = 50
DOC_LABEL_PREFIX = DOCUMENT_LABEL_PREFIX
DOC_LABEL_MAX_LENGTH = 50

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_HASHED_DOCUMENT_LABEL_RE = re.compile(
    rf"^[a-z0-9][a-z0-9-]*-[0-9a-f]{{{DOCUMENT_LABEL_HASH_LENGTH}}}$"
)
_PREFIXED_DOCUMENT_LABEL_RE = re.compile(
    rf"^{DOCUMENT_LABEL_PREFIX}-[0-9a-f]{{{DOCUMENT_LABEL_HASH_LENGTH}}}$"
)
_SHORT_TOKEN_ALLOWLIST = {"ai", "bi", "qa", "ui", "ux"}
_STOPWORDS = {
    "a",
    "ad",
    "al",
    "alla",
    "alle",
    "con",
    "da",
    "dal",
    "dalla",
    "dalle",
    "dei",
    "del",
    "della",
    "delle",
    "di",
    "e",
    "ed",
    "from",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "nel",
    "nella",
    "nelle",
    "per",
    "su",
    "the",
    "to",
    "un",
    "una",
    "uno",
}


def _hash_source(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:DOCUMENT_LABEL_HASH_LENGTH]


def _normalize_source_name(value: Union[str, Path]) -> str:
    raw_value = str(value or "").strip()
    raw_name = Path(raw_value).stem if raw_value else ""
    normalized = _SLUG_PATTERN.sub("-", raw_name.lower()).strip("-")
    return normalized or "documento"


def _shorten_source_name(source_name: str, *, max_length: int) -> str:
    tokens = [token for token in source_name.split("-") if token]
    if not tokens:
        return "documento"

    def _is_meaningful(token: str) -> bool:
        return (
            token.isdigit()
            or len(token) > 3
            or token in _SHORT_TOKEN_ALLOWLIST
            or any(ch.isdigit() for ch in token)
        ) and token not in _STOPWORDS

    meaningful_tokens = [token for token in tokens if _is_meaningful(token)]
    if not meaningful_tokens:
        meaningful_tokens = tokens

    first_token = tokens[0]
    prioritized_tokens = meaningful_tokens
    if first_token not in _STOPWORDS:
        prioritized_tokens = [first_token] + [
            token for token in meaningful_tokens if token != first_token
        ]

    shortened: list[str] = []
    current_length = 0
    for token in prioritized_tokens:
        remaining = max_length - current_length - (1 if shortened else 0)
        if remaining <= 0:
            break
        if len(token) <= remaining:
            shortened.append(token)
            current_length += len(token) + (1 if len(shortened) > 1 else 0)
            continue
        if not shortened:
            shortened.append(token[:remaining].rstrip("-"))
        break

    compact = "-".join(part for part in shortened if part).strip("-")
    return compact or source_name[:max_length].rstrip("-") or "documento"


def _build_hashed_label(
    prefix: str,
    slug_source: str,
    digest_source: str,
    fallback_slug: str,
    max_length: int,
) -> str:
    slug = _SLUG_PATTERN.sub("-", slug_source.lower()).strip("-") or fallback_slug
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:6]

    prefix_part = f"{prefix}-" if prefix else ""
    hash_part = f"-{digest}" if digest else ""
    available_for_slug = max_length - len(prefix_part) - len(hash_part)

    if len(slug) > available_for_slug:
        slug = slug[:available_for_slug].rstrip("-")

    return f"{prefix_part}{slug}{hash_part}"


def _build_canonical_document_label(source_name: str) -> str:
    return _build_hashed_label(
        "",
        _shorten_source_name(source_name, max_length=DOCUMENT_LABEL_MAX_SLUG_LENGTH),
        f"document::{source_name}",
        fallback_slug="documento",
        max_length=DOCUMENT_LABEL_MAX_LENGTH,
    )


def _build_full_canonical_document_label(source_name: str) -> str:
    return _build_hashed_label(
        "",
        source_name,
        f"document::{source_name}",
        fallback_slug="documento",
        max_length=KB_LABEL_MAX_LENGTH,
    )


def _build_prefixed_document_label(source_name: str) -> str:
    return f"{DOCUMENT_LABEL_PREFIX}-{_hash_source(f'document::{source_name}')}"


def build_kb_label(path: Path) -> str:
    """Restituisce la label documento canonica condivisa con Jira e graph."""

    return _build_canonical_document_label(_normalize_source_name(path))


def build_doc_label(name: str, digest_source: str | None = None) -> str:
    """Restituisce la label documento canonica per analisi one-shot e KB."""

    source_name = _normalize_source_name(digest_source or name)
    return _build_canonical_document_label(source_name)


def build_legacy_kb_label(path: Path) -> str:
    """Genera la label storica <slug>-<hash> usata prima della convenzione doc-<hash>."""

    source_name = _normalize_source_name(path)
    return _build_hashed_label(
        "",
        source_name,
        f"kb::{source_name}",
        fallback_slug="documento",
        max_length=KB_LABEL_MAX_LENGTH,
    )


def build_legacy_doc_label(name: str, digest_source: str | None = None) -> str:
    """Genera la variante legacy delle analisi one-shot per compatibilità in lettura."""

    source_name = _normalize_source_name(digest_source or name)
    return _build_hashed_label(
        "",
        source_name,
        f"analysis::{source_name}",
        fallback_slug="documento",
        max_length=DOC_LABEL_MAX_LENGTH,
    )


def build_prefixed_doc_label(name: str, digest_source: str | None = None) -> str:
    """Genera l'alias legacy doc-<hash> mantenuto solo per compatibilità in lettura."""

    source_name = _normalize_source_name(digest_source or name)
    return _build_prefixed_document_label(source_name)


def build_document_label_candidates(
    source: Union[str, Path], digest_source: str | None = None
) -> list[str]:
    """Ritorna label canonica e alias legacy, in ordine di preferenza."""

    if isinstance(source, Path):
        source_name = _normalize_source_name(source)
        labels = [
            build_kb_label(source),
            _build_full_canonical_document_label(source_name),
            _build_prefixed_document_label(source_name),
            build_legacy_kb_label(source),
            build_legacy_doc_label(source.name, digest_source),
        ]
    else:
        source_name = _normalize_source_name(digest_source or source)
        labels = [
            build_doc_label(source, digest_source),
            _build_full_canonical_document_label(source_name),
            _build_prefixed_document_label(source_name),
            build_legacy_kb_label(Path(source)),
            build_legacy_doc_label(source, digest_source),
        ]
    return list(dict.fromkeys(label for label in labels if label))


def is_canonical_document_label(label: str) -> bool:
    candidate = (label or "").strip().lower()
    return bool(
        _HASHED_DOCUMENT_LABEL_RE.fullmatch(candidate)
        and not _PREFIXED_DOCUMENT_LABEL_RE.fullmatch(candidate)
    )


def is_supported_document_label(label: str) -> bool:
    candidate = (label or "").strip().lower()
    return bool(
        candidate
        and (
            candidate.startswith(("knowledge-base-", "kb-"))
            or _HASHED_DOCUMENT_LABEL_RE.fullmatch(candidate)
            or _PREFIXED_DOCUMENT_LABEL_RE.fullmatch(candidate)
        )
    )


__all__ = [
    "DOCUMENT_LABEL_HASH_LENGTH",
    "DOCUMENT_LABEL_MAX_LENGTH",
    "DOCUMENT_LABEL_PREFIX",
    "build_doc_label",
    "build_document_label_candidates",
    "build_kb_label",
    "build_prefixed_doc_label",
    "build_legacy_doc_label",
    "build_legacy_kb_label",
    "is_canonical_document_label",
    "is_supported_document_label",
    "KB_LABEL_PREFIX",
    "KB_LABEL_MAX_LENGTH",
    "DOC_LABEL_PREFIX",
    "DOC_LABEL_MAX_LENGTH",
]
