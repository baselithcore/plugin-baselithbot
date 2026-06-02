"""
Differential diagnosis reasoning agent.

Two responsibilities:
    * **Extraction**: turn a free-form patient utterance into an
      :class:`ExtractedObservation` so the graph can be updated. When the
      LLM fails to produce a schema-valid payload the agent falls back to a
      deterministic keyword/regex extractor so the Symptom Matrix is never
      empty after a meaningful utterance.
    * **Ranking**: starting from the :class:`SymptomMatrix`, produce a
      :class:`DifferentialDiagnosis` with calibrated confidences. A
      heuristic baseline ranks common Italian symptom→condition mappings
      when the LLM is unavailable, so the UI can show a live preview.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from core.observability.logging import get_logger

from ..models.clinical import (
    DifferentialDiagnosis,
    DifferentialHypothesis,
    ExtractedObservation,
    Symptom,
    SymptomMatrix,
)
from ..providers.medgemma_ollama import OllamaMedGemmaProvider
from ..safety.icd10 import sanitize_icd10

logger = get_logger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "system_differential.md"
)


# Ordered alternatives so multi-word symptoms match before bare keywords.
_SYMPTOM_LEXICON: Final[tuple[tuple[str, str, str | None], ...]] = (
    ("cefalea improvvisa", "cefalea improvvisa", "R51"),
    ("mal di testa", "cefalea", "R51"),
    ("dolore toracico", "dolore toracico", "R07.4"),
    ("dolore al petto", "dolore toracico", "R07.4"),
    ("dolore al collo", "cervicalgia", "M54.2"),
    ("zona cervicale", "cervicalgia", "M54.2"),
    ("rigidità del collo", "rigidità nucale", "R29.1"),
    ("dolore addominale", "dolore addominale", "R10"),
    ("mal di stomaco", "dolore addominale", "R10"),
    ("mal di pancia", "dolore addominale", "R10"),
    ("dolore alla pancia", "dolore addominale", "R10"),
    ("dolore al ventre", "dolore addominale", "R10"),
    ("dolore di pancia", "dolore addominale", "R10"),
    ("dolore allo stomaco", "dolore addominale", "R10"),
    ("crampi addominali", "dolore addominale", "R10"),
    ("crampi alla pancia", "dolore addominale", "R10"),
    ("pancia", "dolore addominale", "R10"),
    ("ventre", "dolore addominale", "R10"),
    ("dolore alla schiena", "lombalgia", "M54.5"),
    ("mal di schiena", "lombalgia", "M54.5"),
    ("dispnea", "dispnea", "R06.0"),
    ("affanno", "dispnea", "R06.0"),
    ("fiato corto", "dispnea", "R06.0"),
    ("nausea", "nausea", "R11"),
    ("vomito", "vomito", "R11"),
    ("febbre", "febbre", "R50.9"),
    ("temperatura alta", "febbre", "R50.9"),
    ("vertigini", "vertigini", "R42"),
    ("capogiri", "vertigini", "R42"),
    ("palpitazioni", "palpitazioni", "R00.2"),
    ("tachicardia", "tachicardia", "R00.0"),
    ("perdita di coscienza", "sincope", "R55"),
    ("svenimento", "sincope", "R55"),
    ("debolezza", "astenia", "R53"),
    ("affaticamento", "astenia", "R53"),
    ("tosse", "tosse", "R05"),
    ("diarrea", "diarrea", "R19.7"),
    ("sanguinamento", "emorragia", "R58"),
    ("dolore agli occhi", "dolore oculare", "H57.1"),
    ("visione offuscata", "visione offuscata", "H53.8"),
    ("dolore al collo", "cervicalgia", "M54.2"),
    ("collo", "cervicalgia", "M54.2"),
    ("testa", "cefalea", "R51"),
    ("petto", "dolore toracico", "R07.4"),
    ("schiena", "lombalgia", "M54.5"),
    ("stomaco", "dolore addominale", "R10"),
    ("addome", "dolore addominale", "R10"),
)

_CHARACTER_KEYWORDS: Final[tuple[str, ...]] = (
    "pulsante",
    "lancinante",
    "sordo",
    "trafittivo",
    "oppressivo",
    "urente",
    "bruciore",
    "pressante",
    "crampiforme",
    "intermittente",
    "continuo",
    "continua",
    "costante",
    "fisso",
    "fissa",
    "persistente",
    "ricorrente",
    "irradiato",
    "irradia",
    "diffuso",
    "diffusa",
    "puntiforme",
    "profondo",
    "profonda",
    "tagliente",
    "acuto",
    "acuta",
    "cronico",
    "cronica",
    "pressivo",
    "pressiva",
    "fastidioso",
    "fastidiosa",
    "leggero",
    "leggera",
    "forte",
    "intenso",
    "intensa",
    "molesto",
    "molesta",
    "improvviso",
    "improvvisa",
    "graduale",
    "pesante",
    "pesantezza",
    "appesantisce",
    "appensantisce",
    "estende",
    "estendersi",
    "diffonde",
    "spasmodico",
    "spasmodica",
    "stretta",
    "stringimento",
    "tensione",
    "rigido",
    "rigida",
    "rigidità",
    "tirato",
    "tirata",
    "crampo",
    "crampi",
)

# Pure quality adjectives that describe a symptom but are never a complaint
# on their own. A bare reply like "costante" / "forte" to a character or
# severity question must enrich the current symptom, NOT spawn a new one in
# the Symptom Matrix. Small models routinely echo the adjective back as a
# ``canonical_name`` — this set blocks those unconditionally. Curated to
# exclude ambiguous words that CAN be standalone symptoms (rigidità, crampo,
# bruciore, prurito, formicolio …).
_BARE_DESCRIPTOR_NAMES: Final[frozenset[str]] = frozenset(
    {
        "costante",
        "continuo",
        "continua",
        "intermittente",
        "fisso",
        "fissa",
        "persistente",
        "ricorrente",
        "pulsante",
        "sordo",
        "sorda",
        "trafittivo",
        "trafittiva",
        "oppressivo",
        "oppressiva",
        "pressante",
        "pressivo",
        "pressiva",
        "crampiforme",
        "puntiforme",
        "profondo",
        "profonda",
        "tagliente",
        "acuto",
        "acuta",
        "lancinante",
        "urente",
        "forte",
        "fortissimo",
        "fortissima",
        "intenso",
        "intensa",
        "lieve",
        "leggero",
        "leggera",
        "moderato",
        "moderata",
        "molesto",
        "molesta",
        "fastidioso",
        "fastidiosa",
        "improvviso",
        "improvvisa",
        "graduale",
        "pesante",
        "diffuso",
        "diffusa",
        "spasmodico",
        "spasmodica",
        "cronico",
        "cronica",
        "irradiato",
        "irradiata",
    }
)

# Slots whose answers are metadata about an existing symptom (quality,
# intensity, timing) rather than a new complaint. A single-token reply to one
# of these never introduces a new symptom.
_METADATA_SLOTS: Final[frozenset[str]] = frozenset(
    {"severity", "character", "timing", "onset", "radiation", "modifiers"}
)

# Radiation / spread of pain detection.
_RADIATION_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(?:fino a(?:l|lla|llo|i|gli|lle)?|si estende|estende(?:rsi|ndosi)?|"
    r"diffonde|diffondersi|raggiunge|arriva (?:al|alla|allo|ai|agli|alle)|"
    r"anche (?:al|alla|allo|ai|agli|alle|in)|irradia(?:to|ta)?|"
    r"verso (?:il|la|lo|i|gli|le)|si propaga)\b",
    re.IGNORECASE,
)


_SEVERITY_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:nrs|scala|severità|intensità|punteggio)\s*[:=]?\s*(\d{1,2})", re.IGNORECASE
)

# Italian onset/timing markers. Each tuple is (regex, callable→datetime|None).
# ``_ONSET_QUAL`` absorbs the optional approximate qualifier between "da" and
# the number ("da più di 10 anni", "da circa 3 giorni", "da oltre 2 mesi").
_ONSET_QUAL: Final[str] = r"(?:circa\s+|quasi\s+|oltre\s+|pi[uù]\s+di\s+|almeno\s+)?"
_ONSET_HOURS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*(or[ae]|h)\b", re.IGNORECASE
)
_ONSET_DAYS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*(giorn[oi]|gg)\b", re.IGNORECASE
)
_ONSET_WEEKS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*settiman[ae]\b", re.IGNORECASE
)
_ONSET_MINUTES_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*minut[oi]\b", re.IGNORECASE
)
_ONSET_MONTHS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*mes[ei]\b", re.IGNORECASE
)
_ONSET_YEARS_REGEX: Final[re.Pattern[str]] = re.compile(
    rf"\bda\s+{_ONSET_QUAL}(\d{{1,3}})\s*ann[oi]\b", re.IGNORECASE
)

_ONSET_KEYWORDS: Final[tuple[tuple[str, timedelta], ...]] = (
    ("adesso", timedelta(minutes=5)),
    ("in questo momento", timedelta(minutes=5)),
    ("ora", timedelta(minutes=5)),
    ("poco fa", timedelta(minutes=30)),
    ("pochi minuti fa", timedelta(minutes=15)),
    ("un'ora fa", timedelta(hours=1)),
    ("mezz'ora fa", timedelta(minutes=30)),
    # Risveglio: most specific first so substring matches don't shadow them.
    ("appena sveglio", timedelta(hours=8)),
    ("appena svegliata", timedelta(hours=8)),
    ("appena svegliato", timedelta(hours=8)),
    ("appena alzato", timedelta(hours=8)),
    ("appena alzata", timedelta(hours=8)),
    ("al risveglio", timedelta(hours=8)),
    ("da quando mi sono svegliato", timedelta(hours=8)),
    ("da quando mi sono svegliata", timedelta(hours=8)),
    ("mi sono svegliato", timedelta(hours=8)),
    ("mi sono svegliata", timedelta(hours=8)),
    # Notte.
    ("stanotte", timedelta(hours=10)),
    ("questa notte", timedelta(hours=10)),
    ("durante la notte", timedelta(hours=10)),
    # Mattina (incluse varianti regionali "stamani"/"stamane").
    ("da stamattina", timedelta(hours=6)),
    ("da stamani", timedelta(hours=6)),
    ("da stamane", timedelta(hours=6)),
    ("da questa mattina", timedelta(hours=6)),
    ("stamattina", timedelta(hours=6)),
    ("stamani", timedelta(hours=6)),
    ("stamane", timedelta(hours=6)),
    ("questa mattina", timedelta(hours=6)),
    # Sera/pomeriggio.
    ("stasera", timedelta(hours=2)),
    ("questa sera", timedelta(hours=2)),
    ("oggi pomeriggio", timedelta(hours=3)),
    ("nel pomeriggio", timedelta(hours=4)),
    ("da oggi", timedelta(hours=6)),
    ("oggi", timedelta(hours=6)),
    ("ieri sera", timedelta(days=1)),
    ("ieri notte", timedelta(days=1)),
    ("ieri mattina", timedelta(days=1, hours=6)),
    ("ieri pomeriggio", timedelta(days=1)),
    ("ieri", timedelta(days=1)),
    ("l'altro ieri", timedelta(days=2)),
    ("altro ieri", timedelta(days=2)),
    ("due giorni fa", timedelta(days=2)),
    ("tre giorni fa", timedelta(days=3)),
    ("qualche giorno fa", timedelta(days=3)),
    ("settimana scorsa", timedelta(days=7)),
    ("la settimana scorsa", timedelta(days=7)),
    ("qualche settimana fa", timedelta(weeks=2)),
    ("mese scorso", timedelta(days=30)),
    ("il mese scorso", timedelta(days=30)),
    ("qualche mese fa", timedelta(days=60)),
)
_FORTE_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(molto\s+forte|fortissim[oa]|insopportabile|atroce)\b", re.IGNORECASE
)
_MEDIUM_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(forte|intens[oa])\b", re.IGNORECASE
)
_MILD_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b(lieve|leggero|moderato)\b", re.IGNORECASE
)


# Italian denial markers. The parser scans each lexicon trigger appearing in
# the utterance and checks whether a negation cue sits within a short window
# *before* the trigger (typical Italian negation surface: "non ho febbre",
# "nessuna nausea", "niente vomito", "senza tosse", "no, non ho la febbre").
# Window is short because chained clauses can flip polarity ("non ho febbre,
# ho solo tosse" must not deny "tosse").
#
# CRITICAL: substring matching is unsafe for short cues — "no " collides with
# "sono ", "non" collides with the Italian word "nonna". Each cue is compiled
# as a regex anchored to word boundaries (or punctuation/start-of-string for
# the trailing "no" variants).
_DENIAL_CUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bnon\s+ho\b",
        r"\bnon\s+ha\b",
        r"\bnon\s+avvert[oe]\b",
        r"\bnon\s+sent[oe]\b",
        r"\bnon\s+riferis[co][oe]\b",
        r"\bnon\s+not[oa]\b",
        r"\bnon\s+c['’]è\b",
        r"\bnon\s+c['’]e\b",
        r"\bnon\s+present[ei]\b",
        r"\bnego\b",
        r"\bnega\b",
        r"\bniente\b",
        r"\bnessun[oa]?\b",
        r"\bsenza\b",
        r"(?:^|[,.;:!?\s])no(?=[\s,.;:!?])",
        r"\bmai\s+avut[oa]\b",
        r"\bnon\s+mi\s+pare\b",
        r"\bnon\s+credo\b",
        r"\bmai\s+prese\b",
        r"\bmai\s+presi\b",
    )
)
_DENIAL_WINDOW_CHARS: Final[int] = 48

# Global-denial patterns — short Italian replies that mean "no, niente" for
# whatever slot the agent just asked about. Used to mark allergy/medication/
# PMH slots as satisfied without forcing the agent to re-ask twice.
_GLOBAL_DENIAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Single-word denials and their light variants.
    re.compile(
        r"^(?:no|niente|nulla|mai|nessun[oa]?)\s*[.,!?]*$",
        re.IGNORECASE,
    ),
    # "no, mai" / "no grazie" / "no nessuno".
    re.compile(
        r"^no[\s,.]+(?:mai|grazie|nessun[oa]?|niente|nulla)\s*[.,!?]*$",
        re.IGNORECASE,
    ),
    # "nessun farmaco" / "nessuna allergia" / "niente di particolare".
    re.compile(
        r"^(?:no\s*,?\s*)?(?:nessun[oa]?|niente|nulla)\s+\w+\s*[.,!?]*$",
        re.IGNORECASE,
    ),
)

# Lightweight Italian allergen lexicon (high-prevalence). Pure heuristic so
# the agent doesn't depend on the LLM to mark the allergy slot as filled.
_ALLERGEN_LEXICON: Final[tuple[tuple[str, str], ...]] = (
    ("polline", "polline"),
    ("polvere", "polvere/acari"),
    ("acari", "polvere/acari"),
    ("graminacee", "graminacee"),
    ("parietaria", "parietaria"),
    ("ambrosia", "ambrosia"),
    ("nichel", "nichel"),
    ("lattice", "lattice"),
    ("penicillina", "penicillina"),
    ("amoxicillina", "amoxicillina"),
    ("cefalosporin", "cefalosporine"),
    ("aspirina", "aspirina (ASA)"),
    ("ibuprofene", "ibuprofene"),
    ("fans", "FANS"),
    ("lattosio", "lattosio"),
    ("glutine", "glutine"),
    ("noci", "frutta a guscio"),
    ("nocciole", "frutta a guscio"),
    ("arachidi", "arachidi"),
    ("uovo", "uovo"),
    ("uova", "uovo"),
    ("pesce", "pesce"),
    ("crostacei", "crostacei"),
    ("frutti di mare", "molluschi/crostacei"),
    ("kiwi", "kiwi"),
    ("fragole", "fragole"),
    ("muffe", "muffe"),
    ("pelo di gatto", "epitelio felino"),
    ("pelo di cane", "epitelio canino"),
)

# Lightweight Italian medication lexicon — extracted whenever the patient
# names a drug class or specific molecule. Conservative: only highly-common
# Italian names so we don't mistakenly capture generic words.
_MEDICATION_LEXICON: Final[tuple[str, ...]] = (
    "tachipirina",
    "paracetamolo",
    "ibuprofene",
    "moment",
    "oki",
    "ketoprofene",
    "aspirina",
    "asa",
    "cardioaspirin",
    "ramipril",
    "enalapril",
    "amlodipina",
    "metformina",
    "insulina",
    "warfarin",
    "eliquis",
    "apixaban",
    "rivaroxaban",
    "atorvastatina",
    "rosuvastatina",
    "simvastatina",
    "omeprazolo",
    "pantoprazolo",
    "lansoprazolo",
    "levotiroxina",
    "eutirox",
    "ventolin",
    "salbutamolo",
    "cortisone",
    "prednisone",
    "metilprednisolone",
    "amoxicillina",
    "augmentin",
    "ciprofloxacina",
    "azitromicina",
    "claritromicina",
    "betabloccante",
    "ace inibitore",
    "diuretico",
    "anticoagulante",
    "antibiotico",
    "antinfiammatorio",
)

# Italian PMH lexicon for risk factors flagged when the patient mentions
# chronic conditions while answering ``past_medical_history``.
_PMH_LEXICON: Final[tuple[tuple[str, str], ...]] = (
    ("ipertensione", "ipertensione arteriosa"),
    ("pressione alta", "ipertensione arteriosa"),
    ("diabete", "diabete mellito"),
    ("dislipidemia", "dislipidemia"),
    ("colesterolo alto", "dislipidemia"),
    ("infarto", "pregresso IMA"),
    ("ima", "pregresso IMA"),
    ("ictus", "pregresso ictus"),
    ("tia", "pregresso TIA"),
    ("aritmia", "aritmia cardiaca"),
    ("fibrillazione atriale", "fibrillazione atriale"),
    ("scompenso cardiaco", "scompenso cardiaco"),
    ("asma", "asma bronchiale"),
    ("bpco", "BPCO"),
    ("copd", "BPCO"),
    ("tiroide", "tireopatia"),
    ("ipotiroid", "ipotiroidismo"),
    ("ipertiroid", "ipertiroidismo"),
    ("epatite", "epatopatia"),
    ("cirrosi", "cirrosi"),
    ("insufficienza renale", "insufficienza renale"),
    ("calcoli", "litiasi"),
    ("tumore", "neoplasia"),
    ("cancro", "neoplasia"),
    ("emicrania", "emicrania cronica"),
    ("epilessia", "epilessia"),
    ("depressione", "depressione"),
    ("ansia", "disturbo d'ansia"),
    ("gravidanza", "gravidanza in corso"),
    ("anticoagulant", "terapia anticoagulante"),
)

# Polarity flippers: when one of these appears between a denial cue and the
# symptom trigger, the symptom is **not** denied (the clause has switched
# from negation to affirmation).
_POLARITY_FLIP_MARKERS: Final[tuple[str, ...]] = (
    ", ",
    "; ",
    ". ",
    "! ",
    "? ",
    " ma ",
    " però ",
    " pero ",
    " invece ",
    " mentre ",
    " solo ",
    " anche ",
    " ho ",
    " ha ",
    " avverto ",
    " avverte ",
    " sento ",
    " sente ",
    " noto ",
    " nota ",
    " presento ",
    " presenta ",
    " riferisco ",
    " riferisce ",
)


# Conservative symptom → candidate condition mapping for live preview.
_BASELINE_DDX: Final[dict[str, list[tuple[str, str | None, list[str]]]]] = {
    "cefalea": [
        ("Cefalea tensiva", "G44.2", ["Anamnesi", "Esame obiettivo neurologico"]),
        ("Emicrania", "G43.9", ["Diario cefalee", "Valutazione neurologica"]),
    ],
    "cefalea improvvisa": [
        (
            "Emorragia subaracnoidea (sospetto)",
            "I60.9",
            ["TC encefalo urgente", "Puntura lombare se TC negativa"],
        ),
    ],
    "dolore toracico": [
        (
            "Sindrome coronarica acuta (sospetto)",
            "I20.9",
            ["ECG 12 derivazioni", "Troponina"],
        ),
        ("Pericardite", "I30.9", ["ECG", "Ecocardiogramma"]),
    ],
    "cervicalgia": [
        ("Cervicalgia muscolo-tensiva", "M54.2", ["Anamnesi", "Esame obiettivo"]),
        (
            "Sospetta radicolopatia cervicale",
            "M50.1",
            ["Esame neurologico", "RM cervicale se persistente"],
        ),
    ],
    "rigidità nucale": [
        (
            "Sospetta meningite",
            "G03.9",
            ["Esame obiettivo neurologico urgente", "TC encefalo + puntura lombare"],
        ),
    ],
    "dolore addominale": [
        ("Gastrite", "K29.7", ["Anamnesi", "EGDS se persistente"]),
        ("Appendicite (sospetto)", "K35.80", ["Esame obiettivo", "Ecografia addome"]),
    ],
    "lombalgia": [
        ("Lombalgia acuta meccanica", "M54.5", ["Anamnesi", "Esame obiettivo"]),
    ],
    "dispnea": [
        (
            "Sospetta embolia polmonare",
            "I26.99",
            ["D-dimero", "Angio-TC torace"],
        ),
        ("Crisi asmatica", "J45.901", ["Saturimetria", "Spirometria"]),
    ],
    "febbre": [
        ("Sindrome influenzale", "J11", ["Tampone respiratorio"]),
    ],
    "sincope": [
        ("Sincope vasovagale", "R55", ["ECG", "Holter ECG"]),
    ],
}


# Typical (expected) findings per hypothesis — used to flip a denied symptom
# into a ``contradicting_findings`` entry that also lowers confidence. Keys
# match condition names from ``_BASELINE_DDX``; values are canonical symptom
# names that, when denied, weaken the hypothesis.
_HYPOTHESIS_TYPICAL_FINDINGS: Final[dict[str, tuple[str, ...]]] = {
    "Cefalea tensiva": ("cefalea",),
    "Emicrania": ("cefalea", "nausea", "vomito"),
    "Emorragia subaracnoidea (sospetto)": (
        "cefalea improvvisa",
        "rigidità nucale",
        "vomito",
    ),
    "Sindrome coronarica acuta (sospetto)": (
        "dolore toracico",
        "dispnea",
        "nausea",
    ),
    "Pericardite": ("dolore toracico", "febbre"),
    "Cervicalgia muscolo-tensiva": ("cervicalgia",),
    "Sospetta radicolopatia cervicale": ("cervicalgia",),
    "Sospetta meningite": ("febbre", "cefalea", "rigidità nucale", "vomito"),
    "Gastrite": ("dolore addominale", "nausea", "vomito"),
    "Appendicite (sospetto)": ("dolore addominale", "febbre", "nausea"),
    "Lombalgia acuta meccanica": ("lombalgia",),
    "Sospetta embolia polmonare": ("dispnea", "dolore toracico", "tachicardia"),
    "Crisi asmatica": ("dispnea", "tosse"),
    "Sindrome influenzale": ("febbre", "tosse", "astenia", "cefalea"),
    "Sincope vasovagale": ("sincope",),
}

# Confidence delta applied per matching pertinent negative.
_DENIAL_PENALTY: Final[float] = 0.15

# Per-condition discriminator questions. Triggered when the heuristic DDx
# shows two or more competing hypotheses (top-2 confidence delta ≤
# ``_DISCRIMINATOR_DELTA``). Asking one of these short, condition-specific
# probes drives the differential the way a real clinician would, instead of
# walking through the generic OPQRST slot list to the end.
#
# Each tuple is (question_text, discriminator_key). ``discriminator_key`` is
# stored on ``snap.discriminators_asked`` so the same probe is never repeated
# in the same session.
DISCRIMINATOR_QUESTIONS: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    "Emicrania": (
        ("Ha fotofobia o fonofobia?", "emicrania_fotofobia"),
        ("Ha avuto aura visiva prima del dolore?", "emicrania_aura"),
        (
            "Il dolore è unilaterale e pulsante?",
            "emicrania_unilaterale",
        ),
    ),
    "Cefalea tensiva": (
        (
            "Il dolore è gravativo-costrittivo bilaterale?",
            "tensiva_costrittivo",
        ),
        (
            "Peggiora con stress o tensione muscolare?",
            "tensiva_stress",
        ),
    ),
    "Sindrome coronarica acuta (sospetto)": (
        (
            "Il dolore si irradia al braccio sinistro o alla mandibola?",
            "sca_irradiazione",
        ),
        (
            "Ha sudorazione fredda o senso di morte imminente?",
            "sca_sudorazione",
        ),
        (
            "Il dolore peggiora con lo sforzo?",
            "sca_sforzo",
        ),
    ),
    "Pericardite": (
        (
            "Il dolore migliora piegandosi in avanti?",
            "pericardite_postura",
        ),
        (
            "Il dolore peggiora con respirazione profonda?",
            "pericardite_pleuritico",
        ),
    ),
    "Sospetta embolia polmonare": (
        (
            "Ha avuto immobilizzazione prolungata o viaggio recente?",
            "ep_immobilizzazione",
        ),
        (
            "Ha tachicardia o sensazione di mancanza d'aria a riposo?",
            "ep_tachicardia",
        ),
        (
            "Ha avuto emottisi (sangue nell'espettorato)?",
            "ep_emottisi",
        ),
    ),
    "Sospetta meningite": (
        (
            "Ha rigidità del collo o fotofobia intensa?",
            "men_nucale",
        ),
        (
            "Ha avuto febbre alta improvvisa?",
            "men_febbre",
        ),
        (
            "Sono comparse macchie cutanee non scompariscenti?",
            "men_petecchie",
        ),
    ),
    "Appendicite (sospetto)": (
        (
            "Il dolore è migrato verso la fossa iliaca destra?",
            "app_migrazione",
        ),
        (
            "Ha perdita di appetito o nausea persistente?",
            "app_anoressia",
        ),
        (
            "Peggiora con la decompressione (segno di Blumberg)?",
            "app_blumberg",
        ),
    ),
    "Gastrite": (
        (
            "Il dolore è correlato ai pasti o all'alcol?",
            "gastrite_pasti",
        ),
        (
            "Assume FANS regolarmente?",
            "gastrite_fans",
        ),
    ),
    "Crisi asmatica": (
        (
            "Ha sibili o fischi al respiro?",
            "asma_sibili",
        ),
        (
            "Ha già diagnosi nota di asma?",
            "asma_nota",
        ),
    ),
    "Sindrome influenzale": (
        (
            "Ha mialgie diffuse e brividi marcati?",
            "flu_mialgie",
        ),
        (
            "Ha avuto contatti con casi confermati?",
            "flu_contatti",
        ),
    ),
    "Sincope vasovagale": (
        (
            "Ha avuto prodromi (sudorazione, visione offuscata)?",
            "sincope_prodromi",
        ),
        (
            "L'episodio è correlato a postura o stimoli emotivi?",
            "sincope_trigger",
        ),
    ),
    "Lombalgia acuta meccanica": (
        (
            "Ha avuto sforzo fisico o trauma recente?",
            "lbp_trauma",
        ),
        (
            "Ha disturbi sfinterici o anestesia a sella?",
            "lbp_sfinteri",
        ),
    ),
    "Sospetta radicolopatia cervicale": (
        (
            "Ha formicolio o debolezza al braccio?",
            "cerv_paresthesia",
        ),
        (
            "Peggiora con movimenti del collo?",
            "cerv_movimento",
        ),
    ),
    "Emorragia subaracnoidea (sospetto)": (
        (
            "È stata la cefalea più intensa della sua vita?",
            "sah_thunderclap",
        ),
        (
            "Ha vomito, rigidità nucale o alterazione di coscienza?",
            "sah_meningismo",
        ),
    ),
}
_DISCRIMINATOR_DELTA: Final[float] = 0.12


def select_discriminator_question(
    differential: DifferentialDiagnosis,
    *,
    already_asked: set[str],
) -> tuple[str, str, str] | None:
    """Return ``(question, discriminator_key, condition)`` for the highest
    yield discriminator we have not yet asked, or ``None`` when the
    differential is not competitive enough or no probes are left.

    A differential is "competitive" when the top hypothesis is within
    ``_DISCRIMINATOR_DELTA`` of the next-best alternative; in that case we
    can shave probability mass off either side with one well-aimed yes/no
    question.
    """
    hypotheses = [h for h in differential.hypotheses if h.confidence > 0]
    if len(hypotheses) < 2:
        return None
    top, second = hypotheses[0], hypotheses[1]
    if (top.confidence - second.confidence) > _DISCRIMINATOR_DELTA:
        return None
    # Try discriminators for the top hypothesis first, then for the runner-up.
    for h in (top, second):
        probes = DISCRIMINATOR_QUESTIONS.get(h.condition, ())
        for question, key in probes:
            if key in already_asked:
                continue
            return question, key, h.condition
    return None


# Default wall-clock budget for the per-turn extraction LLM call. Tuned for
# a small model (medgemma:4b, ~2-3s). Big models (medgemma:27b, ~12-15s warm)
# REQUIRE raising this via ``provider.turn_timeout_seconds`` in plugins.yaml,
# otherwise extraction always times out and the heuristic extractor runs on
# every turn (same generic questions, same baseline DDx).
_DEFAULT_LLM_TURN_TIMEOUT_SECONDS: Final[float] = 3.0


class DifferentialDxAgent:
    """Wraps MedGemma for extraction and DDx ranking with safe fallbacks."""

    name = "baselithmed-differential"

    def __init__(
        self,
        *,
        provider: OllamaMedGemmaProvider,
        fast_provider: OllamaMedGemmaProvider | None = None,
        system_prompt: str | None = None,
        canonicalization_lexicon: tuple[tuple[str, str, str | None], ...] | None = None,
        turn_timeout_seconds: float = _DEFAULT_LLM_TURN_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        # ``fast_provider`` handles the latency-sensitive per-turn extraction
        # (NER). When unset it falls back to the main provider — a single-
        # model deployment behaves exactly as before. The main provider is
        # reserved for the quality-sensitive finalize DDx ranking.
        self._fast_provider = fast_provider or provider
        self._system_prompt = system_prompt or _PROMPT_PATH.read_text(encoding="utf-8")
        self._turn_timeout = turn_timeout_seconds
        # The LLM-output canonicalizer can be swapped per language so a non-IT
        # patient utterance ("chest pain") still maps to the Italian
        # canonical keys downstream graph/red-flag layers expect. The
        # heuristic extractor stays Italian for now — its regex/keyword
        # surface is language-specific and refactoring it is a larger
        # change tracked separately.
        self._canonicalization_lexicon = (
            canonicalization_lexicon
            if canonicalization_lexicon is not None
            else _SYMPTOM_LEXICON
        )

    # Upper bound on an LLM symptom name. A "symptom" longer than this is
    # almost always the model echoing the whole utterance — drop those, but
    # keep genuine multi-word symptoms ("apnea notturna", "dolore lombare").
    _MAX_SYMPTOM_NAME_LEN: Final[int] = 60

    # Placeholder / negation tokens that small models emit as a "symptom"
    # when the patient reply carries none (e.g. answering an onset question
    # with "da più di 10 anni" → model returns canonical_name="nessun
    # sintomo"). These must never enter the Symptom Matrix.
    _NON_SYMPTOM_NAMES: Final[frozenset[str]] = frozenset(
        {
            "nessun sintomo",
            "nessun sintomo riferito",
            "nessuno",
            "nessuna",
            "nessun",
            "niente",
            "nulla",
            "n/a",
            "na",
            "none",
            "no symptom",
            "no symptoms",
            "asintomatico",
            "asintomatica",
            "non specificato",
            "sconosciuto",
            "non disponibile",
        }
    )

    def _canonicalize_symptoms(self, obs: ExtractedObservation) -> ExtractedObservation:
        """Normalize LLM symptoms against the lexicon, keeping unmapped ones.

        Two cases:
            * **Lexicon hit** — rewrite to the canonical Italian name and
              attach the lexicon ICD-10 hint (so synonyms like ``mal di
              testa`` collapse to ``cefalea``).
            * **No lexicon hit** — KEEP the symptom using the LLM's own
              (lowercased) name. The lexicon is only ~50 entries; treating
              it as a whitelist silently drops every real symptom outside
              it (e.g. ``apnea notturna``), leaving the Symptom Matrix
              empty and the interview stuck re-asking the chief complaint.
              We trust the model's NER here and rely on the ICD-10
              validator to null out fabricated codes.

        Obvious junk (empty names, or a "symptom" longer than
        ``_MAX_SYMPTOM_NAME_LEN`` — i.e. the whole utterance echoed back) is
        still discarded.
        """
        if not obs.symptoms:
            return obs
        kept: list[Symptom] = []
        for sym in obs.symptoms:
            name_lower = sym.canonical_name.lower().strip()
            quote_lower = (sym.raw_quote or "").lower()
            if not name_lower or len(name_lower) > self._MAX_SYMPTOM_NAME_LEN:
                continue
            if name_lower in self._NON_SYMPTOM_NAMES:
                continue
            # Bare quality adjectives ("costante", "forte") are descriptors of
            # an existing symptom, never a standalone complaint — the LLM
            # echoes them back when the patient answers a character/severity
            # question. The enrichment path routes the word to the current
            # symptom's character/severity instead.
            if name_lower in _BARE_DESCRIPTOR_NAMES:
                continue
            canonical: str | None = None
            icd = sym.icd10_hint
            for trigger, target_canonical, target_icd in self._canonicalization_lexicon:
                if (
                    trigger == name_lower
                    or trigger in name_lower
                    or trigger in quote_lower
                ):
                    canonical = target_canonical
                    icd = icd or target_icd
                    break
            # No lexicon match → keep the LLM symptom verbatim (normalized).
            final_name = canonical if canonical is not None else name_lower
            kept.append(
                sym.model_copy(
                    update={
                        "canonical_name": final_name,
                        "icd10_hint": sanitize_icd10(icd),
                    }
                )
            )
        return obs.model_copy(update={"symptoms": kept})

    async def extract_entities(
        self,
        utterance: str,
        *,
        turn_id: str,
        last_question_slot: str | None = None,
    ) -> ExtractedObservation:
        """Run NER on a patient utterance with heuristic fallback.

        ``last_question_slot`` is the slot the agent probed on the previous
        turn. A single-token reply to a metadata slot (severity/character/…)
        is a descriptor of the current symptom, never a new complaint, so any
        symptom the LLM hallucinates from it is dropped.
        """
        prompt = (
            "Estrai sintomi, body sites, farmaci, fattori di rischio e link "
            "temporali dalla frase del paziente. Per ogni sintomo imposta "
            "`source_turn_id` al valore fornito. Lingua italiana.\n\n"
            f"turn_id: {turn_id}\n"
            f"frase paziente: {utterance!r}\n\n"
            "Esempio output valido per ExtractedObservation:\n"
            "{\n"
            '  "symptoms": [\n'
            '    {"canonical_name": "cefalea", "raw_quote": "mi fa male la testa", '
            '"body_site": "testa", "severity_nrs": 6, "character": ["pulsante"], '
            f'"icd10_hint": "R51", "source_turn_id": "{turn_id}"}}\n'
            "  ],\n"
            '  "body_sites": ["testa"], "medications": [], '
            '"risk_factors": [], "temporal_links": []\n'
            "}"
        )
        try:
            llm_obs = await asyncio.wait_for(
                self._fast_provider.generate_structured(
                    prompt=prompt,
                    schema=ExtractedObservation,
                    system=self._system_prompt,
                ),
                timeout=self._turn_timeout,
            )
        except TimeoutError:
            logger.warning(
                "DDx extraction LLM timed out (>%ss), using heuristic.",
                self._turn_timeout,
            )
            llm_obs = ExtractedObservation()
        except Exception as exc:  # noqa: BLE001
            logger.warning("DDx extraction LLM failed, using heuristic: %s", exc)
            llm_obs = ExtractedObservation()

        llm_obs = self._canonicalize_symptoms(llm_obs)
        # Single-token reply to a metadata slot ("costante", "8", "forte") is a
        # descriptor of the current symptom, never a new complaint. Drop any
        # symptom the LLM invented from it; the enrichment path in the flow
        # routes the token to the existing symptom's character/severity.
        if (
            last_question_slot in _METADATA_SLOTS
            and len(utterance.split()) <= 1
            and llm_obs.symptoms
        ):
            llm_obs = llm_obs.model_copy(update={"symptoms": []})
        heuristic = self._heuristic_extract(utterance, turn_id=turn_id)
        # Heuristic denials win against LLM hallucination: small medical
        # models routinely emit ``"febbre"`` as a confirmed symptom even when
        # the utterance is ``"non ho febbre"``. The negation parser is more
        # reliable than the LLM here, so drop affirmed LLM symptoms whose
        # canonical name appears in the heuristic denial list.
        if heuristic.denied_symptoms:
            denied_set = set(heuristic.denied_symptoms)
            kept = [s for s in llm_obs.symptoms if s.canonical_name not in denied_set]
            if len(kept) != len(llm_obs.symptoms):
                llm_obs = llm_obs.model_copy(update={"symptoms": kept})
        return self._merge_observations(llm_obs, heuristic)

    # Budget for the explicit ``/triage/finalize`` LLM call. medgemma:27b
    # cold-start can take 30-60s on commodity hardware; the patient is no
    # longer waiting on the chat at this point, so the budget is generous.
    FINALIZE_LLM_TIMEOUT_SECONDS: float = 90.0

    async def rank(
        self, matrix: SymptomMatrix, *, timeout: float | None = None
    ) -> DifferentialDiagnosis:
        """Rank candidate diagnoses given the current Symptom Matrix.

        Always returns a non-empty :class:`DifferentialDiagnosis` if there is
        any symptom: when the LLM fails the heuristic baseline is returned.
        ``timeout`` lets the caller widen the budget for an explicit
        clinician-facing finalize.
        """
        if not matrix.symptoms:
            return DifferentialDiagnosis(
                hypotheses=[],
                model_id=self._provider.model_id,
                notes="Nessun sintomo estratto.",
            )
        prompt = (
            "Genera la differential diagnosis ordinata per confidence "
            "decrescente partendo dai sintomi raccolti.\n\n"
            f"{json.dumps(matrix.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"model_id deve essere '{self._provider.model_id}'."
        )
        budget = timeout if timeout is not None else self.FINALIZE_LLM_TIMEOUT_SECONDS
        fallback_reason: str
        try:
            ddx = await asyncio.wait_for(
                self._provider.generate_structured(
                    prompt=prompt,
                    schema=DifferentialDiagnosis,
                    system=self._system_prompt,
                ),
                timeout=budget,
            )
            ddx.hypotheses.sort(key=lambda h: h.confidence, reverse=True)
            if ddx.hypotheses:
                # Strip fabricated ICD-10 codes from the LLM output before
                # surfacing them to the clinician/UI.
                ddx.hypotheses = [
                    h.model_copy(update={"icd10": sanitize_icd10(h.icd10)})
                    for h in ddx.hypotheses
                ]
                return ddx
            fallback_reason = "empty_hypotheses"
            logger.warning("DDx ranking LLM returned 0 hypotheses, using heuristic.")
        except (TimeoutError, asyncio.TimeoutError):
            fallback_reason = "timeout"
            logger.warning(
                "DDx ranking LLM timed out (>%ss), using heuristic.",
                budget,
            )
        except Exception as exc:  # noqa: BLE001
            fallback_reason = "exception"
            logger.warning("DDx ranking LLM failed, using heuristic: %s", exc)

        return self._heuristic_rank(matrix, fallback_reason=fallback_reason)

    async def execute(
        self, input: Any, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Bridge for the orchestrator AgentProtocol."""
        context = context or {}
        turn_id = str(context.get("turn_id", "turn-0"))
        observation = await self.extract_entities(str(input), turn_id=turn_id)
        return observation.model_dump(mode="json")

    # ------------------------------------------------------------------ helpers

    def _heuristic_extract(
        self, utterance: str, *, turn_id: str
    ) -> ExtractedObservation:
        lower = utterance.lower()
        symptoms: list[Symptom] = []
        seen_canonical: set[str] = set()
        onset = _infer_onset(utterance)
        severity = _infer_severity(utterance)
        character = [c for c in _CHARACTER_KEYWORDS if c in lower]
        if _RADIATION_REGEX.search(lower) and "irradia" not in character:
            character.append("irradia")

        denied = _extract_denials(lower)

        for trigger, canonical, icd in _SYMPTOM_LEXICON:
            if trigger not in lower:
                continue
            if canonical in seen_canonical:
                continue
            # Skip lexicon hits that are actually negated — they belong to
            # ``denied_symptoms`` and must not be added as confirmed symptoms.
            if canonical in denied:
                continue
            body_site = _infer_body_site(trigger, canonical)
            symptoms.append(
                Symptom(
                    canonical_name=canonical,
                    raw_quote=utterance,
                    body_site=body_site,
                    onset=onset,
                    severity_nrs=severity,
                    character=character,
                    icd10_hint=icd,
                    source_turn_id=turn_id,
                )
            )
            seen_canonical.add(canonical)

        body_sites: list[str] = sorted({s.body_site for s in symptoms if s.body_site})
        return ExtractedObservation(
            symptoms=symptoms,
            body_sites=body_sites,
            denied_symptoms=denied,
        )

    @staticmethod
    def _merge_observations(
        primary: ExtractedObservation, secondary: ExtractedObservation
    ) -> ExtractedObservation:
        """Merge LLM + heuristic observations deduping on canonical_name.

        When both extractors yield the same symptom, the union of their
        slot fields is kept (onset/severity/body_site/character) so a
        single LLM omission cannot mask metadata supplied by the heuristic.
        """
        by_canonical: dict[str, Symptom] = {}
        for sym in [*primary.symptoms, *secondary.symptoms]:
            existing = by_canonical.get(sym.canonical_name)
            if existing is None:
                by_canonical[sym.canonical_name] = sym
                continue
            merged_character = list(
                dict.fromkeys([*existing.character, *sym.character])
            )
            by_canonical[sym.canonical_name] = existing.model_copy(
                update={
                    "body_site": existing.body_site or sym.body_site,
                    "onset": existing.onset or sym.onset,
                    "severity_nrs": existing.severity_nrs
                    if existing.severity_nrs is not None
                    else sym.severity_nrs,
                    "character": merged_character,
                    "icd10_hint": existing.icd10_hint or sym.icd10_hint,
                }
            )
        merged_denied = list(
            dict.fromkeys([*primary.denied_symptoms, *secondary.denied_symptoms])
        )
        affirmed = {s.canonical_name for s in by_canonical.values()}
        merged_denied = [d for d in merged_denied if d not in affirmed]
        return ExtractedObservation(
            symptoms=list(by_canonical.values()),
            body_sites=sorted({*primary.body_sites, *secondary.body_sites}),
            medications=sorted({*primary.medications, *secondary.medications}),
            risk_factors=sorted({*primary.risk_factors, *secondary.risk_factors}),
            temporal_links=[*primary.temporal_links, *secondary.temporal_links],
            denied_symptoms=merged_denied,
        )

    def _heuristic_rank(
        self,
        matrix: SymptomMatrix,
        *,
        fallback_reason: str = "unspecified",
    ) -> DifferentialDiagnosis:
        hypotheses: list[DifferentialHypothesis] = []
        seen: dict[str, int] = {}
        affirmed = {s.canonical_name for s in matrix.symptoms}
        denied = [d for d in matrix.denied_symptoms if d not in affirmed]
        # Top hypothesis confidence scales with number of supporting symptoms.
        for sym in matrix.symptoms:
            candidates = _BASELINE_DDX.get(sym.canonical_name, [])
            base_conf = 0.6 if sym.severity_nrs and sym.severity_nrs >= 7 else 0.45
            for condition, icd, workup in candidates:
                if condition in seen:
                    # Boost an already-ranked condition when more than one
                    # symptom supports it — multi-symptom evidence is the
                    # strongest signal a heuristic can offer.
                    idx = seen[condition]
                    h = hypotheses[idx]
                    if sym.canonical_name not in h.supporting_findings:
                        new_support = [*h.supporting_findings, sym.canonical_name]
                        hypotheses[idx] = h.model_copy(
                            update={
                                "supporting_findings": new_support,
                                "confidence": min(1.0, h.confidence + 0.1),
                            }
                        )
                    continue
                seen[condition] = len(hypotheses)
                hypotheses.append(
                    DifferentialHypothesis(
                        condition=condition,
                        icd10=sanitize_icd10(icd),
                        confidence=base_conf,
                        supporting_findings=[sym.canonical_name],
                        contradicting_findings=[],
                        recommended_workup=workup,
                    )
                )

        # Apply pertinent-negative penalties: denied typical findings turn
        # into ``contradicting_findings`` and shave confidence per match.
        if denied and hypotheses:
            penalized: list[DifferentialHypothesis] = []
            for h in hypotheses:
                typical = _HYPOTHESIS_TYPICAL_FINDINGS.get(h.condition, ())
                contradictions = [d for d in denied if d in typical]
                if not contradictions:
                    penalized.append(h)
                    continue
                new_conf = max(
                    0.05, h.confidence - _DENIAL_PENALTY * len(contradictions)
                )
                penalized.append(
                    h.model_copy(
                        update={
                            "confidence": round(new_conf, 3),
                            "contradicting_findings": list(
                                dict.fromkeys(
                                    [*h.contradicting_findings, *contradictions]
                                )
                            ),
                        }
                    )
                )
            hypotheses = penalized

        if not hypotheses:
            hypotheses.append(
                DifferentialHypothesis(
                    condition="Quadro aspecifico — approfondimento clinico",
                    confidence=0.3,
                    supporting_findings=[s.canonical_name for s in matrix.symptoms[:3]],
                    recommended_workup=["Anamnesi mirata", "Esame obiettivo completo"],
                )
            )
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        reason_notes: dict[str, str] = {
            "timeout": (
                "Modello LLM non ha risposto entro il budget configurato; "
                "rilanciare la finalizzazione per provare di nuovo l'LLM."
            ),
            "exception": (
                "Modello LLM ha sollevato un errore (transport / parse / "
                "validazione schema); vedi log backend per dettagli e "
                "rilanciare la finalizzazione."
            ),
            "empty_hypotheses": (
                "Modello LLM ha risposto correttamente ma con zero ipotesi: "
                "sintomi insufficienti per un differenziale calibrato. "
                "Aggiungere più anamnesi o validare il ranking euristico."
            ),
            "unspecified": (
                "Fallback euristico attivo (motivo non specificato dal chiamante)."
            ),
        }
        cause = reason_notes.get(fallback_reason, reason_notes["unspecified"])
        notes = f"Ranking deterministico (regole cliniche italiane). {cause}"
        if denied:
            notes += f" Pertinent negatives applicati: {', '.join(denied)}."
        return DifferentialDiagnosis(
            hypotheses=hypotheses,
            model_id=f"{self._provider.model_id} · ranking deterministico",
            notes=notes,
        )


