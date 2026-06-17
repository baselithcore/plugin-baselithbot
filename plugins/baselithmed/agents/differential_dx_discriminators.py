"""
Per-condition discriminator questions for the differential diagnosis agent.

Separated from the main lexicon table so the lexicon module stays under the
500 LOC cap.
"""

from __future__ import annotations

from typing import Final

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
