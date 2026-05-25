from __future__ import annotations

import json
import logging
from typing import Any, Dict

from agent_jira.agents.graph.relationship_detector import RelationshipDetector
from agent_jira.llm import generate_response
from agent_jira.config import OLLAMA_MODEL

from .extractors import ProjectContextExtractor
from .models import ProjectContext

logger = logging.getLogger(__name__)


class MetadataAgent:
    """Agent that orchestrates metadata extraction using LLM."""

    MIN_LLM_TEXT_LENGTH = 250
    MIN_LLM_TEXT_LENGTH_LOW_SIGNAL = 120
    MIN_RELATIONSHIP_TEXT_LENGTH = 300
    MAX_PROMPT_CHARS = 8000

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.fast_extractor = ProjectContextExtractor()
        self.model = OLLAMA_MODEL

    def analyze_document(
        self, text: str, doc_id: str = "", enrich: bool = True
    ) -> ProjectContext:
        """
        Analyze document text to extract structured project metadata.
        Uses a two-step approach:
        1. Fast Path (Regex)
        2. Slow Path (LLM) - Merges into context (optional)
        """
        context = self.extract_metadata(text)

        if enrich and self._should_run_llm(text, context):
            context = self.enrich_metadata(text, context, doc_id=doc_id)

        return context

    def extract_metadata(self, text: str) -> ProjectContext:
        """Perform fast, regex-based metadata extraction."""
        return self.fast_extractor.extract_from_text(text)

    def enrich_metadata(
        self, text: str, context: ProjectContext, doc_id: str = ""
    ) -> ProjectContext:
        """Perform slow, LLM-based metadata enrichment on an existing context."""
        prompt = f"""
        SYSTEM
        Sei un esperto di analisi documentale rigorosa. Il tuo obiettivo è l'estrazione di metadati puramente basata sull'evidenza.

        REGOLE DI GROUNDING (ASSOLUTE):
        1. NO CREATIVITÀ: Non inventare mai campi, entità, stakeholder, integrazioni o rischi. Se non sono nel testo, non esistono.
        2. NO INFERENZE DEBOLI: Non dedurre ruoli o tecnologie basandoti sulla tua conoscenza generale se non sono esplicitamente menzionati o direttamente logici.
        3. FONTE UNICA: Il documento fornito è l'unica fonte di verità ammessa.
        4. PRECISIONE: Se un'informazione è ambigua o dubbia, ignorala. È meglio un metadato in meno che uno errato.
        5. LINGUA: Tutti i contenuti estratti devono essere in ITALIANO, mantenendo i termini tecnici originali se appropriato.

        TASK
        Analizza il documento ed estrai metadati strutturati per alimentare un sistema di GraphRAG.
        Restituisci SOLO JSON valido.

        Testo del Documento:
        {text[: self.MAX_PROMPT_CHARS]}
        """
        prompt += """
        Estrai i seguenti campi (in italiano):
        - goals: Lista di obiettivi del progetto (stringhe in italiano)
        - stakeholders: Lista di oggetti {name, role, email}
        - modules: Lista di moduli, processi o funzionalità principali
        - integrations: Lista di sistemi esterni, API o piattaforme integrate
        - constraints: Lista di vincoli espliciti (normativi, tecnici, temporali, SLA, compliance)
        - business_rules: Lista di regole business o decisioni operative deducibili dal documento
        - assumptions: Lista di assunzioni o dipendenze implicite/esplicite
        - open_questions: Lista di punti ambigui, mancanti o da chiarire con il business
        - timeline: Lista di milestone. Ogni milestone DEVE avere:
            - name: Titolo breve in italiano (es. "Rilascio Fase 1")
            - date: Data ISO o descrizione testuale (es. "2024-01-01", "Q3 2024")
            - type: Uno tra ["Release", "Deadline", "Meeting", "Decision", "Start", "End", "Generic"]
            - status: Uno tra ["Planned", "Completed", "Delayed", "AtRisk"] (dedurre dal contesto, default "Planned")
            - description: Breve descrizione in italiano di cosa accade
        - technologies: Lista di tecnologie (stringhe)
        - risks: Lista di rischi potenziali (stringhe in italiano)
        - domain: dominio business principale del documento, se inferibile

        Vincoli di estrazione:
        - Non dedurre stakeholder, sistemi o moduli solo perché sono comuni nel dominio.
        - Non trasformare ipotesi deboli in regole business.
        - Non estrarre open_questions se il testo è chiaro; usale solo per dubbi reali presenti o impliciti nel documento.
        - Se il documento non contiene abbastanza informazioni per un campo, restituisci il campo vuoto.

        Struttura JSON:
        {
            "goals": ["obiettivo 1 in italiano", "obiettivo 2 in italiano"],
            "stakeholders": [{"name": "...", "role": "...", "email": "..."}],
            "modules": ["Gestione anagrafica", "Workflow approvativo"],
            "integrations": ["Core banking", "API antifrode"],
            "constraints": ["Tempo massimo di risposta 2 secondi"],
            "business_rules": ["La richiesta è approvabile solo se ..."],
            "assumptions": ["Il dato anagrafico è già presente sul sistema master"],
            "open_questions": ["Va gestita la retrocompatibilità con il canale X?"],
            "timeline": [
                {"name": "Nome milestone in italiano", "date": "...", "type": "...", "status": "...", "description": "Descrizione in italiano"}
            ],
            "technologies": ["React", "PostgreSQL"],
            "risks": ["rischio 1 in italiano", "rischio 2 in italiano"],
            "domain": "finance"
        }
        """

        try:
            if self.use_llm:
                response = generate_response(prompt, json=True)
                data = json.loads(self._sanitize_json_response(response))
                self._enrich_context(context, data)
                logger.info(f"MetadataAgent: Enriched {doc_id} with LLM data.")

                # Semantic Relationships
                if len(text.strip()) >= self.MIN_RELATIONSHIP_TEXT_LENGTH:
                    detector = RelationshipDetector()
                    edges = detector.detect_semantic_relationships(text)
                    context.semantic_relationships = [
                        {
                            "source": e.source,
                            "target": e.target,
                            "relationship": e.relationship,
                            "confidence": e.confidence,
                            "evidence": e.evidence,
                        }
                        for e in edges
                    ]

        except Exception as e:
            logger.warning(
                f"MetadataAgent: LLM extraction failed for {doc_id}, falling back to Regex only: {e}"
            )

        return context

    def _enrich_context(self, context: ProjectContext, data: Dict[str, Any]):
        """Merge LLM data into existing context (from regex)."""
        # Merge simple lists
        self._merge_list(context.goals, data.get("goals", []))
        self._merge_list(context.risks, data.get("risks", []))
        self._merge_list(context.technologies, data.get("technologies", []))
        self._merge_list(context.modules, data.get("modules", []))
        self._merge_list(context.integrations, data.get("integrations", []))
        self._merge_list(context.constraints, data.get("constraints", []))
        self._merge_list(context.business_rules, data.get("business_rules", []))
        self._merge_list(context.assumptions, data.get("assumptions", []))
        self._merge_list(context.open_questions, data.get("open_questions", []))
        if not context.domain and isinstance(data.get("domain"), str):
            context.domain = data["domain"].strip() or context.domain

        # Merge Stakeholders
        regex_names = {s["name"].lower() for s in context.stakeholders}
        for s in data.get("stakeholders", []):
            if isinstance(s, dict) and "name" in s:
                if s["name"].lower() not in regex_names:
                    context.stakeholders.append(s)

        # Merge Timeline
        existing_generic_by_date = {}
        existing_names = set()

        for idx, m in enumerate(context.timeline):
            existing_names.add(m.get("name", "").lower())
            if m.get("type") == "Generic" and m.get("date"):
                existing_generic_by_date[m["date"]] = idx

        for m in data.get("timeline", []):
            if not isinstance(m, dict) or "name" not in m:
                continue

            llm_name = m["name"].lower()
            llm_date = m.get("date")

            if llm_name in existing_names:
                continue

            if llm_date and llm_date in existing_generic_by_date:
                idx_to_replace = existing_generic_by_date[llm_date]
                context.timeline[idx_to_replace] = m
                existing_names.add(llm_name)
                del existing_generic_by_date[llm_date]
                continue

            context.timeline.append(m)
            existing_names.add(llm_name)

    def _should_run_llm(self, text: str, context: ProjectContext) -> bool:
        if not self.use_llm:
            return False
        text_length = len(text.strip())
        if text_length >= self.MIN_LLM_TEXT_LENGTH:
            return True
        return (
            text_length >= self.MIN_LLM_TEXT_LENGTH_LOW_SIGNAL
            and context.signal_count() <= 1
        )

    def _sanitize_json_response(self, response: str) -> str:
        """Extract JSON from potential markdown code blocks."""
        response = response.strip()
        if "```json" in response:
            params = response.split("```json")
            if len(params) > 1:
                return params[1].split("```")[0].strip()
        if "```" in response:
            params = response.split("```")
            if len(params) > 1:
                return params[1].split("```")[0].strip()
        return response

    def _merge_list(self, target_list: list, source_list: list):
        """Merge source into target avoiding partial duplicates."""
        existing = {str(item).lower() for item in target_list}
        for item in source_list:
            if isinstance(item, str) and item.lower() not in existing:
                target_list.append(item)
                existing.add(item.lower())