def is_global_denial(utterance: str) -> bool:
    """``True`` when the patient's reply is a short global "no/niente"."""
    stripped = utterance.strip()
    return any(p.match(stripped) for p in _GLOBAL_DENIAL_PATTERNS)


def extract_allergies(lower_utterance: str) -> list[str]:
    """Return matched allergen canonical names, dedup."""
    found: list[str] = []
    seen: set[str] = set()
    for trigger, canonical in _ALLERGEN_LEXICON:
        if trigger in lower_utterance and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def extract_medications(lower_utterance: str) -> list[str]:
    """Return medication names mentioned, normalized to title-case."""
    found: list[str] = []
    seen: set[str] = set()
    for med in _MEDICATION_LEXICON:
        if med in lower_utterance and med not in seen:
            seen.add(med)
            found.append(med.title())
    return found


def extract_risk_factors(lower_utterance: str) -> list[str]:
    """Return PMH/risk-factor labels from the utterance."""
    found: list[str] = []
    seen: set[str] = set()
    for trigger, canonical in _PMH_LEXICON:
        if trigger in lower_utterance and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


# Subject-aware denials: "nessun farmaco", "niente allergie", "no malattie".
# Map subject keyword → which anamnestic slot the denial satisfies. Lets a
# proactive "nessun farmaco" answer fill the ``medications`` slot even when
# the agent just asked about something else.
_SUBJECT_DENIAL_MAP: Final[tuple[tuple[str, str], ...]] = (
    # Medications subjects.
    ("farmac", "medications"),
    ("medicin", "medications"),
    ("pillol", "medications"),
    ("pastigl", "medications"),
    ("terapi", "medications"),
    # Allergies subjects.
    ("allerg", "allergies"),
    ("intolleranz", "allergies"),
    # PMH subjects.
    ("malatti", "past_medical_history"),
    ("patolog", "past_medical_history"),
    ("intervent", "past_medical_history"),
    ("operazion", "past_medical_history"),
    ("ricover", "past_medical_history"),
)
_NEGATIVE_QUANTIFIERS: Final[tuple[str, ...]] = (
    "nessun ",
    "nessuna ",
    "nessuno",
    "niente",
    "no ",
    "non ho ",
    "non assumo",
    "non prendo",
    "non soffro",
    "mai avuto",
    "mai presi",
    "mai prese",
)


