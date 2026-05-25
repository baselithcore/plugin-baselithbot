import logging
import re
from typing import Dict, List, Optional

from agent_jira.llm import generate_response
from agent_jira.config import OLLAMA_MODEL

logger = logging.getLogger(__name__)


def detect_project_context(
    query: str,
    available_projects: List[Dict[str, str]],
    history: str = "",
) -> Optional[str]:
    """
    Tenta di identificare il progetto Jira dal contesto della conversazione.
    Usa Regex per pattern comuni e fallback su LLM.
    Il risultato viene validato contro i progetti reali su Jira.
    """

    def _resolve_to_valid_key(candidate: str) -> Optional[str]:
        """Cerca il candidate tra key e name dei progetti reali."""
        if not candidate or not available_projects:
            return candidate or None
        norm = candidate.strip().upper()
        # Corrispondenza esatta sulla chiave
        for p in available_projects:
            if p["key"].upper() == norm:
                return p["key"]
        # Corrispondenza parziale sul nome
        norm_lower = candidate.strip().lower()
        for p in available_projects:
            if norm_lower in p["name"].lower() or p["name"].lower() in norm_lower:
                logger.info(
                    "Project key resolved via name match: '%s' -> '%s'",
                    candidate,
                    p["key"],
                )
                return p["key"]
        # Non trovato nei progetti reali → chiave non valida
        logger.warning(
            "Project key '%s' not found in available Jira projects: %s",
            candidate,
            [p["key"] for p in available_projects],
        )
        return None

    # 0. Regex: pattern espliciti come "progetto ABC" / "project ABC"
    regex_pattern = (
        r"(?:progetto|project|key)[\s:]+([A-Z]+[A-Z0-9]*-\d+|[A-Z]+[A-Z0-9]*)"
    )
    match = re.search(regex_pattern, query, re.IGNORECASE)
    if match:
        candidate = match.group(1).upper()
        resolved = _resolve_to_valid_key(candidate)
        if resolved:
            logger.info("Project context detected via Regex: %s", resolved)
            return resolved

    # 1. Fallback LLM
    prompt = f"""
Sei un assistente che estrae metadati. Analizza la richiesta dell'utente e la cronologia.
Identifica se l'utente ha specificato esplicitamente un nome o una chiave di progetto Jira.

Richiesta: {query}
Cronologia recente: {history[-500:] if history else "Nessuna"}

Rispondi SOLO con il nome/chiave del progetto se presente, altrimenti rispondi "NULL".
Non aggiungere altro testo.
"""
    try:
        result = generate_response(prompt, model=OLLAMA_MODEL)
        cleaned = result.strip().replace('"', "").replace("'", "")
        if cleaned.upper() == "NULL" or not cleaned:
            return None
        return _resolve_to_valid_key(cleaned)
    except Exception:
        logger.warning("Project detection failed", exc_info=True)
        return None
