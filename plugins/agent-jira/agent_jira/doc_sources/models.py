from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class DocumentItem:
    """Rappresenta un documento sorgente da indicizzare."""

    uid: str
    content: str
    fingerprint: str
    metadata: Dict[str, str]


class DocumentSourceError(Exception):
    """Errore generico per le sorgenti dei documenti."""

    pass
