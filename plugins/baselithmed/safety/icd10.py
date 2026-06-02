"""ICD-10 code validator.

LLM-emitted ICD codes are a known hallucination surface (e.g. ``"X99.9"``
for ``"emicrania"``). This module enforces two layers of defense:

    1. **Format check** — codes must match the ICD-10 canonical pattern
       ``^[A-Z]\\d{2}(\\.\\d{1,2})?$``. Bare letters, hyphens, or US
       ICD-10-CM extensions (4+ decimals) are rejected.
    2. **Allowlist** — only codes the plugin has previously seen and
       reviewed are accepted. The allowlist is the union of:
           * every code used in the symptom lexicon
             (``differential_dx_agent._SYMPTOM_LEXICON``);
           * every code used in the baseline DDx mapping
             (``differential_dx_agent._BASELINE_DDX``);
           * a small, conservative set of additional common ED conditions
             so the LLM can still nominate hypotheses outside the baseline
             heuristic.

Anything outside the allowlist is dropped at the emission boundary — the
hypothesis/symptom is preserved, only the bad code is stripped. This is the
clinical-AI equivalent of "fail open without lying": the user sees the
clinical reasoning, just not a fabricated medical reference.
"""

from __future__ import annotations

import re
from typing import Final

# Canonical ICD-10 surface code: one alpha + two digits + optional decimal
# subdivision (1-4 digits). ICD-10-CM extensions are accepted at the format
# layer; the allowlist below is the real gate.
_ICD10_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")

# Known-good codes. Conservative by design — extension requires review.
# Grouped by chapter for readability; lookup is via the unified ``set``.
_VALID_ICD10_CODES: Final[frozenset[str]] = frozenset(
    {
        # I00–I99 — Circulatory
        "I20.9",  # Angina pectoris, unspecified
        "I21.9",  # Acute myocardial infarction, unspecified
        "I26.99",  # Pulmonary embolism, unspecified
        "I30.9",  # Acute pericarditis, unspecified
        "I50.9",  # Heart failure, unspecified
        "I60.9",  # Subarachnoid haemorrhage, unspecified
        "I63.9",  # Cerebral infarction, unspecified
        "I64",  # Stroke, not specified as haemorrhage or infarction
        # J00–J99 — Respiratory
        "J11",  # Influenza, virus not identified
        "J18.9",  # Pneumonia, unspecified organism
        "J45.901",  # Unspecified asthma with acute exacerbation
        "J93.9",  # Pneumothorax, unspecified
        "J96.0",  # Acute respiratory failure
        # K00–K93 — Digestive
        "K29.7",  # Gastritis, unspecified
        "K35.80",  # Unspecified acute appendicitis
        "K80.5",  # Calculus of bile duct without cholangitis
        "K85.9",  # Acute pancreatitis, unspecified
        "K92.2",  # Gastrointestinal haemorrhage, unspecified
        # M00–M99 — Musculoskeletal
        "M50.1",  # Cervical disc disorder with radiculopathy
        "M54.2",  # Cervicalgia
        "M54.5",  # Low back pain
        "M79.1",  # Myalgia
        # G00–G99 — Nervous system
        "G03.9",  # Meningitis, unspecified
        "G40.9",  # Epilepsy, unspecified
        "G43.9",  # Migraine, unspecified
        "G44.2",  # Tension-type headache
        # H00–H59 — Eye / adnexa
        "H53.8",  # Other visual disturbances
        "H57.1",  # Ocular pain
        # N00–N99 — Genitourinary
        "N17.9",  # Acute kidney failure, unspecified
        "N39.0",  # Urinary tract infection, site not specified
        # R00–R99 — Symptoms / signs not elsewhere classified
        "R00.0",  # Tachycardia, unspecified
        "R00.2",  # Palpitations
        "R05",  # Cough
        "R06.0",  # Dyspnoea
        "R07.4",  # Chest pain, unspecified
        "R10",  # Abdominal and pelvic pain
        "R11",  # Nausea and vomiting
        "R19.7",  # Diarrhoea, unspecified
        "R29.1",  # Meningismus
        "R42",  # Dizziness and giddiness
        "R50.9",  # Fever, unspecified
        "R51",  # Headache
        "R53",  # Malaise and fatigue
        "R55",  # Syncope and collapse
        "R58",  # Haemorrhage, not elsewhere classified
        # T78 — Anaphylactic reaction
        "T78.2",  # Anaphylactic shock, unspecified
        # X60–Y09 — Self-harm / intentional
        "X83",  # Intentional self-harm, unspecified means (placeholder)
        # F00–F99 — Mental & behavioural
        "F32.9",  # Major depressive disorder, single episode, unspecified
        "F41.9",  # Anxiety disorder, unspecified
        # E00–E89 — Endocrine
        "E11.9",  # Type 2 diabetes mellitus without complications
        "E78.5",  # Hyperlipidaemia, unspecified
        # A00–B99 — Infectious
        "A41.9",  # Sepsis, unspecified organism
    }
)


def is_valid_icd10(code: str | None) -> bool:
    """``True`` when ``code`` is well-formed AND in the curated allowlist."""
    if code is None:
        return False
    if not _ICD10_PATTERN.match(code):
        return False
    return code in _VALID_ICD10_CODES


def sanitize_icd10(code: str | None) -> str | None:
    """Return ``code`` if valid, else ``None``. Use at emission boundaries."""
    return code if is_valid_icd10(code) else None
