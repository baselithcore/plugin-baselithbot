# Document Compliance Checker — Blueprint Tecnico Enterprise

**Stato:** Draft v0.1 · 2026-05-03
**Owner:** g.ippolito@gdservices.tech
**Target MVP:** workstation singola Electron + backend Python su NVIDIA DGX Spark dedicato. Path multi-tenant post-MVP.

---

## Pillar di Prodotto

1. **Glass Box Architecture** — ogni verdetto cita riga/sezione documento + policy esatta violata. Reasoning agent tracciato end-to-end.
2. **Zero Cloud Leak** — local-first, no API esterne, modelli e vector DB on-prem.
3. **Multi-Agent Verifiable** — pipeline LangGraph con agenti specializzati (Parser, Structurer, Legal, Technical, PII, Synthesizer) e validazione Pydantic obbligatoria.

## Stack Vincolato

- **Backend:** Python 3.12, FastAPI, LangGraph, LlamaIndex.
- **LLM Serving:** vLLM su NVIDIA DGX Spark, modello primario `Llama-3.3-70B-Instruct Q4_K_M`, fallback `Llama-3.1-8B`.
- **Embedding:** BGE-M3 multilingue (IT + EN nativi).
- **Vector DB:** ChromaDB (MVP) → Qdrant (multi-tenant post-MVP).
- **Persistenza:** SQLCipher (SQLite cifrato) per audit + core. Master key in OS keychain.
- **OCR:** PaddleOCR layout-aware.
- **Frontend:** Electron + Next.js statico + React + TanStack Query + Zustand + Tailwind + shadcn/ui.
- **Comunicazione FE↔BE:** gRPC su Unix socket + WebSocket per streaming reasoning.

## Personas

- **Compliance Officer / Legal Counsel** — gestisce policy, valida documenti sensibili.
- **Data Protection Officer (DPO)** — verifica zero leak, audit trail integrità.
- **Enterprise User** — uploads contratti/offerte per validazione veloce.

## File del Blueprint

| File | Contenuto |
|------|-----------|
| `00_overview.md` | Questo documento. |
| `01_core_architecture.md` | Architettura layered, componenti produzione (RBAC, audit, cache, packaging). |
| `02_agentic_flow.md` | LangGraph state machine, schema agenti, multilingua, glass box. |
| `03_ui_ux.md` | Layout 60/40, interazioni, tipografia, accessibilità. |
| `04_data_flow.md` | Event flow, schema JSON Finding/Report, caching keys. |
| `05_implementation_plan.md` | 4 fasi, 14 settimane, KPI, rischi. |
| `06_db_schema.sql` | Schema SQLCipher completo (core + audit hash-chained). |
| `07_prompt_templates.md` | Prompt per ogni agente con guardrails. |
| `08_design_tokens.yaml` | Token design system mappati shadcn/ui. |
| `09_wireframes.md` | Spec frame Figma-ready, componenti, stati interattivi. |

## KPI MVP

- Precision findings ≥ 85% (test set 50 contratti annotati IT).
- Tempo analisi doc 20 pagine < 90s su DGX Spark.
- Zero pacchetti rete uscenti durante analisi (validazione tcpdump in CI).
- 100% findings con `evidence.bbox` + `policy_ref.excerpt` non-null.
