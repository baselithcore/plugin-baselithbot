"""Locale-aware lexicon loader for the BaselithMed plugin.

The loader returns the same in-memory shapes that
``differential_dx_agent`` currently hard-codes, so that wiring the agent
through ``load_symptom_lexicon(lang)`` becomes a one-line swap once a
second language ships. Until then the YAML files mirror the Python
constants byte-for-byte; the test suite proves that mirror is intact.

Two file kinds live in this package:
    * ``symptoms_{lang}.yaml`` — list of ``{trigger, canonical, icd10}``
      mappings (the order matters: multi-word triggers must precede their
      single-word substrings to win the substring match).
    * ``red_flags_{lang}.yaml`` — ``{keyword: message}`` pairs for the
      :class:`~plugins.baselithmed.safety.redflags.RedFlagEvaluator`.

YAML is loaded via :mod:`yaml` (PyYAML), already a transitive dependency
of the core stack. The loader caches per ``(lang, kind)`` so callers may
invoke it freely without re-reading files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final

import yaml

SymptomTriple = tuple[str, str, str | None]
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("it", "en")
DEFAULT_LANGUAGE: Final[str] = "it"

_LEXICON_DIR: Final[Path] = Path(__file__).resolve().parent


def _file_for(lang: str, kind: str) -> Path:
    return _LEXICON_DIR / f"{kind}_{lang}.yaml"


@lru_cache(maxsize=8)
def load_symptom_lexicon(lang: str = DEFAULT_LANGUAGE) -> tuple[SymptomTriple, ...]:
    """Return the ordered ``(trigger, canonical, icd10)`` symptom map.

    Raises :class:`FileNotFoundError` when no YAML exists for ``lang``.
    """
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language {lang!r}; "
            f"available: {', '.join(SUPPORTED_LANGUAGES)}"
        )
    path = _file_for(lang, "symptoms")
    if not path.exists():
        raise FileNotFoundError(f"Lexicon file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    triples: list[SymptomTriple] = []
    for entry in raw:
        trigger = entry["trigger"]
        canonical = entry["canonical"]
        icd10 = entry.get("icd10")
        triples.append((trigger, canonical, icd10))
    return tuple(triples)


@lru_cache(maxsize=8)
def load_red_flags(lang: str = DEFAULT_LANGUAGE) -> dict[str, str]:
    """Return ``{keyword: message}`` red-flag pairs for ``lang``."""
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language {lang!r}; "
            f"available: {', '.join(SUPPORTED_LANGUAGES)}"
        )
    path = _file_for(lang, "red_flags")
    if not path.exists():
        raise FileNotFoundError(f"Red-flag file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(raw)
