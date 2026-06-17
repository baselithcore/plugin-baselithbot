"""
Lexicon tables for the differential diagnosis agent.

All ``Final`` constant tuples/dicts/frozensets that encode clinical
knowledge live here so they can be imported by both the agent and any
sibling module (e.g. ``interview_flow``) without pulling in the full
agent class and its provider dependency.
"""

from __future__ import annotations

from typing import Final

from .differential_dx_discriminators import (
    DISCRIMINATOR_QUESTIONS as DISCRIMINATOR_QUESTIONS,
)
from .differential_dx_discriminators import _DISCRIMINATOR_DELTA as _DISCRIMINATOR_DELTA

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
