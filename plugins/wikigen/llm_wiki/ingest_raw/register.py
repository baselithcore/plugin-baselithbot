"""Inferenza ``doc_register`` da ``source_type``.

Il classificatore LLM dell'ingest pipeline assegna a ogni source un
``source_type`` libero (`whitepaper`, `runbook`, `ADR`, `sentenza`,
`articolo`, `manuale`, ecc.). Questa tassonomia è ricca ma rumorosa:
per il filtro upstream del retrieval e l'iniezione di un signal
deterministico nel CONTESTO bastano **tre classi**:

- ``operational`` — manuali, runbook, ADR, spec API, README di codice,
  procedure step-by-step.
- ``conceptual`` — whitepaper, articoli divulgativi, executive summary,
  brochure, presentazioni strategiche, libri.
- ``mixed`` — documenti che esibiscono entrambe le componenti
  (es. tutorial articolato).

Una pagina di vault con ``doc_register=conceptual`` deve essere usata
con un prompt che vieta la fabbricazione di procedure operative; una
``operational`` può ospitare comandi/snippet verbatim. Il RAG agent
inietta la classe nel chunk header (``Registro:`` + spiegazione)
così il modello la vede ad ogni turn — backup deterministico in
caso di mismatch con la classificazione regex del CONTESTO.

Il mapping è euristico e tollerante: input ignoto / vuoto → ``unknown``
(no signal). Non spinge mai a buttare via il chunk: il filtro upstream
è un boost, non una hard-filter, per evitare cataclismi di retrieval.
"""

from __future__ import annotations

from typing import Final

# Mapping {token normalizzato → register}. La chiave è confrontata in
# lowercase. Token più specifici prima dei generici per evitare
# misclassificazioni.
_REGISTER_MAP: Final[dict[str, str]] = {
    # operational
    "runbook": "operational",
    "playbook": "operational",
    "adr": "operational",
    "rfc": "operational",
    "spec": "operational",
    "specifica": "operational",
    "manuale": "operational",
    "manual": "operational",
    "readme": "operational",
    "tutorial": "operational",
    "guida": "operational",
    "guide": "operational",
    "howto": "operational",
    "how-to": "operational",
    "procedura": "operational",
    "procedure": "operational",
    "api": "operational",
    "openapi": "operational",
    "swagger": "operational",
    "post-mortem": "operational",
    "postmortem": "operational",
    "rca": "operational",
    "incident": "operational",
    # conceptual
    "whitepaper": "conceptual",
    "white-paper": "conceptual",
    "ebook": "conceptual",
    "e-book": "conceptual",
    "book": "conceptual",
    "libro": "conceptual",
    "articolo": "conceptual",
    "article": "conceptual",
    "brochure": "conceptual",
    "executive": "conceptual",
    "executive-summary": "conceptual",
    "summary": "conceptual",
    "presentation": "conceptual",
    "presentazione": "conceptual",
    "slide": "conceptual",
    "report": "conceptual",
    "vision": "conceptual",
    "strategy": "conceptual",
    "strategia": "conceptual",
    "policy": "conceptual",
    "case-study": "conceptual",
    "case_study": "conceptual",
    "casestudy": "conceptual",
    "blog": "conceptual",
    "research": "conceptual",
    "ricerca": "conceptual",
    "paper": "conceptual",
    # best-practices / industry-leader content lives in the conceptual
    # register: prose narrative without verbatim commands or step-by-step
    # procedures. Without these tokens classifying as conceptual, queries
    # like "come costruire X?" against a whitepaper trigger the operational
    # schema and the LLM fabricates plausible-but-ungrounded prerequisites.
    "best_practices": "conceptual",
    "best-practices": "conceptual",
    "bestpractices": "conceptual",
    "industry": "conceptual",
    "industry-leaders": "conceptual",
    "leadership": "conceptual",
    "thought-leadership": "conceptual",
    "thoughtleadership": "conceptual",
    "essay": "conceptual",
    "saggio": "conceptual",
    "playbook-strategico": "conceptual",  # NB: nudo "playbook" è operational
    "framework-strategico": "conceptual",
    # legal/normativo: trattati come operational (testo normativo è applicabile)
    "sentenza": "operational",
    "legge": "operational",
    "regolamento": "operational",
    "circolare": "operational",
    "decreto": "operational",
    "normativa": "operational",
}


def infer_doc_register(source_type: str | None) -> str:
    """Mappa un ``source_type`` libero a ``operational/conceptual/mixed/unknown``.

    Strategia: split per word boundary, lookup di ogni token nel mapping.
    Se entrambi i registri appaiono (es. "manual whitepaper") → ``mixed``.
    Se nessun token mappa → ``unknown`` (segnale neutro a valle).
    Case-insensitive, trim, tollerante a separatori ``-`` / ``_`` / ``.``.
    """
    if not source_type or not source_type.strip():
        return "unknown"
    normalized = source_type.lower().strip()
    # Split su separatori comuni mantenendo anche la chiave intera (può
    # essere multi-parola con trattini, es. "white-paper").
    tokens = {normalized}
    for sep in ("-", "_", "/", ".", " "):
        for piece in normalized.split(sep):
            piece = piece.strip()
            if piece:
                tokens.add(piece)

    found: set[str] = set()
    for tok in tokens:
        reg = _REGISTER_MAP.get(tok)
        if reg:
            found.add(reg)
    if not found:
        return "unknown"
    if len(found) == 1:
        return next(iter(found))
    return "mixed"


def register_hint(register: str) -> str:
    """Frase breve da iniettare nel chunk header per orientare il modello.

    Output deterministico: il modello impara a vedere la stringa esatta
    e ad allineare il proprio registro di risposta. Vuoto su ``unknown``
    (no signal).
    """
    mapping = {
        "operational": (
            "documento operativo (runbook/spec/manuale). "
            "Comandi/snippet/procedure possono essere citati verbatim "
            "se presenti nel chunk."
        ),
        "conceptual": (
            "documento concettuale/strategico (whitepaper/articolo/"
            "brochure). NON dedurre comandi, procedure, snippet di "
            "codice da prosa narrativa; cita principi, definizioni, "
            "raccomandazioni che il testo formula esplicitamente."
        ),
        "mixed": (
            "documento misto (parte operativa + parte concettuale). "
            "Distingui chiaramente le due aree nella risposta; non "
            "miscelare procedure verbatim con principi alti."
        ),
    }
    return mapping.get(register, "")


__all__ = ["infer_doc_register", "register_hint"]
