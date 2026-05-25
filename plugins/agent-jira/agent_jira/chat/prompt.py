from __future__ import annotations

from datetime import datetime
from typing import Any, List, Mapping, Optional, Sequence

from agent_jira.integrations.jira import JiraIssueResult
from agent_jira.project_manager import ProjectPlan
from agent_jira.config import PROJECT_PLANNER_ENABLE_TEST_CASES

CONVERSATION_SYSTEM_PROMPT = """
# AgentBot – System Prompt (Agile PM & User Story Generator)

L’assistente è **Agent-Jira**, esperto di **Project Management** e **metodologie Agile**, progettato per analizzare documenti aziendali e generare output strutturati come **Epic, User Story e Acceptance Criteria** per strumenti come **Jira**.
La data corrente è {current_date}.

---

## 🎯 MISSIONE E SCOPO

AgentBot è l’assistente virtuale ufficiale per:

- analisi della documentazione aziendale,
- estrazione dei requisiti,
- identificazione di funzionalità, attori e obiettivi,
- generazione automatica di **User Story Jira-ready**,
- supporto a PMO, Agile Coach, Product Owner e Scrum Master.

Agisce esclusivamente sulla base dei contenuti disponibili nel CONTEXT, senza inventare informazioni.

---

## 🔍 ISTRUZIONI OPERATIVE PRINCIPALI

- Usa **solo** le informazioni presenti nel CONTEXT o nella storia della conversazione.
- Se il CONTEXT è vuoto:
  > ⚠️ Non ho trovato informazioni pertinenti nei documenti.
- Mantieni un tono **professionale, sintetico, orientato all'esecuzione**.
- Se la domanda richiede User Story, generale nel formato Jira standard.

---

## 🧠 COMPETENZE SPECIALISTICHE

### Project Management
- Analisi milestone, deliverable, KPI, dipendenze.
- Generazione di RACI, RAID e piani di progetto sintetici.
- Valutazione rischi e impatti.

### Agile (Scrum, Kanban, SAFe)
- Derivazione automatica di **Epic → Feature → User Story → Task**.
- Identificazione di attori, obiettivi e benefici.
- Definizione di Acceptance Criteria con formato **Gherkin Given/When/Then** (opzionale).
- Riassunti Sprint, Definition of Ready e Definition of Done.

---

## 🧩 CREAZIONE USER STORY (RULESET)

Quando richiesto di creare User Story:

### 1. Identifica:
- attori,
- obiettivo funzionale,
- motivazione/valore,
- eventuali dipendenze.

### 2. Usa lo schema:
**User Story**
> Come *[attore]*, voglio *[obiettivo]* in modo da *[beneficio misurabile]*.

**Acceptance Criteria**
- Deve essere misurabile.
- Deve essere verificabile.
- Deve derivare dai documenti.

Formato Jira:

```
Story:
Come [attore], voglio [obiettivo] in modo da [beneficio].

Acceptance Criteria:
- [AC1]
- [AC2]
- [AC3]

Note: [dipendenze o vincoli]
Fonte: documents/...
```

---

## 📚 STILE DI RISPOSTA

- Markdown strutturato.
- Usa tabelle solo quando c’è bisogno di confrontare o allineare dati tabellari; per elenchi o requisiti preferisci paragrafi e bullet.
- Non includere mai le fonti (file, URL, percorsi) nell'output: ci pensa l'app a mostrarle in una sezione separata.
- Nessuna opinione personale.
- Nessuna inferenza non basata su documenti.
- Risposte brevi e tecniche.
- **Sintassi Italiana**: Tutte le stringhe devono essere in italiano chiaro e professionale. Le espressioni 'così da', 'in modo da', 'per', 'al fine di' devono essere SEMPRE seguite dal verbo all'infinito (es. 'per consentire', NON 'per consente'). Verifica sempre coniugazioni e concordanze prima di rispondere.

---

## ⚠️ LIMITAZIONI

- Non inventare requisiti.
- Non creare user story se mancano informazioni sufficienti.
- Non introdurre attori o funzionalità non presenti nel CONTEXT.
- Non usare conoscenza esterna.

Il modello riceverà a seguire, in questo ordine:
1. Conversazione recente (se presente).
2. Eventuale project plan e sincronizzazioni Jira già disponibili.
3. CONTEXT costruito dall'agente (documenti rilevanti).
4. DOMANDA corrente dell'utente.

Restituisci la risposta finale in italiano grammaticalmente corretto, basata **esclusivamente** sul CONTEXT.
""".strip()


def _render_history(history_text: str) -> str:
    if not history_text.strip():
        return ""
    return f"CONVERSAZIONE PRECEDENTE (ultimi turni):\n{history_text.strip()}\n\n"


def _escape_plan_table_value(value: str) -> str:
    text = (value or "—").strip()
    return text.replace("|", "\\|").replace("\n", " ")


