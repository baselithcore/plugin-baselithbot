"""Groundedness scorer (LLM-as-judge) post-generazione.

Implementa la difesa #2 raccomandata dai criteri di valutazione: dopo
che il RAG ha generato una risposta, un secondo LLM call vincolato a
JSON-schema confronta ogni claim con i chunk recuperati e ritorna
una metrica ``supported_ratio`` ∈ [0,1].

Sotto soglia configurabile (``RAG_GROUNDEDNESS_MIN``) il chiamante può:
1. rigenerare la risposta con prompt rafforzato (path ``answer``);
2. emettere evento ``groundedness_warning`` nello stream UI (path ``stream``);
3. loggare e basta (default OFF: nessun costo extra).

Cost model: 1 LLM call extra per turn quando attivo. Su Ollama remoto
con `gpt-oss:20b` aggiunge ~5–15s; su `qwen2.5:7b-instruct` ~1–3s; su
OpenAI ~500ms. Quindi OFF di default — il sistema funziona già con
intent-guard + sampling determinitisco + anchor citations, questo è
il livello di paranoia massimo per deploy regolati (medico/legale).

Implementazione deliberatamente snella (<200 LOC):
- splitting in claim via separatori `.`, `!`, `?` con filtro dei wikilink;
- 1 call structured-output che ritorna ``{claims: [{text, supported, note}]}``;
- aggregazione + threshold;
- repair loop opzionale (rigenerazione con feedback delle unsupported).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from llm_wiki.utils.llm import generate

logger = logging.getLogger(__name__)


_CLAIM_SPLIT_RE = re.compile(r"(?<=[\.!?])\s+(?=[A-ZÀ-Ý])")
# Wikilink pieni `[[…]]`, code fences, sezioni "Fonti:" non sono claim:
# vanno filtrati prima dello scoring per non gonfiare il denominatore.
_WIKILINK_FULL_LINE_RE = re.compile(r"^\s*[-*•]?\s*\[\[[^\]]+\]\]\s*$")
_FONTI_HEADER_RE = re.compile(r"^\s*(##+\s*)?Fonti[:\s]*$", re.IGNORECASE)


@dataclass
class ClaimScore:
    text: str
    supported: bool
    note: str = ""


@dataclass
class GroundednessReport:
    claims: list[ClaimScore] = field(default_factory=list)
    supported_ratio: float = 1.0
    threshold: float = 0.95
    below_threshold: bool = False
    raw_response: str = ""

    def summary(self) -> str:
        return (
            f"groundedness {self.supported_ratio:.2f} "
            f"({sum(1 for c in self.claims if c.supported)}/{len(self.claims)} claim, "
            f"soglia {self.threshold:.2f})"
        )

    def unsupported_claims(self) -> list[ClaimScore]:
        return [c for c in self.claims if not c.supported]


def split_into_claims(answer: str) -> list[str]:
    """Tokenizza la risposta in claim atomici.

    Esclude wikilink stand-alone (es. liste in ``Fonti:``), code fence,
    intestazioni di sezione vuote, righe < 20 char (segnale rumoroso).
    Conserva l'ordine — utile per evidenziare quale claim ha fallito.
    """
    out: list[str] = []
    inside_code = False
    skip_section = False
    for raw_line in answer.split("\n"):
        line = raw_line.strip()
        if line.startswith("```"):
            inside_code = not inside_code
            continue
        if inside_code or not line:
            continue
        if _FONTI_HEADER_RE.match(line):
            skip_section = True
            continue
        if skip_section:
            # tutto ciò che segue "Fonti:" è una lista citation-only
            continue
        if _WIKILINK_FULL_LINE_RE.match(line):
            continue
        if line.startswith("#"):
            continue
        # spezza in claim multiple frasi
        for piece in _CLAIM_SPLIT_RE.split(line):
            piece = piece.strip(" -*•")
            if len(piece) >= 20:
                out.append(piece)
    return out


_JUDGE_SYSTEM = """\
Sei un valutatore deterministico di groundedness per un sistema RAG.
Ricevi un CONTESTO (chunk recuperati dal vault) e una lista di CLAIM
estratti dalla risposta generata. Per ogni claim devi decidere se è
**supportato** dal CONTESTO.

Regole:
- "supported=true" SOLO se il claim può essere verificato direttamente
  da almeno un passaggio del CONTESTO (anche parafrasato, ma con
  sostanza identica). Mai inferire o "completare" il senso.