# Italian aggravating / relieving modifier cues. Capturing the *clause* the
# patient used (truncated) gives the clinician the raw context while letting
# the slot-fill predicate recognise the modifier via the canonical
# ``peggiora:`` / ``migliora:`` prefix.
_AGGRAVATING_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"peggior[aoi]|aggrav[aoi]|scatena|provoca|"
    r"aumenta\s+con|fa\s+male\s+quando|fa\s+stare\s+peggio|"
    r"peggio\s+con|peggio\s+quando|peggio\s+se"
    r")\b",
    re.IGNORECASE,
)
_RELIEVING_REGEX: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"miglior[aoi]|allevi[aoi]|scompare|sparisce|sparito|"
    r"si\s+attenua|passa\s+con|passa\s+se|"
    r"riduce|ridotto|cala|calmo\s+con|allevia\s+con|"
    r"sto\s+meglio\s+(?:con|se|quando)|mi\s+sento\s+meglio"
    r")\b",
    re.IGNORECASE,
)


def extract_modifiers(lower_utterance: str) -> list[str]:
    """Return character-list entries describing what makes the symptom
    worse or better.

    Each entry is prefixed with ``peggiora:`` / ``migliora:`` so the
    existing slot-fill predicate (``character starts with`` either prefix)
    picks it up without any predicate change.
    """
    entries: list[str] = []
    trimmed = lower_utterance.strip()
    snippet = trimmed[:120]
    if _AGGRAVATING_REGEX.search(trimmed):
        entries.append(f"peggiora: {snippet}")
    if _RELIEVING_REGEX.search(trimmed):
        entries.append(f"migliora: {snippet}")
    return entries


