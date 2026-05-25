"""Numeric-claim guard — verifica deterministica dei dati quantitativi.

Implementa la difesa specifica richiesta dai criteri "LLM-as-a-Judge per
l'Allineamento": ogni valore quantitativo nella risposta del modello
(percentuale, durata, valuta, dimensione, numero in scala migliaia) deve
trovare riscontro letterale nel CONTESTO recuperato. Se l'answer dichiara
"latenza 30s" ma il CONTESTO non menziona mai né "30 s" né "30 secondi"
né "30000 ms", il claim è fabbricato.

Difesa deterministica (no LLM call). Più cheap e specifica del
``groundedness`` scorer LLM-as-judge: cattura solo claim numerici, ma
li cattura sempre, anche quando il judge è disabilitato per costo.

Pattern coperti:

- Percentuali           — ``30%``, ``2.5 %``
- Durate                — ``30s``, ``5 min``, ``2 h``, ``45 ms``
- Valute                — ``€100``, ``$5.99``, ``1500 EUR``
- Dimensioni            — ``2 GB``, ``500 MB``, ``1.5 TB``
- Numeri scala migliaia — ``1.500``, ``2,500`` (>= 1000)
- Numeri generici       — opt-in via ``include_generic=True`` (off di
  default per ridurre falsi positivi su anni / numerazione di sezioni).

La matching strategy estrae per ogni claim un *core* numerico (cifre +
opzionale separatore decimale) e una *unit family*. Un claim è
supportato se il CONTESTO contiene almeno una stringa con lo stesso core
+ unit family — la variazione di whitespace e separatore decimale
(``30s`` vs ``30 s``, ``2.5`` vs ``2,5``) non rompe il match.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

# Unit families. ``""`` = nessuna unità (numero standalone).
_PERCENT_UNITS = ("%",)
_TIME_UNITS = (
    "ms",
    "millisecond",
    "millisecondi",
    "s",
    "sec",
    "secondo",
    "secondi",
    "min",
    "minuto",
    "minuti",
    "minute",
    "minutes",
    "h",
    "ora",
    "ore",
    "hour",
    "hours",
    "d",
    "gg",
    "giorno",
    "giorni",
    "day",
    "days",
    "settimana",
    "settimane",
    "week",
    "weeks",
    "mese",
    "mesi",
    "month",
    "months",
    "anno",
    "anni",
    "year",
    "years",
)
_CURRENCY_UNITS = ("€", "$", "£", "eur", "usd", "gbp", "euro", "euros", "dollar", "dollari")
_BYTE_UNITS = (
    "b",
    "byte",
    "bytes",
    "kb",
    "kib",
    "mb",
    "mib",
    "gb",
    "gib",
    "tb",
    "tib",
    "pb",
    "kilobyte",
    "megabyte",
    "gigabyte",
    "terabyte",
)

# Map unit-lowercase → family.
_UNIT_FAMILY: dict[str, str] = {}
for _u in _PERCENT_UNITS:
    _UNIT_FAMILY[_u] = "percent"
for _u in _TIME_UNITS:
    _UNIT_FAMILY[_u] = "time"
for _u in _CURRENCY_UNITS:
    _UNIT_FAMILY[_u] = "currency"
for _u in _BYTE_UNITS:
    _UNIT_FAMILY[_u] = "byte"


# Cattura: numero (con eventuali separatori migliaia/decimali) + unità
# opzionale separata da whitespace facoltativo. La unit segue il numero
# in tutte le lingue supportate (it/en).
#
# Esempi: 30%, 2.5 %, €100, $5.99, 1500 EUR, 30s, 5 min, 2 GB.
#
# Esclusi deliberatamente: anni a 4 cifre standalone (1900..2099) —
# vedi ``_looks_like_year``; numerazione di sezioni "## 2 Foo" — il
# numero qui è sempre piccolo e senza unit ma il falso positivo è
# accettabile perché lo strip è opt-in (default OFF) e il warning
# elenca esplicitamente i token.
_NUMERIC_RE = re.compile(
    r"""
    (?P<currency_prefix>[€$£])?              # opzionale simbolo valuta prefisso
    \s*
    (?P<number>
        \d{1,3}(?:[., \s]\d{3})+        # 1.500 / 2,500 / 1 500 (>= 1000)
        (?:[.,]\d+)?                         # opzionale decimale
        |
        \d+(?:[.,]\d+)?                      # 30 / 2.5 / 0,75
    )
    \s*
    (?P<unit>
        %|€|\$|£|
        (?:ms|s|sec|secondi?|min|minut[oie]|minutes?|h|or[ae]|hours?|d|gg|giorn[oi]|days?|
           settiman[ae]|weeks?|mes[ei]|months?|ann[oi]|years?|
           eur|usd|gbp|euros?|dollar[oi]?|dollars?|
           kib|mib|gib|tib|kb|mb|gb|tb|pb|bytes?|kilobytes?|megabytes?|gigabytes?|terabytes?)
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class NumericClaim:
    """Singolo claim numerico estratto da un testo."""

    raw: str  # token verbatim come appariva nel testo
    core: str  # numero normalizzato senza separatori migliaia
    family: str  # percent|time|currency|byte|none
    unit: str  # unit lowercase (può essere "")
    position: int  # offset nel testo originale


@dataclass
class NumericGuardReport:
    answer_claims: list[NumericClaim] = field(default_factory=list)
    context_claims: list[NumericClaim] = field(default_factory=list)
    unsupported: list[NumericClaim] = field(default_factory=list)
    has_violations: bool = False

    def summary(self) -> str:
        if not self.has_violations:
            return "numeric guard ok"
        bad = ", ".join(sorted({c.raw.strip() for c in self.unsupported}))
        return f"numeric claim(s) senza riscontro nel CONTESTO: {bad}"


def _normalize_core(number_str: str) -> str:
    """Normalizza il core numerico per il match.

    Rimuove separatori delle migliaia (``.``, ``,``, NBSP, spazi) e
    converte il separatore decimale in ``.`` quando determinabile. Per
    pattern ambigui (``1,5`` può essere 1.5 o 1500) la euristica usa la
    convenzione che un solo separatore con 1-2 cifre dopo è decimale,
    un solo separatore con 3 cifre è migliaio. La regex di estrazione
    ha già fatto il grosso del lavoro tagliando spazi.
    """
    s = number_str.replace(" ", "").replace(" ", "")
    # Caso 1: contiene sia "." che "," → quello in fondo è decimale.
    if "." in s and "," in s:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
        return s
    # Caso 2: solo "," → decimale se 1-2 cifre dopo, migliaio se 3.
    if "," in s and "." not in s:
        last = s.rsplit(",", 1)[-1]
        if len(last) == 3 and s.count(",") >= 1:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
        return s
    # Caso 3: solo "." → simmetrico.
    if "." in s and "," not in s:
        last = s.rsplit(".", 1)[-1]
        if len(last) == 3 and s.count(".") >= 1:
            s = s.replace(".", "")
        return s
    return s


def _unit_family(unit_lower: str) -> str:
    """Mappa unità lowercase su famiglia. ``""`` per numeri standalone."""
    if not unit_lower:
        return "none"
    return _UNIT_FAMILY.get(unit_lower, "none")


def _looks_like_year(core: str, family: str, raw: str) -> bool:
    """Filtra anni a 4 cifre standalone (1900..2099).

    Falso positivo tipico: ``"il documento del 2024 indica…"`` produce
    un claim ``2024 / none`` mai presente come tale in un CONTESTO con
    formattazioni diverse. Senza filtro ogni answer che cita un anno
    fa scattare il guard.
    """
    if family != "none":
        return False
    if "." in core or "," in core:
        return False
    try:
        n = int(core)
    except ValueError:
        return False
    return 1900 <= n <= 2099 and raw.strip().isdigit()


def extract_numeric_claims(
    text: str,
    *,
    include_generic: bool = False,
    skip_years: bool = True,
) -> list[NumericClaim]:
    """Estrai i claim numerici da ``text``.

    ``include_generic`` controlla se i numeri standalone (senza unit
    riconoscibile) vengono inclusi: default OFF perché producono troppi
    falsi positivi su numerazione di sezione, conteggi banali ("3 punti"),
    ID. Attivare quando si vuole massimo recall (corpora con metriche
    nude tipo "throughput 1500" senza unit esplicita).
    """
    if not text:
        return []
    out: list[NumericClaim] = []
    for m in _NUMERIC_RE.finditer(text):
        prefix = (m.group("currency_prefix") or "").strip()
        number = m.group("number")
        unit = (m.group("unit") or "").strip().lower()
        if prefix and not unit:
            unit = prefix.lower()
        if not number:
            continue
        core = _normalize_core(number)
        family = _unit_family(unit)
        if family == "none" and not include_generic:
            continue
        raw = m.group(0)
        if skip_years and _looks_like_year(core, family, raw):
            continue
        out.append(
            NumericClaim(
                raw=raw,
                core=core,
                family=family,
                unit=unit,
                position=m.start(),
            )
        )
    return out


def _claim_supported(claim: NumericClaim, context_claims: Iterable[NumericClaim]) -> bool:
    """Un claim è supportato se il CONTESTO contiene la stessa coppia (core, family).

    Cross-family match non ammesso: ``5%`` nel claim ≠ ``5 minuti`` nel
    CONTESTO. ``family="none"`` è considerato compatibile con qualunque
    family quando il core coincide (es. answer dice "5%" e contesto
    dice "5"; conservativo, riduce falsi positivi).
    """
    for ctx in context_claims:
        if ctx.core != claim.core:
            continue
        if claim.family == ctx.family:
            return True
        if claim.family == "none" or ctx.family == "none":
            return True
    return False


def analyze(
    answer: str,
    context: str,
    *,
    include_generic: bool = False,
) -> NumericGuardReport:
    """Confronta i claim numerici di ``answer`` con quelli del ``context``.

    Per ogni claim numerico nella risposta, verifica che ``core`` +
    ``family`` siano presenti anche nel CONTESTO. Claim senza riscontro
    finiscono in ``unsupported``.
    """
    a_claims = extract_numeric_claims(answer, include_generic=include_generic)
    c_claims = extract_numeric_claims(
        context,
        include_generic=True,
        skip_years=False,  # contesto: massimo recall
    )

    report = NumericGuardReport(answer_claims=a_claims, context_claims=c_claims)
    for claim in a_claims:
        if not _claim_supported(claim, c_claims):
            report.unsupported.append(claim)
    report.has_violations = bool(report.unsupported)
    return report


def repair_feedback(report: NumericGuardReport) -> str:
    """Feedback breve da iniettare in un secondo pass LLM."""
    if not report.has_violations:
        return ""
    bad = sorted({c.raw.strip() for c in report.unsupported})
    return (
        "NUMERIC CLAIM VIOLATION rilevata. I seguenti valori quantitativi "
        f"compaiono nella tua risposta ma NON nel CONTESTO: {', '.join(bad)}. "
        "Stai fabbricando dati numerici non grounded. Riscrivi la risposta "
        "rimuovendo o sostituendo questi valori con citazioni verbatim dal "
        "CONTESTO. Se la domanda richiede metriche assenti dalle fonti: "
        "dichiara onestamente che il vault non contiene quel dato."
    )


def strip_unsupported_numerics(answer: str, report: NumericGuardReport) -> str:
    """Versione "hard": redact i claim non supportati con ``[dato non verificato]``.

    Conservativa: sostituisce solo il token verbatim, lascia intatta la
    prosa circostante. Usata dal repair-loop come fallback quando il
    repair LLM fallisce o è disabilitato.
    """
    if not report.has_violations or not answer:
        return answer
    # Ordina per offset decrescente così le sostituzioni successive non
    # invalidano gli offset precedenti.
    redactions = sorted(report.unsupported, key=lambda c: c.position, reverse=True)
    out = answer
    for claim in redactions:
        start = claim.position
        end = start + len(claim.raw)
        if 0 <= start < len(out) and out[start:end] == claim.raw:
            out = out[:start] + "[dato non verificato]" + out[end:]
    return out


__all__ = [
    "NumericClaim",
    "NumericGuardReport",
    "analyze",
    "extract_numeric_claims",
    "repair_feedback",
    "strip_unsupported_numerics",
]
