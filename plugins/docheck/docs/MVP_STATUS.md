# doCheck MVP — Status & Handoff

**Versione blueprint:** 0.1.0
**Data finalizzazione scaffold:** 2026-05-03
**Owner:** <g.ippolito@gdservices.tech>

---

## Cosa è pronto

### Backend Engine (Python)

- ✅ FastAPI + Uvicorn (Unix socket / TCP loopback)
- ✅ Auth: argon2id login → **JWT EdDSA** (Ed25519, jose) [`core/jwt.py`](../docheck-engine/src/docheck/core/jwt.py)
- ✅ RBAC: roles + permissions + `require(resource, action)` dependency
- ✅ Audit log Ed25519 hash-chained, immutable triggers SQLite/Postgres, **per-tenant chain**
- ✅ LangGraph multi-agent: Structurer · Legal · Technical · PII · Synthesizer
- ✅ Glass Box: `evidence.bbox` + `policy_ref.excerpt` validation Pydantic
- ✅ Vector store abstraction: ChromaDB (MVP) ↔ Qdrant (multi-tenant) con tenant scoping
- ✅ Document parsers: PDF (pdfplumber + PaddleOCR fallback), DOCX, XLSX, MD/TXT
- ✅ Report signing Ed25519 + verify CLI-friendly
- ✅ WebSocket streaming pipeline events
- ✅ OpenTelemetry locale (file exporter, no cloud)
- ✅ OIDC stub pronto attivazione (issuer config-flag)
- ✅ Postgres RLS migration + session GUC binding
- ✅ Multi-tenant: `TenantMixin` colonna `tenant_id`, ContextVar propagation, middleware

### Frontend UI (Next.js + Electron)

- ✅ Layout 60/40 split-pane resizable
- ✅ Document Viewer con highlight bbox + scroll-to-finding
- ✅ FindingsPanel virtualizzata (`react-virtuoso`)
- ✅ Reasoning Drawer (Glass Box) con timeline agent steps
- ✅ Policy Manager modal (default IT preselect, EU, World, Custom)
- ✅ PolicyManager + Policies dedicated page master/detail
- ✅ Audit Log viewer + chain integrity verify
- ✅ Settings (Account, Engine, Security, Storage)
- ✅ Login + AuthGuard + Sidebar nav
- ✅ Tenant header `X-Tenant-Id` propagato + Bearer JWT
- ✅ ScoreGauge, SeverityBadge, PhaseIndicator components
- ✅ Phase streaming progress bar
- ✅ Electron shell con preload sandboxed

### Infra & Deploy

- ✅ Docker Compose single-tenant (engine + vLLM)
- ✅ Docker Compose multi-tenant (engine + Postgres + Qdrant)
- ✅ Helm chart skeleton (engine StatefulSet + ConfigMap + NetworkPolicy)
- ✅ Alembic migrations: 0001 schema, 0002 tenant_id, 0003 Postgres RLS
- ✅ CI: lint + type-check + tests + **egress lockdown gate** (tcpdump + iptables)
- ✅ Mock LLM server per dev offline

### Tests

| File | Cosa copre |
|------|-----------|
| `test_audit_chain.py` | Hash chain integrity |
| `test_audit_tenant_isolation.py` | Per-tenant chain independence |
| `test_signing.py` | Ed25519 sign/verify + tampering |
| `test_jwt.py` | JWT issue/verify/expiry/tamper |
| `test_rbac.py` | Permission allow/deny |
| `test_pipeline.py` | Agent E2E con mock LLM |
| `test_parser_text.py` | Text/MD parser |
| `test_tenant_context.py` | ContextVar propagation, isolation |
| `test_vectorstore_isolation.py` | Cross-tenant collection isolation |
| `test_oidc_stub.py` | OIDC config gating |
| `test_auth_login.py` | Login flow integration |
| `test_full_flow.py` | E2E: login → upload → analyze → audit verify |

### Docs

- 10 file blueprint enterprise (`blueprint/`)
- 6 ADR (`docs/adr/0001..0006`)
- Module docs: `agents.md`, `audit.md`, `events.md`, `tenant.md`, `api.md`
- API reference: `docs/api/endpoints.md`
- Runbooks: `setup-dev.md`, `kpi-evaluation.md`
- Helm README `docker/helm/docheck/README.md`

---

## Cosa serve completare prima GA

### F2 late (agentic refinement)

- [ ] StructurerAgent: prompt tuning IT contracts
- [ ] Parallel branch fan-out legal/technical/pii in LangGraph
- [ ] Verdict cache hit-ratio metrics

### F3 finishing

- [ ] pdf.js viewer reale (oggi placeholder rendering chunks)
- [ ] Drag&drop multi-file
- [ ] Export PDF report con highlight rendering

### F4 hardening

- [ ] OIDC end-to-end con Keycloak
- [ ] Pen-test interno (egress, CSP Electron, audit tampering)
- [ ] Master key custody → OS keychain (oggi file 0600)
- [ ] CSP rules Electron production-grade

### F5+ multi-tenant

- [ ] Test integration RLS Postgres real
- [ ] Tenant onboarding flow (admin + setup wizard)
- [ ] Quota / rate limiting per tenant
- [ ] Helm chart: ServiceMonitor Prometheus, ingress TLS
- [ ] Backfill migration script clienti legacy

### Quality gate MVP

- [ ] Test set 50 contratti IT annotati
- [ ] KPI gate: precision ≥0.85, recall ≥0.80, F1 baseline
- [ ] Soak test 100 doc concorrenti su DGX Spark
- [ ] Accessibility audit WCAG AA (axe-core CI)

---

## Quick start handoff team

```bash
# Engine
cd docheck-engine
uv sync --extra dev
uv run alembic upgrade head
uv run python ../scripts/seed_policies.py
uv run python -m docheck.main

# UI (altro terminale)
cd ../docheck-ui
pnpm install
pnpm dev

# Mock LLM (terzo terminale, dev offline)
cd ..
uv run --project docheck-engine python scripts/mock_llm.py
```

Login: crea admin via `uv run python scripts/seed_admin.py`.

---

## File count finale

```
~70 file sorgente (engine + UI + helm + scripts)
10 blueprint markdown
6 ADR
12 test files
3 alembic migrations
```

Tutti i file rispettano il limite **500 LOC** (vedi [CLAUDE.md](../CLAUDE.md)).

---

## Stack reference

- **Backend:** Python 3.12, FastAPI, LangGraph, SQLAlchemy 2 async, PyNaCl, python-jose, structlog, OTel
- **LLM:** vLLM (Llama-3.3-70B Q4_K_M su DGX Spark) | Mock dev | Ollama dev
- **Embedding:** BGE-M3 multilingue
- **Vector:** ChromaDB | Qdrant
- **DB:** SQLCipher (SQLite) | Postgres + RLS
- **OCR:** PaddleOCR + Tesseract fallback
- **Frontend:** Next.js 15, React 19, Tailwind, shadcn/ui, TanStack Query, Zustand
- **Desktop:** Electron 33
- **Deploy:** Docker Compose | Helm chart Kubernetes

Pronto handoff team dev MVP.