def detect_subject_denials(lower_utterance: str) -> list[str]:
    """Return the slot names that the patient just denied by topic.

    Looks for a negative quantifier followed (within a short window) by a
    subject keyword. Example: ``"nessun farmaco"`` returns
    ``["medications"]``. The same utterance can deny multiple slots, e.g.
    ``"nessun farmaco e nessuna allergia"`` returns both.
    """
    hits: list[str] = []
    seen: set[str] = set()
    for subject, slot in _SUBJECT_DENIAL_MAP:
        idx = lower_utterance.find(subject)
        if idx == -1:
            continue
        window_start = max(0, idx - 24)
        window = lower_utterance[window_start:idx]
        if any(q in window for q in _NEGATIVE_QUANTIFIERS):
            if slot not in seen:
                seen.add(slot)
                hits.append(slot)
    return hits


def _extract_denials(lower_utterance: str) -> list[str]:
    """Return canonical symptom names the patient explicitly denied.

    For each symptom-lexicon hit, look back ``_DENIAL_WINDOW_CHARS`` characters
    and find the *latest* denial cue (matched with regex word boundaries so
    short cues like ``"no"`` do not collide with ``"sono"``). The text
    between the cue end and the trigger must not contain any polarity-
    flipping marker (comma, ``" ma "``, ``" ho "``, etc.) — that handles
    compound clauses like ``"non ho febbre, ho tosse"`` correctly.
    """
    denied: list[str] = []
    seen: set[str] = set()
    for trigger, canonical, _icd in _SYMPTOM_LEXICON:
        idx = lower_utterance.find(trigger)
        if idx == -1:
            continue
        if canonical in seen:
            continue
        window_start = max(0, idx - _DENIAL_WINDOW_CHARS)
        window = lower_utterance[window_start:idx]
        denial_end = -1
        for pattern in _DENIAL_CUE_PATTERNS:
            # Find the latest match inside the window.
            last_end = -1
            for m in pattern.finditer(window):
                if m.end() > last_end:
                    last_end = m.end()
            if last_end > denial_end:
                denial_end = last_end
        if denial_end == -1:
            continue
        between = window[denial_end:]
        if any(fm in between for fm in _POLARITY_FLIP_MARKERS):
            continue
        seen.add(canonical)
        denied.append(canonical)
    return denied


