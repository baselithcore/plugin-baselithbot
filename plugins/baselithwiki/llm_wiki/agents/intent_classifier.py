"""Intent classifier per query e CONTESTO recuperato.

Scopo: rilevare il mismatch fra intento della domanda (es. **operativa /
procedurale**: "come creare un agent?", "qual è il comando per …",
"deploy in produzione") e registro effettivo del CONTESTO recuperato
(es. **concettuale / strategico**: whitepaper, articoli divulgativi,
documenti di posizionamento aziendale).

Quando i due registri divergono il rischio è altissimo: il modello, posto
davanti a una richiesta procedurale e a chunk di prosa, riempie i vuoti
con knowledge parametrica fabbricando comandi/passaggi inesistenti. Il
RAG agent inietta un "scope warning" deterministico in cima al contesto
che il modello echeggia come premessa onesta della risposta.

Implementazione deliberatamente leggera: euristiche lessicali (no LLM
extra call). Costo trascurabile, integrazione zero-friction; preferisce
falsi negativi a falsi positivi (meglio nessun warning che warning su
ogni domanda).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

# Verbi/sostantivi tipici di query operative-procedurali (IT + EN).
# Pensate per dare segnale alto su:
#   "come creare un agent?", "qual è il comando per X", "deploy ...",
#   "scrivere uno script", "esempio di codice", "errore in produzione",
#   "passi per installare …".
_OPERATIONAL_TOKENS = (
    # imperativi/operativi italiani
    "come faccio",
    "come creo",
    "come si crea",
    "come si configura",
    "come configurare",
    "come installare",
    "come installo",
    "come eseguo",
    "come eseguire",
    "come deploy",
    "come avvio",
    "come avviare",
    "creare un",
    "creare una",
    "configurare",
    "installare",
    "eseguire",
    "deployare",
    "deploy",
    "comando",
    "script",
    "endpoint",
    "api",
    "passi per",
    "step per",
    "procedura per",
    "tutorial",
    "esempio di codice",
    "snippet",
    "rollback",
    "fix",
    "errore",
    "stack trace",
    "ci/cd",
    "kubernetes",
    "docker",
    "container",
    "pipeline",
    "build",
    "compile",
    "compilare",
    "linea di comando",
    "terminale",
    "cli",
    # imperativi/operativi inglesi
    "how do i",
    "how to",
    "command",
    "deploy",
    "install",
    "configure",
    "run",
    "execute",
    "snippet",
    "example code",
    "compile",
    "build",
)

# Token-marker presenti nei chunk operativi. Le code fence, le righe shell
# e i token CLI sono segnali forti che il documento ha registro tecnico
# eseguibile (runbook, ADR, spec, README di code base).
_OPERATIONAL_CHUNK_MARKERS = (
    "```bash",
    "```sh",
    "```shell",
    "```python",
    "```typescript",
    "```js",
    "```go",
    "```rust",
    "```sql",
    "```yaml",
    "```json",
    "```cypher",
    "$ ",
    "# !/",
    "kubectl ",
    "docker ",
    "git ",
    "npm ",
    "pip ",
    "uv ",
    "curl ",
    "wget ",
    "ssh ",
    "ssh@",
    "sudo ",
    "systemctl ",
    "make ",
    "apt-get",
    "brew ",
    "pytest",
    "rollback",
    "deploy",
    "endpoint",
)

# Marker concettuali/strategici (whitepaper, articoli, guide divulgative).
# Presenza alta + assenza di marker operativi → registro concettuale.
_CONCEPTUAL_CHUNK_MARKERS = (
    "whitepaper",
    "executive summary",
    "panoramica",
    "strategia",
    "vision",
    "principi",
    "approccio",
    "obiettivi",
    "benefit",
    "roadmap strategica",
    "framework concettuale",
    "case study",
    "background",
)

_CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\n[\s\S]*?\n```")
_SHELL_LINE_RE = re.compile(r"(?m)^\s*\$\s+\S+")
_CLI_FLAG_RE = re.compile(r"(?m)(?<![\w-])--[a-zA-Z][\w-]+")


@dataclass(frozen=True)
class IntentReport:
    """Report deterministico, serializzabile, di un singolo ciclo RAG."""

    query_intent: str  # "operational" | "conceptual" | "mixed" | "unknown"
    context_register: str  # idem, classificazione del CONTESTO
    mismatch: bool  # True ⇔ query_intent operational & context_register conceptual
    code_blocks_in_context: int
    cli_tokens_in_context: int
    operational_signal_query: int
    operational_signal_context: int
    conceptual_signal_context: int

    def warning_block(self) -> str:
        """Stringa da prepend al CONTESTO quando ``mismatch=True``.

        Marcata come commento HTML per essere visibile al modello ma non
        confondibile con un chunk di vault. L'istruzione è imperativa,
        scritta in italiano per coerenza col system prompt.
        """
        if not self.mismatch:
            return ""
        return (
            "<!-- SCOPE WARNING (sistema, non-negoziabile):\n"
            "La domanda dell'utente ha un INTENTO OPERATIVO/PROCEDURALE\n"
            "(richiede passaggi, comandi, snippet di codice o procedure\n"
            "eseguibili), ma il CONTESTO recuperato dal vault è di registro\n"
            "CONCETTUALE/STRATEGICO/DIVULGATIVO (prosa di alto livello,\n"
            "principi, panoramiche). Apri la tua risposta dichiarando\n"
            "esplicitamente questo gap nelle prime 2-3 righe — esempio:\n"
            "'La conoscenza disponibile nel vault è di livello strategico,\n"
            "non operativo: non contiene comandi, script o procedure\n"
            "tecniche eseguibili. Posso però sintetizzare i principi e le\n"
            "raccomandazioni che il documento espone.'\n"
            "NON improvvisare procedure tecniche, comandi CLI o codice\n"
            "che il CONTESTO non contiene. -->\n\n"
        )


def _count_signals(text: str, tokens: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for t in tokens if t in lowered)


def classify_query_intent(question: str) -> tuple[str, int]:
    """Ritorna (intent, signal_count) per la query.

    intent ∈ {"operational", "conceptual", "mixed", "unknown"}.
    Soglia minima 2 token operativi → operational, 0 → conceptual (per
    default tutte le query non-operative sono concettuali, registro
    discorsivo), 1 → unknown (ambiguo).
    """
    if not question or not question.strip():
        return ("unknown", 0)
    op = _count_signals(question, _OPERATIONAL_TOKENS)
    if op >= 2:
        return ("operational", op)
    if op == 1:
        return ("mixed", op)
    return ("conceptual", op)


def classify_context_register(context_text: str) -> tuple[str, dict[str, int]]:
    """Classifica il registro del CONTESTO costruito dal retrieval.

    Conta code fence, righe shell, flag CLI, marker concettuali. Ritorna
    intent + diagnostiche per logging/telemetria.
    """
    if not context_text or not context_text.strip():
        return ("unknown", {"code_blocks": 0, "cli_tokens": 0, "concept_tokens": 0})

    code_blocks = len(_CODE_FENCE_RE.findall(context_text))
    shell_lines = len(_SHELL_LINE_RE.findall(context_text))
    cli_flags = len(_CLI_FLAG_RE.findall(context_text))
    operational_marker_hits = _count_signals(context_text, _OPERATIONAL_CHUNK_MARKERS)
    conceptual_marker_hits = _count_signals(context_text, _CONCEPTUAL_CHUNK_MARKERS)

    operational_signal = (
        code_blocks * 3 + shell_lines + cli_flags + operational_marker_hits
    )
    diagnostics = {
        "code_blocks": code_blocks,
        "cli_tokens": shell_lines + cli_flags,
        "concept_tokens": conceptual_marker_hits,
    }

    if operational_signal >= 3 and conceptual_marker_hits <= operational_signal:
        return ("operational", diagnostics)
    if conceptual_marker_hits >= 2 and operational_signal < 3:
        return ("conceptual", diagnostics)
    if operational_signal >= 2 and conceptual_marker_hits >= 2:
        return ("mixed", diagnostics)
    if operational_signal == 0 and conceptual_marker_hits == 0:
        return ("unknown", diagnostics)
    return ("conceptual" if operational_signal < 3 else "operational", diagnostics)


def majority_register_from_hits(hits: list[dict[str, Any]]) -> str:
    """Voto di maggioranza su ``doc_register`` letto dai payload Qdrant.

    Iniettato a ingest time da :mod:`ingest_raw.register`, è il signal
    più affidabile (deterministico, persistito): supera l'euristica
    regex su `context_text` quando entrambi sono presenti. Output
    ``unknown`` se nessun hit espone ``doc_register`` o se i registri
    si bilanciano fra operational e conceptual (→ ``mixed``).
    """
    if not hits:
        return "unknown"
    counts: Counter[str] = Counter()
    for h in hits:
        payload = h.get("payload") or {}
        reg = str(payload.get("doc_register") or "").strip().lower()
        if reg in {"operational", "conceptual", "mixed"}:
            counts[reg] += 1
    if not counts:
        return "unknown"
    if (
        counts.get("mixed", 0) > 0
        and counts.get("operational", 0)
        and counts.get("conceptual", 0)
    ):
        return "mixed"
    op = counts.get("operational", 0)
    co = counts.get("conceptual", 0)
    if op > 0 and co == 0:
        return "operational"
    if co > 0 and op == 0:
        return "conceptual"
    if op == co:
        return "mixed"
    return "operational" if op > co else "conceptual"


def analyze(
    question: str,
    context_text: str,
    *,
    hits: list[dict[str, Any]] | None = None,
) -> IntentReport:
    """Routine end-to-end usata dal RAG agent.

    Priorità segnali per ``context_register``:
    1. Metadati espliciti ``doc_register`` nei payload (via ``hits``) —
       ingest-time, deterministici, fonte autorevole.
    2. Fallback: euristica regex su ``context_text``.

    Mismatch ⇔ query operational e contesto NON operativo. Casi
    misti/incerti non triggerano warning: si preferisce falso-negativo
    a falso-positivo.
    """
    q_intent, q_signal = classify_query_intent(question)

    explicit = majority_register_from_hits(hits or [])
    if explicit != "unknown":
        # Manteniamo le diagnostiche regex per logging/telemetria anche
        # quando il signal autorevole arriva dai metadati.
        _, diag = classify_context_register(context_text)
        c_register = explicit
    else:
        c_register, diag = classify_context_register(context_text)

    mismatch = q_intent == "operational" and c_register in {"conceptual", "unknown"}

    return IntentReport(
        query_intent=q_intent,
        context_register=c_register,
        mismatch=mismatch,
        code_blocks_in_context=diag["code_blocks"],
        cli_tokens_in_context=diag["cli_tokens"],
        operational_signal_query=q_signal,
        conceptual_signal_context=diag["concept_tokens"],
        operational_signal_context=(diag["code_blocks"] * 3 + diag["cli_tokens"]),
    )


__all__ = [
    "IntentReport",
    "analyze",
    "classify_context_register",
    "classify_query_intent",
]
