"""Prompt templates for blueprint synthesis and scoped code generation.

Kept pure (no I/O) so prompts are unit-testable in isolation and the runtime
remains a thin orchestration layer over deterministic string construction.
"""

from __future__ import annotations

__all__ = [
    "BLUEPRINT_SYSTEM_PROMPT",
    "get_blueprint_prompt",
    "SCOPED_CODING_SYSTEM_PROMPT",
    "get_scoped_generate_prompt",
]


# ---------------------------------------------------------------------------
# Blueprint synthesis — natural language -> structured specification
# ---------------------------------------------------------------------------

BLUEPRINT_SYSTEM_PROMPT = """You are the BaselithCore Agent Architect.

Given a natural-language description of a desired agent, you emit a STRICT JSON
object describing how to construct it. You never invent capabilities outside the
allowed vocabulary and you keep the agent narrowly scoped to its stated purpose.

Allowed capabilities: generate, fix, test, refactor, explain, operate.
  - generate/fix/test/refactor/explain are CODE-authoring actions.
  - operate is a LIVE action: the agent runs a ReAct tool loop to DO a task
    (fetch data, send messages). Choose operate for "monitor/notify/send/check"
    style requests, and populate scope.allowed_tools.
Available runtime tools (for operate): http_get, send_telegram, now.
Allowed providers: anthropic, openai, ollama.

Respond with JSON only — no markdown fences, no commentary."""


def get_blueprint_prompt(description: str, default_provider: str) -> str:
    """Build the user prompt that turns a request into a blueprint JSON.

    Args:
        description: The user's natural-language agent description.
        default_provider: Provider to assume when the request is silent on it.

    Returns:
        A fully rendered prompt instructing the model to emit blueprint JSON.
    """
    return f"""Design an agent for this request:

\"\"\"{description}\"\"\"

Emit a JSON object with exactly these keys:
{{
  "name": "<short human name>",
  "description": "<one sentence>",
  "system_directive": "<persona/system prompt for the agent, <= 1500 chars>",
  "provider": "<anthropic|openai|ollama, default {default_provider}>",
  "model": "<explicit model id or null>",
  "tags": ["<keyword>", ...],
  "scope": {{
    "capabilities": ["<subset of generate|fix|test|refactor|explain|operate>"],
    "doc_namespaces": ["<doc path prefixes the agent should rely on, or []>"],
    "allowed_tools": ["<subset of http_get|send_telegram|now, only for operate>"],
    "max_iterations": <int 1-10>,
    "language": "<primary language, lowercase>",
    "allow_execution": <true|false>
  }}
}}

Pick the SMALLEST capability set that satisfies the request. Use operate (with
the needed allowed_tools) for live monitor/notify/send/fetch tasks. Prefer
grounding the agent in framework documentation via doc_namespaces when the task
touches BaselithCore internals. Output JSON only."""


# ---------------------------------------------------------------------------
# Scoped code generation — grounded in framework documentation
# ---------------------------------------------------------------------------

SCOPED_CODING_SYSTEM_PROMPT = """You are a BaselithCore-native coding agent.

You write production-grade, asynchronous Python that conforms to the framework's
conventions: PEP 604 unions, full type hints, Pydantic models for config,
async/await for all I/O, Google-style docstrings, and a hard 500-LOC per-file
ceiling. You stay strictly within the scope and documentation context you are
given and never introduce dependencies or behaviours outside that scope.

Respond with valid code only — no markdown fences, no prose."""


def get_scoped_generate_prompt(
    directive: str,
    task: str,
    language: str,
    doc_context: str,
) -> str:
    """Compose a generation prompt grounded in retrieved documentation.

    Args:
        directive: The blueprint's persona/system directive.
        task: The concrete code task to perform.
        language: Target programming language.
        doc_context: Documentation excerpts the agent must respect.

    Returns:
        A rendered prompt binding the task to its documentation context.
    """
    grounding = doc_context.strip() or "(no framework documentation retrieved)"
    return f"""Agent directive:
{directive or "(none)"}

Framework documentation context (authoritative — do not contradict):
---
{grounding}
---

Task: write {language} code for the following, staying within the documented
conventions above and within the agent's declared scope:

{task}

Provide only the code."""
