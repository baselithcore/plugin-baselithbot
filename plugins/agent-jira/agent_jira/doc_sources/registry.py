from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from .models import DocumentSourceError

SourceFactory = Callable[[], object]

_REGISTRY: List[Tuple[str, SourceFactory]] = []


def register_source(name: str, factory: SourceFactory) -> None:
    """
    Registra una factory per una sorgente documentale.

    Se il nome è già registrato viene sovrascritto, mantenendo l'ordine di registrazione.
    """

    normalized_name = (name or "").strip()
    if not normalized_name:
        raise ValueError("Il nome della sorgente non può essere vuoto.")
    if not callable(factory):
        raise TypeError("La factory della sorgente deve essere callable.")

    for idx, (existing_name, _) in enumerate(_REGISTRY):
        if existing_name == normalized_name:
            _REGISTRY[idx] = (normalized_name, factory)
            break
    else:
        _REGISTRY.append((normalized_name, factory))


def registered_sources() -> Sequence[str]:
    """Restituisce l'elenco dei nomi di sorgente registrati (ordine stabile)."""

    return [name for name, _ in _REGISTRY]


def create_document_sources(
    *, space_filter: Optional[List[str]] = None
) -> List[Tuple[str, object]]:
    """
    Istanzia le sorgenti documentali registrate.

    Args:
        space_filter: elenco opzionale di nomi da includere (case sensitive).

    Returns:
        Lista di tuple (nome, istanza sorgente).
    """

    allowed = {name.strip() for name in space_filter or [] if name and name.strip()}
    sources: List[Tuple[str, object]] = []

    for name, factory in _REGISTRY:
        if allowed and name not in allowed:
            continue
        try:
            instance = factory()
        except DocumentSourceError:
            raise
        except Exception as exc:  # pragma: no cover - errori runtime factory
            raise DocumentSourceError(
                f"Impossibile inizializzare la sorgente '{name}': {exc}"
            ) from exc

        if instance is None:
            continue
        sources.append((name, instance))

    return sources
