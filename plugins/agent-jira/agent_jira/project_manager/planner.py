import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from agent_jira.agents.metadata import QueryAnalyzer
from agent_jira.cost_control import BudgetExceededError
from agent_jira.llm import generate_response
from agent_jira.project_manager.models import ProjectPlan
from agent_jira.project_manager.story_count import parse_requested_story_count
from agent_jira.config import OLLAMA_MODEL, PROJECT_PLANNER_MIN_SCENARIOS

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent_jira.test_case_generator import TestCaseGenerator


class ProjectPlanner:
    """Genera backlog e user story a partire dal contesto fornito."""

    def __init__(
        self,
        *,
        model: str = OLLAMA_MODEL,
        max_user_stories: int = 6,
        min_scenarios: int = PROJECT_PLANNER_MIN_SCENARIOS,
        include_test_cases: bool = True,
        test_case_generator: Optional["TestCaseGenerator"] = None,
    ) -> None:
        self.model = model
        self.max_user_stories = max(1, max_user_stories)
        self.min_scenarios = max(1, min_scenarios)
        self.include_test_cases = include_test_cases
        self.test_case_generator = test_case_generator

    def generate_plan(
        self,
        *,
        query: str,
        context: str,
        history_text: str,
        jira_project_key: Optional[str] = None,
        max_stories: Optional[int] = None,
        include_tests: Optional[bool] = None,
        metadata_brief: Optional[str] = None,
    ) -> ProjectPlan:
        """
        Genera il piano di progetto chiamando l'LLM.
        """
        if max_stories:
            logger.info(
                f"ProjectPlanner: generating plan with STRICT max_stories={max_stories}"
            )
        else:
            logger.info(
                f"ProjectPlanner: generating plan with default max_stories={self.max_user_stories}"
            )

        if not context.strip():
            return self._fallback_plan(query)

        # Use overrides or defaults
        effective_max_stories = (
            max_stories if max_stories is not None else self.max_user_stories
        )
        exact_story_count = (
            max_stories is not None
            and parse_requested_story_count(query, default=None) == max_stories
        )
        effective_include_tests = (
            include_tests if include_tests is not None else self.include_test_cases
        )

        logger.info(
            f"ProjectPlanner.generate_plan: max_stories arg={max_stories}, "
            f"self.max_user_stories={self.max_user_stories}, "
            f"effective={effective_max_stories}"
        )

        prompt = self._build_prompt(
            query=query,
            context=context,
            history=history_text,
            jira_project_key=jira_project_key,
            max_stories=effective_max_stories,
            exact_story_count=exact_story_count,
            metadata_brief=metadata_brief,
            include_test_cases=effective_include_tests,
        )
        try:
            raw_result = generate_response(prompt, model=self.model)
        except BudgetExceededError:
            logger.error("Planner interrotto: budget superato (token/query limit).")
            raise
        except Exception:
            logger.exception("Impossibile generare il piano: errore LLM")
            return self._fallback_plan(query)

        payload = self._parse_payload(raw_result)
        if not payload:
            logger.warning("Planner LLM ha prodotto un output non valido.")
            logger.warning(f"Raw LLM output (first 1000 chars): {raw_result[:1000]}")
            return self._fallback_plan(query)

        plan = ProjectPlan.from_payload(payload)
        plan = self._repair_story_count_if_needed(
            plan=plan,
            query=query,
            context=context,
            history_text=history_text,
            jira_project_key=jira_project_key,
            exact_story_count=exact_story_count,
            target_story_count=effective_max_stories,
            metadata_brief=metadata_brief,
        )
        if not plan.functional_summary:
            plan.functional_summary = (
                "Analisi agile non disponibile: nessun riassunto fornito dal modello."
            )

        if plan.user_stories:
            plan.user_stories = plan.user_stories[:effective_max_stories]
            # Test cases are now generated inline by the planner prompt
            # (single LLM call instead of separate test_case_generator pass).
            # If the planner didn't produce test_cases, ensure empty list.
            if not effective_include_tests:
                for story in plan.user_stories:
                    story.test_cases = []

        return plan

    def _build_prompt(
        self,
        *,
        query: str,
        context: str,
        history: str,
        jira_project_key: Optional[str] = None,
        max_stories: Optional[int] = None,
        exact_story_count: bool = False,
        metadata_brief: Optional[str] = None,
        include_test_cases: bool = True,
    ) -> str:
        query_metadata = QueryAnalyzer().analyze_query(query)
        history_block = ""
        if history.strip():
            history_block = "### Conversazione precedente rilevante\n{}\n\n".format(
                history.strip()
            )

        metadata_block = ""
        if metadata_brief and metadata_brief.strip():
            metadata_block = f"{metadata_brief.strip()}\n\n"

        query_metadata_lines = []
        if query_metadata.request_type:
            query_metadata_lines.append(
                f"- Tipo richiesta: {query_metadata.request_type}"
            )
        if query_metadata.feature_module:
            query_metadata_lines.append(
                f"- Modulo richiesto: {query_metadata.feature_module}"
            )
        if query_metadata.priority:
            query_metadata_lines.append(
                f"- Priorità percepita: {query_metadata.priority}"
            )
        if query_metadata.quantity is not None:
            query_metadata_lines.append(
                f"- Quantità richiesta: {query_metadata.quantity}"
            )
        if query_metadata.mentioned_stakeholders:
            query_metadata_lines.append(
                "- Stakeholder citati: "
                + ", ".join(query_metadata.mentioned_stakeholders[:5])
            )

        query_metadata_block = ""
        if query_metadata_lines:
            query_metadata_block = "### Metadati della richiesta utente\n{}\n\n".format(
                "\n".join(query_metadata_lines)
            )

        limit_stories = (
            max_stories if max_stories is not None else self.max_user_stories
        )

        objectives = [
            "Estrarre i requisiti funzionali chiave dal documento analizzato, assegnando a ciascuno un ID univoco.",
            (
                f"Elaborare fino a {limit_stories} user story complete e distinte, ma solo se integralmente supportate dal documento."
                if exact_story_count
                else f"Elaborare al massimo {limit_stories} user story complete, ciascuna con scenari BDD generati automaticamente in numero variabile."
            ),
            "Associare ogni user story ai requisiti che soddisfa (satisfied_requirements).",
            "Produrre acceptance criteria chiari e verificabili.",
            "Evidenziare rischi e domande aperte utili al team di progetto.",
        ]

        if jira_project_key:
            objectives.append(
                f"Utilizzare '{jira_project_key}' come progetto Jira predefinito per le user story "
                f"(il campo 'jira_project_key' potrà essere modificato per ogni singola story prima della sincronizzazione)."
            )

        objectives_block = "\n".join(
            f"{idx}. {text}" for idx, text in enumerate(objectives, start=1)
        )

        guidelines = [
            # Linee guida generali
            "- Usa solo le informazioni contenute nel context e nella conversazione.",
            "- Usa esclusivamente informazioni esplicite del documento o inferenze minime ad alta confidenza immediatamente ancorate al testo.",
            "- Non usare conoscenza generale di dominio, best practice esterne o supposizioni per completare campi mancanti.",
            "- Se un'informazione non è supportata dal documento, non inventarla: lasciala fuori oppure trasformala in open_questions.",
            "- Mantieni tutte le stringhe in italiano chiaro, professionale e grammaticalmente ineccepibile.",
            "- **Sintassi Italiana**: Le espressioni 'così da', 'in modo da', 'per', 'al fine di' devono essere SEMPRE seguite dal verbo all'infinito (es. 'per consentire', NON 'per consente').",
            "- Evita riferimenti espliciti ai percorsi dei file; descrivi solo concetti funzionali.",
            "- Ogni requisito, rischio, domanda aperta e user story deve essere tracciabile al contenuto del documento.",
            # Requisiti
            "- I requisiti strutturati devono avere ID brevi e progressivi (es. REQ-01, REQ-02).",
            "- Non creare requisiti impliciti deboli: se il testo non è sufficiente, registra il gap tra le open_questions.",
            # Linee guida BDD
            f"- Genera almeno {self.min_scenarios} scenari BDD per ogni user story; aggiungi ulteriori scenari solo se supportati dal documento (percorsi alternativi, eccezioni, variazioni di stato).",
            "- Usa ID incrementali per gli scenari: SCENARIO_01, SCENARIO_02, SCENARIO_03...",
            "- Ogni scenario deve includere blocchi separati: Given, When, Then.",
            "- I risultati nei blocchi Then devono essere verificabili, oggettivi e non ambigui.",
            "- Non generare scenari ridondanti o non supportati dal documento analizzato.",
            "- Gli scenari devono derivare esclusivamente dalle informazioni presenti nel documento.",
            "- Non introdurre eccezioni, validazioni, attori, integrazioni o transizioni di stato assenti dal documento.",
            "- Se role, goal o benefit non sono esplicitamente deducibili, usa formulazioni prudenti e minimali senza aggiungere dettagli non presenti.",
            "- **Qualità Linguistica**: Prima di restituire il JSON, verifica che le descrizioni non contengano errori di sintassi o coniugazioni errate.",
            "- Acceptance criteria e BDD devono descrivere solo condizioni, azioni ed esiti osservabili nel documento.",
        ]

        if jira_project_key:
            guidelines.append(
                f"- Il campo 'jira_project_key' dovrebbe essere '{jira_project_key}' come valore predefinito, "
                f"ma l'utente potrà modificarlo per ogni storia prima della sincronizzazione."
            )
        if exact_story_count:
            guidelines.extend(
                [
                    f"- Prova a raggiungere {limit_stories} user story solo se il documento contiene evidenze sufficienti; la copertura del documento ha priorità sul conteggio richiesto.",
                    "- Se il contesto è denso, suddividi i requisiti in vertical slice distinte e non duplicative.",
                    "- Se il contesto è limitato, restituisci meno storie invece di inventare funzionalità fuori ambito e spiega i gap nelle open_questions.",
                ]
            )

        if include_test_cases:
            guidelines.append(
                "- Per ogni user story, genera 1-2 test case strutturati con: title, objective, preconditions, test_data, steps, expected_result, priority, labels. Copri golden path e almeno un caso negativo."
            )

        guidelines_block = "\n".join(guidelines)

        test_cases_schema = ""
        if include_test_cases:
            test_cases_schema = """,
      "test_cases": [
        {{
          "title": "TC-1 Titolo test case",
          "objective": "Cosa verifica questo test",
          "preconditions": ["Condizione necessaria"],
          "test_data": ["Dato di test"],
          "steps": ["Passo 1", "Passo 2"],
          "expected_result": "Risultato atteso",
          "priority": "High|Medium|Low",
          "labels": ["test-case", "qa"],
          "jira_issue_type": "Test Case"
        }}
      ]"""

        return f"""SYSTEM
Sei un Agile Project Manager senior incaricato di analizzare documentazione tecnica.
Protocollo obbligatorio:
1. Considera il documento come unica fonte di verità.
2. Non inventare mai requisiti, flussi, attori, sistemi, regole, eccezioni o dettagli implementativi non presenti.
3. Quando il documento è ambiguo o incompleto, riduci l'output e registra il dubbio in open_questions.
4. Se un campo non è supportato dal documento, preferisci omissione, formulazione prudente o array vuoto.
5. La fedeltà al documento viene prima di completezza, creatività o rispetto del conteggio richiesto.

TASK
Il tuo obiettivo è:
{objectives_block}

Restituisci **solo JSON valido** in italiano con la seguente struttura:
{{
  "functional_summary": "riassunto funzionale",
  "key_requirements": ["testo req 1", "testo req 2"],
  "structured_requirements": [
      {{ "id": "REQ-01", "text": "Il sistema deve permettere l'autenticazione a due fattori." }},
      {{ "id": "REQ-02", "text": "Gli utenti devono poter reimpostare la password in autonomia." }}
  ],
  "user_stories": [
    {{
      "title": "titolo sintetico",
      "role": "Chi beneficia (es. HR Manager)",
      "goal": "Cosa vuole ottenere",
      "benefit": "Perché è utile",
      "description": "descrizione orientata al valore",
      "business_value": [
        "Outcome misurabile o beneficio concreto 1",
        "Impatto su processo/tempo/costi/qualità 2",
        "Beneficio per stakeholder specifico 3"
      ],
      "acceptance_criteria": ["criterio 1", "criterio 2"],
      "priority": "Highest|High|Medium|Low|Lowest",
      "story_points": 3,
      "labels": ["agent-jira", "automated"],
      "satisfied_requirements": ["REQ-01"],
      "bdd_scenarios": [
        {{
          "id": "SCENARIO_01",
          "title": "Titolo dello scenario",
          "given": [
            "Condizione iniziale o contesto rilevante",
            "Altre condizioni se presenti"
          ],
          "when": [
            "Azione dell'utente o evento scatenante"
          ],
          "then": [
            "Risultato atteso verificabile",
            "Ulteriori risultati se necessari"
          ]
        }}
      ]{test_cases_schema}
    }}
  ],
  "risks": ["rischio 1"],
  "open_questions": ["domanda 1"]
}}

Linee guida generali:
{guidelines_block}
- Compila sempre role, goal e benefit con frasi specifiche tratte dal contesto.
- La description deve espandere role/goal/benefit in forma fluida orientata al valore.
- Se role, goal o benefit non sono interamente supportati dal documento, mantienili generici ma aderenti al testo senza aggiungere dettagli inventati.
- Il campo business_value deve contenere esattamente 3 punti sintetici e concreti:
  * Non ripetere la frase "Come <ruolo> voglio <goal> così da <benefit>"
  * Esprimi outcome misurabili, benefici per stakeholder specifici, o impatti su processo/tempo/costi/qualità
  * Mantieni ogni punto breve (max 1-2 righe)
  * Non introdurre outcome non supportati dal documento
- Il campo open_questions deve raccogliere in modo esplicito tutti i buchi informativi che impediscono un'analisi completa.
- Se il documento non giustifica una user story, non crearla.

{history_block}
{metadata_block}{query_metadata_block}

### Documentazione indicizzata
{context}

### Richiesta dell'utente
{query}
"""

    def _repair_story_count_if_needed(
        self,
        *,
        plan: ProjectPlan,
        query: str,
        context: str,
        history_text: str,
        jira_project_key: Optional[str],
        exact_story_count: bool,
        target_story_count: int,
        metadata_brief: Optional[str],
    ) -> ProjectPlan:
        current_count = len(plan.user_stories)
        if not exact_story_count or current_count == target_story_count:
            return plan

        if current_count > target_story_count:
            logger.warning(
                "Planner returned %d stories, trimming to requested %d.",
                current_count,
                target_story_count,
            )
            plan.user_stories = plan.user_stories[:target_story_count]
            return plan

        logger.warning(
            "Planner returned %d grounded stories instead of requested %d. Keeping factual result.",
            current_count,
            target_story_count,
        )
        gap_note = (
            f"Il documento non contiene evidenze sufficienti per produrre esattamente "
            f"{target_story_count} user story senza introdurre assunzioni."
        )
        existing_questions = {item.strip().lower() for item in plan.open_questions}
        if gap_note.lower() not in existing_questions:
            plan.open_questions = list(plan.open_questions) + [gap_note]
        return plan

    def _build_story_count_retry_prompt(
        self,
        *,
        query: str,
        context: str,
        history: str,
        jira_project_key: Optional[str],
        target_story_count: int,
        current_plan: Dict[str, Any],
        metadata_brief: Optional[str],
    ) -> str:
        retry_plan_json = json.dumps(current_plan, ensure_ascii=False, indent=2)
        retry_note = (
            f"La risposta precedente conteneva {len(current_plan.get('user_stories', []) or [])} "
            f"user story, ma ne servono esattamente {target_story_count}."
        )
        base_prompt = self._build_prompt(
            query=query,
            context=context,
            history=history,
            jira_project_key=jira_project_key,
            max_stories=target_story_count,
            exact_story_count=True,
            metadata_brief=metadata_brief,
        )
        return f"""{base_prompt}

Correzione obbligatoria:
- {retry_note}
- Rigenera l'intero JSON.
- Mantieni summary, rischi e domande aperte coerenti con il contesto.
- Le user story devono essere distinte tra loro e non duplicate.

JSON precedente da correggere:
{retry_plan_json}
"""

    def _parse_payload(self, raw_result: str) -> Dict[str, Any]:
        candidate = raw_result.strip()
        if not candidate:
            return {}

        # Strip markdown code blocks if present (common LLM wrapper)
        if candidate.startswith("```"):
            lines = candidate.split("\n")
            # Remove first line if it's just ```json or ```
            if lines[0].strip() in ("```", "```json", "```JSON"):
                lines = lines[1:]
            # Remove last line if it's just ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON object between first { and last }
            start = candidate.find("{")
            end = candidate.rfind("}")
            if 0 <= start < end:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    logger.debug("Planner JSON parsing failed even after extraction")
        return {}

    def _fallback_plan(self, query: str) -> ProjectPlan:
        summary = (
            "Non riesco a estrarre requisiti affidabili dal contenuto ricevuto. "
            "Richiesta originale: "
            f"{query}"
        )
        return ProjectPlan(functional_summary=summary)