def _infer_body_site(trigger: str, canonical: str) -> str | None:
    if "testa" in trigger or canonical == "cefalea":
        return "testa"
    if "collo" in trigger or "cervic" in trigger or canonical == "cervicalgia":
        return "collo"
    if "petto" in trigger or "toracico" in trigger:
        return "torace"
    if (
        "addom" in trigger
        or "stomaco" in trigger
        or "pancia" in trigger
        or "ventre" in trigger
    ):
        return "addome"
    if "schiena" in trigger or "lombal" in canonical:
        return "lombare"
    if "occhi" in trigger or "ocular" in canonical:
        return "occhi"
    return None


def _infer_onset(utterance: str, *, now: datetime | None = None) -> datetime | None:
    """Return a best-effort onset datetime parsed from Italian temporal hints.

    The resolution is conservative: when nothing matches return ``None`` so
    the slot remains marked unfilled. We prefer numerical hints
    (``da 3 ore``) over keywords because they carry more information.
    """
    now = now or datetime.now(timezone.utc)
    lower = utterance.lower()

    m = _ONSET_MINUTES_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(minutes=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_HOURS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(hours=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_DAYS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(days=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_WEEKS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(weeks=int(m.group(1)))
        except ValueError:
            pass

    m = _ONSET_MONTHS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(days=int(m.group(1)) * 30)
        except ValueError:
            pass

    m = _ONSET_YEARS_REGEX.search(lower)
    if m:
        try:
            return now - timedelta(days=int(m.group(1)) * 365)
        except ValueError:
            pass

    for keyword, delta in _ONSET_KEYWORDS:
        if keyword in lower:
            return now - delta

    return None


def _infer_severity(utterance: str) -> int | None:
    m = _SEVERITY_REGEX.search(utterance)
    if m:
        try:
            v = int(m.group(1))
            if 0 <= v <= 10:
                return v
        except ValueError:
            pass
    if _FORTE_REGEX.search(utterance):
        return 9
    if _MEDIUM_REGEX.search(utterance):
        return 7
    if _MILD_REGEX.search(utterance):
        return 3
    return None


# Suppress unused-import warning for uuid4 — kept for future schema reshapes.
_ = uuid4
