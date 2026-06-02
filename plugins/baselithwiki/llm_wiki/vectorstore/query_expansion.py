"""Query expansion domain-specific per il wiki assicurativo/legale italiano.

Scopo: espandere la query utente con sinonimi, varianti contrattuali e termini
tecnici correlati prima del retrieval, per aumentare recall su domande che
usano lessico divulgativo contro un corpus in registro contrattuale (e
viceversa).

Esempio: "cosa non copre" → anche cerca "esclusioni", "delimitazioni",
"rischi esclusi", "limiti di indennizzo".

Architettura:
- Dizionario statico curato a mano (evita round-trip LLM in hot path).
- Matching **case-insensitive** sull'intera query (non token-level): individua
  la locuzione più lunga che combacia, espande con le varianti.
- Output: lista di query (incluso l'originale). `expand()` di una query già
  priva di match ritorna `[query]`.
- Caller responsabile del merge dei risultati (tipicamente RRF o union + dedup).

Design scelte:
- **Statico, non LLM-based**: 100x più veloce; sufficiente per il domain
  coverage attuale. Per migrazione futura a LLM-rewriter, mantenere la stessa
  API `expand(query, max_variants=...) -> list[str]`.
- **Italian-only**: i set informativi sono in italiano; non applichiamo sinonimi
  inglesi se non per termini tecnici latinizzati già in uso nel vault
  (claims-made, loss-occurrence).
- **Variants, not rewrites**: la funzione aggiunge frasi equivalenti; non
  elimina l'originale, così il reranker conserva il segnale diretto della query
  utente.
"""

from __future__ import annotations

import re
from typing import Final

# Dizionario di espansione: chiave = locuzione da matchare (lowercase),
# valore = lista di varianti semanticamente equivalenti nel dominio.
# L'ordine in value-list è irrilevante; duplicati sono tollerati e deduplicati a valle.
_EXPANSIONS: Final[dict[str, tuple[str, ...]]] = {
    # Copertura / esclusione
    "cosa non copre": (
        "esclusioni",
        "delimitazioni",
        "rischi esclusi",
        "rischi non assicurati",
        "limiti di indennizzo",
        "casi in cui la garanzia non opera",
    ),
    "cosa copre": (
        "oggetto dell'assicurazione",
        "rischi coperti",
        "prestazioni garantite",
        "garanzie prestate",
        "operatività della garanzia",
    ),
    "esclusioni": (
        "rischi esclusi",
        "delimitazioni",
        "cosa non copre",
        "rischi non assicurati",
    ),
    "delimitazioni": ("esclusioni", "cosa non copre", "casi di non operatività"),
    # Importi a carico Assicurato
    "franchigia": (
        "importo a carico dell'Assicurato",
        "scoperto minimo",
        "quota fissa non indennizzata",
    ),
    "scoperto": (
        "percentuale a carico dell'Assicurato",
        "quota percentuale del danno non indennizzata",
        "minimo non indennizzabile",
    ),
    "massimale": (
        "limite di indennizzo",
        "tetto di esposizione della Società",
        "somma massima garantita",
    ),
    "sotto-limite": (
        "sottolimite",
        "limite particolare di indennizzo",
        "cap di indennizzo per sotto-garanzia",
    ),
    # Termini e tempi
    "carenza": (
        "periodo di carenza",
        "periodo di attesa",
        "tempo di franchigia temporale",
        "periodo iniziale di non operatività",
    ),
    "prescrizione": (
        "termine di prescrizione",
        "decadenza del diritto",
        "art. 2952 CC",
    ),
    "decorrenza": (
        "effetto del contratto",
        "inizio della copertura",
        "data di effetto",
    ),
    "recesso": ("scioglimento del contratto", "disdetta", "risoluzione del contratto"),
    # Sinistro
    "denuncia": (
        "comunicazione del sinistro",
        "notifica del sinistro",
        "denuncia di sinistro",
        "art. 1913 CC",
    ),
    "sinistro": ("evento dannoso", "fatto generatore del danno", "evento coperto"),
    "indennizzo": (
        "liquidazione del danno",
        "somma liquidata",
        "risarcimento (Sezioni Danni)",
        "pagamento a carico della Società",
    ),
    # Regole e istituti
    "regola proporzionale": (
        "art. 1907 CC",
        "proporzionale in caso di sottoassicurazione",
        "riduzione proporzionale dell'indennizzo",
    ),
    "rivalsa": (
        "azione di rivalsa",
        "regresso",
        "surroga della Società ex art. 1916 CC",
    ),
    "surroga": ("surrogazione della Società", "rivalsa", "art. 1916 CC"),
    "aggravamento del rischio": ("art. 1898 CC", "mutamento del rischio"),
    "altre assicurazioni": (
        "coassicurazione indiretta",
        "art. 1910 CC",
        "pluralità di coperture",
    ),
    # Forme di assicurazione
    "valore intero": (
        "art. 1907 CC",
        "forma a valore pieno",
        "valore integrale dei beni",
    ),
    "primo rischio": (
        "primo rischio assoluto",
        "deroga all'art. 1907 CC",
        "senza regola proporzionale",
    ),
    # Sezioni / prodotti
    "rc casa": ("responsabilità civile vita privata", "danni a terzi", "capofamiglia"),
    "rc": ("responsabilità civile", "danni cagionati a terzi"),
    "incendio": ("danni da fuoco", "combustione con sviluppo di fiamma"),
    "furto": ("sottrazione illecita", "impossessamento fraudolento altrui"),
    "terremoto": ("evento sismico", "scossa tellurica", "sisma"),
    "alluvione": ("esondazione", "straripamento di corsi d'acqua"),
    "allagamento": ("ruscellamento", "accumulo esterno di acqua da eventi atmosferici"),
    # Documenti
    "dip": ("Documento Informativo Precontrattuale", "IPID"),
    "dip aggiuntivo": ("DIP Aggiuntivo Danni", "documento integrativo precontrattuale"),
    "condizioni generali": ("Condizioni di Assicurazione", "CdA", "CGA"),
    "condizioni di assicurazione": (
        "CdA",
        "CGA",
        "Condizioni Generali di Assicurazione",
    ),
    "norme tecniche assuntive": ("NTA", "regole di sottoscrizione", "norme assuntive"),
    # Contraente / assicurato
    "assicurato": (
        "persona nel cui interesse è stipulato il contratto",
        "beneficiario della copertura",
    ),
    "contraente": ("sottoscrittore del contratto", "persona che stipula la Polizza"),
}