def _normalize_test_case_steps(raw_steps: Sequence[str] | Any) -> str:
    if isinstance(raw_steps, Sequence) and not isinstance(raw_steps, (str, bytes)):
        cleaned = [str(step).strip() for step in raw_steps if str(step).strip()]
        if cleaned:
            return "; ".join(cleaned)
    return ""


def _build_plan_test_case_table(test_cases: Sequence[Any]) -> List[str]:
    if not PROJECT_PLANNER_ENABLE_TEST_CASES or not test_cases:
        return []
    lines = [
        "| # | Titolo | Obiettivo | Passi | Risultato atteso |",
        "| - | ------ | --------- | ----- | ---------------- |",
    ]
    for idx, test_case in enumerate(test_cases, start=1):
        if isinstance(test_case, Mapping):
            title = str(test_case.get("title") or "").strip() or "Test case"
            objective = str(test_case.get("objective") or "").strip()
            raw_steps = test_case.get("steps", [])
            expected = str(test_case.get("expected_result") or "").strip()
        else:
            title = getattr(test_case, "title", "").strip() or "Test case"
            objective = getattr(test_case, "objective", "").strip()
            raw_steps = getattr(test_case, "steps", [])
            expected = getattr(test_case, "expected_result", "").strip()
        steps = _normalize_test_case_steps(raw_steps)
        lines.append(
            "| {idx} | {title} | {objective} | {steps} | {expected} |".format(
                idx=idx,
                title=_escape_plan_table_value(title),
                objective=_escape_plan_table_value(objective),
                steps=_escape_plan_table_value(steps or "—"),
                expected=_escape_plan_table_value(expected or "—"),
            )
        )
    return lines


def _render_plan_section(project_plan: Optional[ProjectPlan]) -> str:
    if project_plan is None:
        return ""

    lines = ["## 🗂️ ANALISI BACKLOG DISPONIBILE"]
    summary = project_plan.functional_summary.strip()
    if summary:
        lines.append("### Sintesi funzionale")
        lines.append(summary)
    if project_plan.key_requirements:
        lines.append("### Requisiti chiave")
        for req in project_plan.key_requirements:
            if req:
                lines.append(f"- {req}")
    if project_plan.user_stories:
        lines.append("### User story candidate")
        for idx, story in enumerate(project_plan.user_stories, start=1):
            story_line = f"{idx}. **{story.title}** ({story.priority or 'Should'})"
            if story.story_points is not None:
                story_line = f"{story_line} · {story.story_points} pt"
            if story.jira_issue_key:
                story_line = f"{story_line} → Jira: {story.jira_issue_key}"
            lines.append(story_line)
            description = story.description.strip()
            if description:
                lines.append(f"    - Obiettivo: {description}")
            if story.acceptance_criteria:
                lines.append("    - Criteri di accettazione:")
                for criterion in story.acceptance_criteria:
                    lines.append(f"        • {criterion}")
            if PROJECT_PLANNER_ENABLE_TEST_CASES:
                table_lines = _build_plan_test_case_table(
                    getattr(story, "test_cases", [])
                )
                if table_lines:
                    lines.append("    - Casi di test:")
                    for table_line in table_lines:
                        lines.append(f"        {table_line}")
    if project_plan.risks:
        lines.append("### Rischi e vincoli")
        for risk in project_plan.risks:
            lines.append(f"- {risk}")
    if project_plan.open_questions:
        lines.append("### Domande aperte verso il business")
        for question in project_plan.open_questions:
            lines.append(f"- {question}")

    return "\n".join(lines) + "\n\n"


def _render_jira_section(results: Sequence[JiraIssueResult]) -> str:
    if not results:
        return ""

    lines = ["## 🧾 SINCRONIZZAZIONE JIRA"]
    for entry in results:
        if entry.error:
            lines.append(f"- {entry.summary}: errore nella creazione ({entry.error})")
        else:
            ticket = entry.key or "ticket non disponibile"
            link = entry.url or "URL non disponibile"
            status = f" · stato: {entry.status}" if entry.status else ""
            lines.append(f"- {entry.summary}: creato {ticket} ({link}){status}")
    return "\n".join(lines) + "\n\n"


def build_prompt(
    user_query: str,
    context: str,
    history_text: str,
    *,
    project_plan: Optional[ProjectPlan] = None,
    jira_results: Optional[Sequence[JiraIssueResult]] = None,
) -> str:
    current_date = datetime.now().strftime("%d/%m/%Y")
    history_section = _render_history(history_text)
    plan_section = _render_plan_section(project_plan)
    jira_section = _render_jira_section(jira_results or [])

    return f"""{CONVERSATION_SYSTEM_PROMPT}
La data corrente è {current_date}.
{history_section}{plan_section}{jira_section}### CONTEXT:
{context}

### DOMANDA:
{user_query}

---

## RISPOSTA (in italiano):
"""


__all__ = ["build_prompt", "CONVERSATION_SYSTEM_PROMPT"]
