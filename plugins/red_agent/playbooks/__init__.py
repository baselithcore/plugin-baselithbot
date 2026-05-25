"""Versioned playbook library.

Playbooks are YAML files describing a curated combination of scanners,
target categories, intensity, and references (OWASP WSTG / LLM Top 10
/ MITRE ATT&CK). The library lets operators launch a coherent attack
chain without hand-picking scanners every time.
"""

from ._loader import (
    Playbook,
    PlaybookCatalogue,
    PlaybookNotFoundError,
    default_catalogue,
    load_playbook_files,
)

__all__ = [
    "Playbook",
    "PlaybookCatalogue",
    "PlaybookNotFoundError",
    "default_catalogue",
    "load_playbook_files",
]
