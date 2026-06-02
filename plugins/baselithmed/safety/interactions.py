"""Drug-interaction and drug-disease contraindication checker.

Two static dictionaries drive the checker:

    * :data:`_DRUG_DRUG_INTERACTIONS` — high-impact pairs (anticoagulant
      stacking, sedative stacking, QT-prolongation pairs, common
      pharmacokinetic interactions).
    * :data:`_DRUG_CONDITION_CONTRAINDICATIONS` — common bedside traps
      (NSAID + CKD, beta-blocker + severe asthma, metformin + acute kidney
      injury, etc.).

The data is intentionally narrow and clinically conservative: the goal is
to never miss an obvious mistake, not to replicate a full DDI database.
Each finding is severity-tagged (``HIGH``, ``MODERATE``, ``LOW``) so the
UI can surface red banners only for items that warrant blocking the
clinician's flow.

Inputs are matched case-insensitively against the lowercase canonical
form, and Italian + English synonyms are folded into a single key via
:data:`_DRUG_ALIASES`. Risk factors are matched against
:data:`_CONDITION_ALIASES`. Unknown drugs/conditions produce **no
finding** — the checker fails open, not loud.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from ..models.clinical import SymptomMatrix


class InteractionSeverity(StrEnum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


# Canonical-key normalisation. The matcher folds Italian + English brand
# names into the same key, so a session that captured "tachipirina" and
# another with "paracetamolo" yield the same finding.
_DRUG_ALIASES: Final[dict[str, str]] = {
    "tachipirina": "paracetamolo",
    "paracetamolo": "paracetamolo",
    "acetaminophen": "paracetamolo",
    "ibuprofene": "ibuprofene",
    "moment": "ibuprofene",
    "oki": "ketoprofene",
    "ketoprofene": "ketoprofene",
    "aspirina": "asa",
    "asa": "asa",
    "cardioaspirin": "asa",
    "aspirin": "asa",
    "warfarin": "warfarin",
    "coumadin": "warfarin",
    "apixaban": "apixaban",
    "eliquis": "apixaban",
    "rivaroxaban": "rivaroxaban",
    "dabigatran": "dabigatran",
    "ramipril": "ace_inibitore",
    "enalapril": "ace_inibitore",
    "lisinopril": "ace_inibitore",
    "ace inibitore": "ace_inibitore",
    "ace_inibitore": "ace_inibitore",
    "valsartan": "arb",
    "losartan": "arb",
    "candesartan": "arb",
    "arb": "arb",
    "metformina": "metformina",
    "metformin": "metformina",
    "insulina": "insulina",
    "insulin": "insulina",
    "atorvastatina": "statina",
    "rosuvastatina": "statina",
    "simvastatina": "statina",
    "statina": "statina",
    "claritromicina": "claritromicina",
    "azitromicina": "azitromicina",
    "ciprofloxacina": "ciprofloxacina",
    "tramadol": "tramadolo",
    "tramadolo": "tramadolo",
    "morfina": "oppioide",
    "fentanyl": "oppioide",
    "codeina": "oppioide",
    "oxicodone": "oppioide",
    "oxicodone hcl": "oppioide",
    "oppioide": "oppioide",
    "diazepam": "benzodiazepina",
    "lorazepam": "benzodiazepina",
    "alprazolam": "benzodiazepina",
    "xanax": "benzodiazepina",
    "benzodiazepina": "benzodiazepina",
    "spironolattone": "diuretico_potassio",
    "amiloride": "diuretico_potassio",
    "metilprednisolone": "corticosteroide",
    "prednisone": "corticosteroide",
    "cortisone": "corticosteroide",
}

_CONDITION_ALIASES: Final[dict[str, str]] = {
    "ipertensione arteriosa": "ipertensione",
    "ipertensione": "ipertensione",
    "asma bronchiale": "asma",
    "asma": "asma",
    "bpco": "bpco",
    "copd": "bpco",
    "insufficienza renale": "ckd",
    "ckd": "ckd",
    "scompenso cardiaco": "scompenso",
    "diabete mellito": "diabete",
    "diabete": "diabete",
    "epatopatia": "epatopatia",
    "cirrosi": "epatopatia",
    "gravidanza in corso": "gravidanza",
    "terapia anticoagulante": "anticoagulazione_in_corso",
}


@dataclass(frozen=True)
class InteractionFinding:
    """One drug-drug or drug-condition concern."""

    severity: InteractionSeverity
    kind: str  # "drug_drug" | "drug_condition"
    items: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity.value,
            "kind": self.kind,
            "items": list(self.items),
            "message": self.message,
        }


# (canonical_a, canonical_b): (severity, message)
# Pairs are stored sorted alphabetically so the lookup is symmetric.
_DRUG_DRUG_INTERACTIONS: Final[
    dict[tuple[str, str], tuple[InteractionSeverity, str]]
] = {
    ("asa", "warfarin"): (
        InteractionSeverity.HIGH,
        "ASA + warfarin: rischio emorragico significativamente aumentato; "
        "valutare INR e indicazione condivisa.",
    ),
    ("apixaban", "asa"): (
        InteractionSeverity.HIGH,
        "Apixaban + ASA: stacking emorragico; preferire monoterapia salvo "
        "indicazione cardiologica strict.",
    ),
    ("apixaban", "warfarin"): (
        InteractionSeverity.HIGH,
        "Apixaban + warfarin: doppio anticoagulante orale, mai associare "
        "salvo bridging temporaneo controllato.",
    ),
    ("ibuprofene", "warfarin"): (
        InteractionSeverity.HIGH,
        "FANS + warfarin: rischio emorragico aumentato e potenziamento "
        "effetto anticoagulante.",
    ),
    ("asa", "ibuprofene"): (
        InteractionSeverity.MODERATE,
        "ASA + ibuprofene: il FANS può ridurre l'effetto antiaggregante "
        "dell'ASA; distanziare le somministrazioni.",
    ),
    ("ace_inibitore", "arb"): (
        InteractionSeverity.HIGH,
        "ACE-inibitore + ARB: doppio blocco RAAS — rischio iperkaliemia, "
        "ipotensione, IRA; evitare associazione.",
    ),
    ("ace_inibitore", "diuretico_potassio"): (
        InteractionSeverity.MODERATE,
        "ACE-inibitore + diuretico risparmiatore di potassio: rischio "
        "iperkaliemia; monitorare K+ entro 7 giorni.",
    ),
    ("benzodiazepina", "oppioide"): (
        InteractionSeverity.HIGH,
        "Benzodiazepina + oppioide: depressione respiratoria sinergica; "
        "evitare associazione (FDA black-box).",
    ),
    ("benzodiazepina", "tramadolo"): (
        InteractionSeverity.HIGH,
        "Benzodiazepina + tramadolo: depressione respiratoria sinergica e "
        "rischio convulsivante; evitare associazione.",
    ),
    ("oppioide", "tramadolo"): (
        InteractionSeverity.MODERATE,
        "Tramadolo + altro oppioide: stacking serotoninergico e "
        "depressione respiratoria; preferire monoterapia.",
    ),
    ("claritromicina", "statina"): (
        InteractionSeverity.HIGH,
        "Claritromicina + statina (simvastatina/atorvastatina): rischio "
        "miopatia/rabdomiolisi via CYP3A4; sospendere statina durante il "
        "ciclo antibiotico.",
    ),
    ("ciprofloxacina", "warfarin"): (
        InteractionSeverity.MODERATE,
        "Ciprofloxacina + warfarin: potenziamento dell'anticoagulazione; "
        "controllare INR a 48-72 h.",
    ),
    ("azitromicina", "statina"): (
        InteractionSeverity.LOW,
        "Azitromicina + statina: interazione meno marcata di claritromicina, "
        "ma sorvegliare CPK se sintomi muscolari.",
    ),
}


# canonical_drug → list of (canonical_condition, severity, message).
_DRUG_CONDITION_CONTRAINDICATIONS: Final[
    dict[str, list[tuple[str, InteractionSeverity, str]]]
] = {
    "ibuprofene": [
        (
            "ckd",
            InteractionSeverity.HIGH,
            "FANS in paziente con insufficienza renale: rischio AKI; "
            "preferire paracetamolo o oppioide a basso dosaggio.",
        ),
        (
            "scompenso",
            InteractionSeverity.HIGH,
            "FANS in scompenso cardiaco: ritenzione idrica e peggioramento; evitare.",
        ),
        (
            "gravidanza",
            InteractionSeverity.HIGH,
            "FANS in gravidanza dopo 20ª settimana: rischio "
            "oligoidramnios e chiusura precoce del dotto.",
        ),
    ],
    "ketoprofene": [
        (
            "ckd",
            InteractionSeverity.HIGH,
            "FANS in paziente con insufficienza renale: rischio AKI; "
            "preferire paracetamolo o oppioide a basso dosaggio.",
        ),
    ],
    "ace_inibitore": [
        (
            "gravidanza",
            InteractionSeverity.HIGH,
            "ACE-inibitore in gravidanza: teratogeno (II-III trimestre); "
            "sospendere e considerare alternativa.",
        ),
    ],
    "arb": [
        (
            "gravidanza",
            InteractionSeverity.HIGH,
            "ARB in gravidanza: teratogeno; sospendere e considerare alternativa.",
        ),
    ],
    "metformina": [
        (
            "ckd",
            InteractionSeverity.HIGH,
            "Metformina in IRC avanzata (eGFR < 30): rischio acidosi "
            "lattica; ridurre dose o sospendere.",
        ),
        (
            "epatopatia",
            InteractionSeverity.MODERATE,
            "Metformina in epatopatia avanzata: rischio acidosi lattica "
            "aumentato; valutare alternative.",
        ),
    ],
    "corticosteroide": [
        (
            "diabete",
            InteractionSeverity.MODERATE,
            "Corticosteroide in paziente diabetico: iperglicemia attesa; "
            "intensificare monitoraggio glicemico.",
        ),
    ],
}


def _canonical_drug(name: str) -> str | None:
    key = name.strip().lower()
    return _DRUG_ALIASES.get(key)


def _canonical_condition(name: str) -> str | None:
    key = name.strip().lower()
    return _CONDITION_ALIASES.get(key)


def check_interactions(matrix: SymptomMatrix) -> list[InteractionFinding]:
    """Return drug-drug + drug-condition findings sorted by severity desc."""
    drug_keys: list[str] = []
    seen_drugs: set[str] = set()
    for med in matrix.medications:
        canonical = _canonical_drug(med)
        if canonical is None or canonical in seen_drugs:
            continue
        seen_drugs.add(canonical)
        drug_keys.append(canonical)

    condition_keys: set[str] = set()
    for cond in matrix.past_medical_history:
        canonical = _canonical_condition(cond)
        if canonical is not None:
            condition_keys.add(canonical)

    findings: list[InteractionFinding] = []

    # Drug-drug pairs (symmetric — store pairs sorted alphabetically).
    for i, a in enumerate(drug_keys):
        for b in drug_keys[i + 1 :]:
            key = (a, b) if a < b else (b, a)
            hit = _DRUG_DRUG_INTERACTIONS.get(key)
            if hit is None:
                continue
            severity, message = hit
            findings.append(
                InteractionFinding(
                    severity=severity,
                    kind="drug_drug",
                    items=key,
                    message=message,
                )
            )

    # Drug-condition.
    for drug in drug_keys:
        for cond, severity, message in _DRUG_CONDITION_CONTRAINDICATIONS.get(drug, []):
            if cond in condition_keys:
                findings.append(
                    InteractionFinding(
                        severity=severity,
                        kind="drug_condition",
                        items=(drug, cond),
                        message=message,
                    )
                )

    severity_order = {
        InteractionSeverity.HIGH: 0,
        InteractionSeverity.MODERATE: 1,
        InteractionSeverity.LOW: 2,
    }
    findings.sort(key=lambda f: severity_order[f.severity])
    return findings