# Ordinamento: dal match più lungo al più corto.
# Serve per matchare "cosa non copre" prima di "copre" isolato.
_SORTED_KEYS: Final[list[str]] = sorted(_EXPANSIONS.keys(), key=len, reverse=True)


_WORD_RE: Final[re.Pattern[str]] = re.compile(r"\w+", re.UNICODE)


def _normalized(s: str) -> str:
    return " ".join(_WORD_RE.findall(s.lower()))


def expand(query: str, *, max_variants: int = 4) -> list[str]:
    """Espande `query` con fino a `max_variants` varianti domain-specific.

    Return:
        Lista di query. Il primo elemento è sempre la query originale.
        Duplicati rimossi preservando l'ordine; max `max_variants + 1` elementi.

    Strategy:
        - Cerca la locuzione matchante più lunga nel dizionario (word-level).
        - Per ogni match, iniettare le varianti sostituendo la locuzione.
        - Se match multipli, combinare produce max `max_variants` varianti.
    """
    if not query or not query.strip():
        return [query]

    normalized = _normalized(query)
    results: list[str] = [query.strip()]
    seen: set[str] = {_normalized(query)}
    budget = max_variants

    for key in _SORTED_KEYS:
        if budget <= 0:
            break
        if key not in normalized:
            continue
        for variant in _EXPANSIONS[key]:
            if budget <= 0:
                break
            # Sostituzione case-insensitive rispettando i word boundary.
            pattern = re.compile(r"\b" + re.escape(key) + r"\b", re.IGNORECASE)
            expanded = pattern.sub(variant, query).strip()
            if not expanded:
                continue
            norm = _normalized(expanded)
            if norm in seen:
                continue
            seen.add(norm)
            results.append(expanded)
            budget -= 1

    return results


def is_expandable(query: str) -> bool:
    """Helper: True se `query` contiene almeno una locuzione espandibile."""
    if not query:
        return False
    normalized = _normalized(query)
    return any(k in normalized for k in _SORTED_KEYS)
