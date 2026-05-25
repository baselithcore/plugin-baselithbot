# app/vectorstore/chunking.py
"""Text chunking and chunk preparation utilities."""

from __future__ import annotations

import uuid
from typing import Any, Dict

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - compatibilità con installazioni legacy
    from langchain.text_splitter import RecursiveCharacterTextSplitter

# Constants
NEWLINE = chr(10)
DOUBLE_NEWLINE = NEWLINE * 2

# Text splitter configuration
splitter = RecursiveCharacterTextSplitter(
    chunk_size=350,
    chunk_overlap=70,
    separators=[DOUBLE_NEWLINE, NEWLINE, "\\n##", "\\n#", "\\n\\n", "\\n", ". ", " "],
)


def _chunk_point_id(document_id: str, chunk_index: int) -> str:
    """Genera un UUID deterministico per ogni chunk."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def _prepare_chunk_text(chunk: str, metadata: Dict[str, Any]) -> str:
    """Arricchisce lo spezzone con metadati utili al recupero."""
    header_lines = []
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        header_lines.append(title.strip())
    url = metadata.get("url") or metadata.get("source")
    if isinstance(url, str) and url.startswith("http"):
        header_lines.append(f"Fonte: {url.strip()}")
    origin = metadata.get("origin")
    if isinstance(origin, str) and origin.strip().lower() == "filesystem":
        relative_path = metadata.get("relative_path") or metadata.get("source")
        if isinstance(relative_path, str) and relative_path.strip():
            header_lines.append(f"File: {relative_path.strip()}")
        category = metadata.get("category")
        if isinstance(category, str) and category.strip():
            header_lines.append(f"Cartella: {category.strip()}")
        doc_type = metadata.get("doc_type")
        if isinstance(doc_type, str) and doc_type.strip():
            header_lines.append(f"Tipo: {doc_type.strip()}")
    domain = metadata.get("domain")
    if isinstance(domain, str) and domain.strip():
        header_lines.append(f"Dominio: {domain.strip()}")
    doc_goals = metadata.get("doc_goals")
    if isinstance(doc_goals, str) and doc_goals.strip():
        header_lines.append(f"Obiettivi: {doc_goals.strip()}")
    doc_modules = metadata.get("doc_modules")
    if isinstance(doc_modules, str) and doc_modules.strip():
        header_lines.append(f"Moduli: {doc_modules.strip()}")
    doc_integrations = metadata.get("doc_integrations")
    if isinstance(doc_integrations, str) and doc_integrations.strip():
        header_lines.append(f"Integrazioni: {doc_integrations.strip()}")
    doc_constraints = metadata.get("doc_constraints")
    if isinstance(doc_constraints, str) and doc_constraints.strip():
        header_lines.append(f"Vincoli: {doc_constraints.strip()}")
    doc_business_rules = metadata.get("doc_business_rules")
    if isinstance(doc_business_rules, str) and doc_business_rules.strip():
        header_lines.append(f"Regole business: {doc_business_rules.strip()}")

    header = NEWLINE.join(header_lines).strip()
    body = chunk.strip()
    return DOUBLE_NEWLINE.join(part for part in [header, body] if part)