- "supported=false" se il claim aggiunge dettagli, comandi, numeri,
  procedure, nomi che il CONTESTO non contiene esplicitamente.
- "supported=false" se il claim contraddice il CONTESTO.
- In caso di dubbio rispondi "supported=false" (preferiamo
  falsi-negativi a falsi-positivi).

Output: SOLO JSON con la forma esatta:
{"claims": [{"text": "<claim>", "supported": true|false, "note": "<motivo in <80 char>"}]}
"""


def score(
    answer: str,
    context: str,
    *,
    threshold: float = 0.95,
    model: str | None = None,
) -> GroundednessReport:
    """Esegui lo scoring. Eccezioni → report neutro (supported_ratio=1.0).

    Il chiamante decide cosa fare con un report ``below_threshold=True``
    (warning, rigenera, blocca).
    """
    claims = split_into_claims(answer)
    if not claims:
        return GroundednessReport(threshold=threshold)

    user_prompt = (
        "CONTESTO:\n"
        f"{context}\n\n"
        "CLAIM da valutare (lista, mantenere l'ordine):\n"
        + "\n".join(f"- {c}" for c in claims)
        + "\n\nRispondi SOLO con il JSON object."
    )
    try:
        raw = generate(
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            json_mode=True,
            use_cache=False,
            options={"temperature": 0.0, "top_p": 1.0},
        )
    except Exception as exc:
        logger.warning("[groundedness] LLM judge failed (%s) — skip scoring", exc)
        return GroundednessReport(threshold=threshold, raw_response=str(exc))

    parsed = _safe_parse_judge(raw, claims)
    supported = sum(1 for c in parsed if c.supported)
    ratio = supported / len(parsed) if parsed else 1.0
    return GroundednessReport(
        claims=parsed,
        supported_ratio=ratio,
        threshold=threshold,
        below_threshold=ratio < threshold,
        raw_response=raw,
    )


def _safe_parse_judge(raw: str, claims: list[str]) -> list[ClaimScore]:
    """Parsing tollerante del JSON ritornato dal judge.

    Fallback: se il parsing fallisce, marca tutto come unsupported con
    nota diagnostica — più conservativo del trust-by-default.
    """
    try:
        body = raw.strip()
        if body.startswith("```"):
            body = body.split("```", 2)[1]
            if body.startswith("json"):
                body = body[4:]
            body = body.split("```", 1)[0]
        data = json.loads(body)
        items = data.get("claims") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ValueError("missing 'claims' list")
        out: list[ClaimScore] = []
        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            text = str(raw_item.get("text") or "").strip()
            if not text:
                continue
            supported = bool(raw_item.get("supported", False))
            note = str(raw_item.get("note") or "").strip()[:120]
            out.append(ClaimScore(text=text, supported=supported, note=note))
        return out or [ClaimScore(text=c, supported=False, note="parse: empty") for c in claims]
    except Exception as exc:
        logger.warning("[groundedness] parse failed: %s — fallback to unsupported", exc)
        return [ClaimScore(text=c, supported=False, note=f"parse_error: {exc}") for c in claims]


def repair_feedback(report: GroundednessReport) -> str:
    """Genera istruzione di repair per un secondo LLM pass.

    Lista i claim unsupported + invita a rimuoverli/correggerli usando
    SOLO informazioni del CONTESTO già fornito. NON ri-cita il CONTESTO
    (è già nella conversation history dell'agent).
    """
    unsup = report.unsupported_claims()
    if not unsup:
        return ""
    bullets = "\n".join(f"- «{c.text}»  → motivo: {c.note or 'non supportato'}" for c in unsup)
    return (
        "GROUNDEDNESS VIOLATION rilevata. I seguenti claim della tua risposta "
        "non sono supportati dal CONTESTO che hai a disposizione:\n\n"
        f"{bullets}\n\n"
        "Riscrivi la risposta:\n"
        "1. RIMUOVI ogni claim non supportato sopra.\n"
        "2. Dichiara esplicitamente quali aspetti della domanda non puoi "
        "rispondere perché non coperti dal CONTESTO.\n"
        "3. Mantieni invece tutti i claim NON elencati (sono supportati).\n"
        "4. Mantieni la sezione `Fonti:` con i wikilink Obsidian usati."
    )


__all__ = [
    "ClaimScore",
    "GroundednessReport",
    "repair_feedback",
    "score",
    "split_into_claims",
]
