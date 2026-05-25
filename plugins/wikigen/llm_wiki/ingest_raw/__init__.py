"""Ingest pipeline: ``raw/`` PDFs → wiki ``.md`` pages.

Stack:

- ``extractor``: PDF → Markdown (Docling preferred, fallback pymupdf+pdfplumber).
- ``schemas``: pydantic models + pack-aware JSON schema builders.
- ``linter``: deterministic page validator (hard gate before write).
- ``prompts``: thin façade over the active pack's Jinja2 templates.
- ``examples``: few-shot retrieval from existing wiki + pack examples.
- ``planner``: classify + propose page list (constrained decoding).
- ``generator``: dispatches to a :class:`PageTypeStrategy` per page.
- ``critic``: refiner loop driven by the linter.
- ``orchestrator``: extract → plan → generate → lint → refine → write.

Design goals:

- **Never write into ``raw/``** — guarded in the orchestrator.
- **Idempotency**: rerun produces the same output modulo timestamps.
- **LLM swap-safe**: reads ``LLM_VENDOR`` + per-vendor model env vars.
- **Domain-pluggable**: page generation logic lives in the active pack's
  strategies module, not in this package.
"""

from __future__ import annotations

from llm_wiki.ingest_raw.orchestrator import IngestResult, ingest_raw_file

__all__ = ["IngestResult", "ingest_raw_file"]
