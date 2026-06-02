"""Code-block guard — vieta la fabbricazione di snippet di codice.

Implementa la difesa specifica raccomandata dai criteri: il modello,
posto davanti a una domanda operativa su un corpus concettuale, tende
a fabbricare blocchi di codice (script Python, comandi bash, YAML
Kubernetes) anche se il CONTESTO non contiene neanche una riga di
codice. Il pattern è particolarmente forte sui termini "agente",
"deploy", "configurazione".

Questo modulo:

1. Estrae i code fence dalla risposta generata.
2. Estrae i code fence dal CONTESTO recuperato.
3. Se la risposta contiene codice ma il CONTESTO no → violazione.
4. Se la risposta contiene un linguaggio (es. ``python``) assente nel
   CONTESTO → violazione (il modello ha inventato la lingua).

Output: ``CodeBlockReport`` con liste violations + helper per emettere
una nota da inserire nel feedback di repair, oppure un evento UI per
lo stream.

Difesa deterministica (no LLM call), zero costo. Complementare al
``groundedness`` scorer (LLM-as-judge): qui catturiamo violazioni
puramente strutturali (presenza/assenza di code-fence), il judge
cattura violazioni semantiche (claim non supportato).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Linguaggio dopo i tre backtick. Cattura anche fence senza linguaggio
# (`\`\`\`` puro) → ``lang=""``.
_FENCE_OPEN_RE = re.compile(r"```([a-zA-Z0-9_+\-]*)\s*\n")
# Inline code `…` deliberatamente NON catturato: il falso positivo
# sarebbe troppo alto (nomi di file, variabili).


@dataclass
class CodeFence:
    language: str  # lowercase; "" se assente
    body: str  # contenuto fra le fence


@dataclass
class CodeBlockReport:
    answer_fences: list[CodeFence] = field(default_factory=list)
    context_fences: list[CodeFence] = field(default_factory=list)
    answer_only_langs: list[str] = field(
        default_factory=list
    )  # langs nella risposta non nel contesto
    answer_has_code_context_does_not: bool = False
    has_violations: bool = False

    def summary(self) -> str:
        if not self.has_violations:
            return "code-block guard ok"
        parts: list[str] = []
        if self.answer_has_code_context_does_not:
            parts.append(
                f"risposta ha {len(self.answer_fences)} code block, CONTESTO nessuno"
            )
        if self.answer_only_langs:
            parts.append(f"lingue fabbricate: {', '.join(self.answer_only_langs)}")
        return "; ".join(parts)


def extract_fences(text: str) -> list[CodeFence]:
    """Estrai blocchi ``\\`\\`\\`<lang>\\n…\\n\\`\\`\\``` da ``text``.

    Tolerante: fence aperto senza chiusura → preso fino a EOF.
    """
    if not text:
        return []
    out: list[CodeFence] = []
    pos = 0
    while True:
        m = _FENCE_OPEN_RE.search(text, pos)
        if not m:
            break
        lang = (m.group(1) or "").strip().lower()
        body_start = m.end()
        close_idx = text.find("\n```", body_start)
        if close_idx < 0:
            body = text[body_start:].rstrip()
            pos = len(text)
        else:
            body = text[body_start:close_idx].rstrip()
            pos = close_idx + len("\n```")
        out.append(CodeFence(language=lang, body=body))
    return out


def analyze(answer: str, context: str) -> CodeBlockReport:
    """Confronta i code fence di ``answer`` con quelli del ``context``.

    Regola 1 (assoluta): se il CONTESTO non ha alcun fence ma la risposta
    sì → violazione (il modello ha inventato i blocchi).

    Regola 2 (di lingua): se la risposta usa un linguaggio (es. python)
    che non compare in alcun fence del CONTESTO → la riga di linguaggio
    è inventata. Più una euristica anti-LLM-bias (modello sceglie
    "python" come default) che un controllo strutturale.

    Casi neutri (no violazione):
    - Entrambi senza fence.
    - Risposta senza fence, CONTESTO con fence.
    - Risposta con fence + CONTESTO con fence sullo stesso linguaggio.
    """
    a_fences = extract_fences(answer)
    c_fences = extract_fences(context)

    report = CodeBlockReport(answer_fences=a_fences, context_fences=c_fences)

    if a_fences and not c_fences:
        report.answer_has_code_context_does_not = True
        report.has_violations = True
        return report

    if a_fences and c_fences:
        ctx_langs = {f.language for f in c_fences if f.language}
        bad_langs: list[str] = []
        for f in a_fences:
            if not f.language:
                continue
            if f.language not in ctx_langs:
                bad_langs.append(f.language)
        if bad_langs:
            report.answer_only_langs = sorted(set(bad_langs))
            report.has_violations = True

    return report


def repair_feedback(report: CodeBlockReport) -> str:
    """Genera un feedback breve da iniettare in un secondo pass LLM.

    Niente verbose: l'agent ha appena visto il CONTESTO, gli ricordiamo
    solo cosa rimuovere e perché.
    """
    if not report.has_violations:
        return ""
    parts: list[str] = ["CODE BLOCK VIOLATION rilevata."]
    if report.answer_has_code_context_does_not:
        parts.append(
            "La tua risposta contiene blocchi di codice fenced (```…```), ma "
            "il CONTESTO non ne contiene **nessuno**. Stai fabbricando "
            "codice non presente nei chunk recuperati."
        )
    if report.answer_only_langs:
        parts.append(
            "I seguenti linguaggi compaiono nella tua risposta ma NON nel "
            f"CONTESTO: {', '.join(report.answer_only_langs)}. Rimuovili — "
            "sono LLM-bias (es. Python come default operativo) non "
            "supportato dalla fonte."
        )
    parts.append(
        "Riscrivi la risposta SENZA blocchi di codice fabbricati. Se la "
        "domanda richiede codice ma il CONTESTO non lo contiene: "
        "dichiara onestamente che il vault non contiene snippet "
        "eseguibili sull'argomento."
    )
    return " ".join(parts)


def strip_fabricated_fences(answer: str, report: CodeBlockReport) -> str:
    """Versione "hard": rimuovi materialmente i blocchi fabbricati.

    Usata dal repair-loop come fallback quando il LLM repair fallisce
    o non disponibile. Preserva il testo prosaico fra le fence,
    cancella solo i fence stessi + il loro contenuto + i fence di
    chiusura. Conservativa: in caso di parsing ambiguo, lascia il testo
    intatto.

    Walk-pattern allineato a :func:`extract_fences`: avanza `pos` al
    di là di ogni fence di chiusura prima di cercare il prossimo
    apertura, così la stessa ``\\`\\`\\``` di chiusura non viene
    interpretata come nuova apertura.
    """
    if not report.has_violations or not answer:
        return answer
    if report.answer_has_code_context_does_not:
        bad_langs: set[str] | None = None  # rimuovi tutti
    elif report.answer_only_langs:
        bad_langs = set(report.answer_only_langs)
    else:
        return answer

    out: list[str] = []
    pos = 0
    while True:
        m = _FENCE_OPEN_RE.search(answer, pos)
        if not m:
            out.append(answer[pos:])
            break
        lang = (m.group(1) or "").strip().lower()
        body_start = m.end()
        close_idx = answer.find("\n```", body_start)
        end_pos = close_idx + len("\n```") if close_idx >= 0 else len(answer)
        if bad_langs is None or lang in bad_langs:
            out.append(answer[pos : m.start()])
        else:
            out.append(answer[pos:end_pos])
        pos = end_pos
    return "".join(out).strip()


__all__ = [
    "CodeBlockReport",
    "CodeFence",
    "analyze",
    "extract_fences",
    "repair_feedback",
    "strip_fabricated_fences",
]
