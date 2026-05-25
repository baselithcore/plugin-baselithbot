"""HTTP routers grouped by surface area.

Currently:

- :mod:`llm_wiki.api.admin` — gated scaffold + tenant management endpoints.

Core RAG/ingest routes still live in ``main.py`` for now. They will be
moved here in phase 2 along with the per-request tenant resolution.
"""
