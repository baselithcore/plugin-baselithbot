# app/nlp.py
from __future__ import annotations

import sys
from functools import lru_cache
from typing import Dict, Optional

try:  # pragma: no cover - import guard per ambienti senza spaCy
    import spacy
    from spacy.language import Language
except ModuleNotFoundError:  # pragma: no cover - gestito a runtime
    spacy = None  # type: ignore[assignment]
    Language = None  # type: ignore[assignment]

from agent_jira.config import ENABLE_SPACY_DOCUMENTS, SPACY_FALLBACK_LANGUAGE, SPACY_MODEL


def _log(message: str) -> None:
    print(f"[spacy] {message}", file=sys.stderr)


@lru_cache(maxsize=1)
def get_spacy_pipeline() -> Optional["Language"]:
    """Restituisce (ed eventualmente carica) la pipeline spaCy configurata."""

    if not ENABLE_SPACY_DOCUMENTS:
        return None

    if spacy is None:
        _log(
            "❌ Libreria spaCy non disponibile. Installa il pacchetto per abilitare le funzionalità NLP."
        )
        return None

    try:
        nlp = spacy.load(SPACY_MODEL)
    except OSError as exc:
        fallback_language = SPACY_FALLBACK_LANGUAGE or (
            SPACY_MODEL.split("_", 1)[0] if SPACY_MODEL else "en"
        )
        _log(
            f"⚠️ Modello '{SPACY_MODEL}' non disponibile ({exc}). Tentativo fallback con pipeline vuota '{fallback_language}'."
        )
        try:
            nlp = spacy.blank(fallback_language)
            if not nlp.has_pipe("sentencizer"):
                nlp.add_pipe("sentencizer")
        except Exception as blank_exc:  # pragma: no cover - fallback raro
            _log(
                f"❌ Impossibile creare pipeline spaCy di fallback '{fallback_language}': {blank_exc}"
            )
            return None
    except Exception as exc:  # pragma: no cover - errori imprevisti
        _log(f"❌ Errore inatteso caricando il modello spaCy '{SPACY_MODEL}': {exc}")
        return None
    else:
        if not (
            nlp.has_pipe("parser")
            or nlp.has_pipe("senter")
            or nlp.has_pipe("sentencizer")
        ):
            try:
                nlp.add_pipe("sentencizer")
            except Exception as exc:  # pragma: no cover - molto raro
                _log(
                    f"⚠️ Impossibile aggiungere il sentencizer alla pipeline spaCy: {exc}"
                )

    return nlp


def is_spacy_available() -> bool:
    """Permette di verificare rapidamente se spaCy è utilizzabile."""

    return get_spacy_pipeline() is not None


def extract_spacy_metadata(
    text: str,
    *,
    max_entities: int = 8,
) -> Dict[str, str]:
    """Deriva metadati testuali di supporto tramite spaCy."""

    nlp = get_spacy_pipeline()
    if nlp is None:
        return {}

    try:
        doc = nlp(text)
    except Exception as exc:  # pragma: no cover - evita crash in fallback
        _log(f"⚠️ Elaborazione spaCy fallita: {exc}")
        return {}

    metadata: Dict[str, str] = {}

    language = getattr(nlp, "lang", None) or "unknown"
    metadata["spacy_language"] = language

    model_name = nlp.meta.get("name") if hasattr(nlp, "meta") else None
    metadata["spacy_model"] = model_name or SPACY_MODEL or "unknown"

    token_count = sum(1 for token in doc if not token.is_space)
    metadata["spacy_token_count"] = str(token_count)

    sentence_count = sum(1 for _ in doc.sents)
    metadata["spacy_sentence_count"] = str(sentence_count)

    unique_entities = []
    seen = set()
    for ent in doc.ents:
        text_value = " ".join(ent.text.strip().split())
        if not text_value:
            continue
        label = ent.label_.strip() if ent.label_ else ""
        descriptor = f"{text_value} ({label})" if label else text_value
        dedupe_key = descriptor.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique_entities.append(descriptor)
        if len(unique_entities) >= max_entities:
            break

    if unique_entities:
        metadata["spacy_entities"] = "; ".join(unique_entities)

    return metadata
