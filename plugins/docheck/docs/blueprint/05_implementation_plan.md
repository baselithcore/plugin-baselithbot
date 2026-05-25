# 5. Piano Implementazione MVP

**Durata totale:** ~14 settimane (3.5 mesi)
**Team consigliato:** 1 tech lead, 2 backend Python, 1 frontend React, 1 designer (part-time), 1 QA/DevOps.

## 5.1 Roadmap 4 Fasi

### F1 — Foundation (settimane 1-3)

**Deliverable:**
- Monorepo setup (`docheck-engine`, `docheck-ui`, `docheck-shared-schemas`).
- FastAPI scaffold con health, auth stub, gRPC Unix socket.
- Electron shell + Next.js statico embedded.
- Ingestion pipeline: PDF (pdfplumber), DOCX (python-docx), XLSX (openpyxl), MD.
- PaddleOCR integration per PDF scansionati.
- ChromaDB + BGE-M3 embedding pipeline.
- Schema SQLite + migrazioni (Alembic).
- Seed policy default (IT GDPR, Codice Civile, Codice Consumo).

**Criteri accettazione:**
- Doc upload via UI → chunks visibili con bbox sovrapposte in viewer.
- Indicizzazione policy seed verificata (3 policy IT, ~50 rule attive).
- Test E2E "upload + parse + index" su 5 doc campione.

### F2 — Agentic Core (settimane 4-7)

**Deliverable:**
- LangGraph state machine con 6 agenti.
- vLLM serving Llama-3.3-70B Q4_K_M su DGX Spark, fallback Llama-3.1-8B.
- Schema Finding validato Pydantic.
- RAG IT/EN funzionante.
- Tools agente (`retrieve_policy`, `check_clause_presence`, `extract_obligation`).
- Verdict cache + embedding cache.

**Criteri accettazione:**
- E2E: contratto test → ≥10 findings tracciabili.
- Score deterministico (stesso input → stesso output, temperature 0.1).
- Tempo analisi 20pp < 90s su DGX Spark.
- 100% findings con evidence + policy_ref non-null.

### F3 — UI Glass Box (settimane 8-11)

**Deliverable:**
- Layout 60/40 con `react-resizable-panels`.
- Document Viewer con highlight bbox via SVG overlay su pdf.js.
- Findings Panel virtualizzata (`react-virtuoso`).
- Reasoning Drawer con timeline agent steps.
- Policy Manager modal (default + custom + import).
- WebSocket streaming findings progressivo.
- Skeleton states + empty states + error states.
- Dark mode default + tokens design system.
- Export report (PDF + MD + JSON firmato).

**Criteri accettazione:**
- Click finding → highlight evidence < 300ms.
- Usability test interno (5 utenti, task completion ≥ 80%).
- WCAG AA verificato (axe-core CI).
- Streaming UX fluida (no jank, 60fps).

### F4 — Hardening & Packaging (settimane 12-14)

**Deliverable:**
- RBAC completo (4 ruoli) + permission enforcement.
- SQLCipher audit trail con hash chain Ed25519.
- Job verifica integrità chain.
- Report signing Ed25519 + verifica CLI.
- Docker Compose production per server DGX.
- Electron installer firmato (notarized macOS, signed Windows, AppImage Linux).
- Pen-test interno (egress lockdown validato con tcpdump).
- Documentazione utente + admin guide.
- CI/CD: lint, type-check, unit, integration, E2E, security scan.

**Criteri accettazione:**
- Pen-test interno superato.
- Audit log immutabile (trigger SQLite verificato).
- Zero pacchetti rete uscenti durante analisi (validazione tcpdump in CI).
- Installer testati su macOS Sonoma+, Windows 11, Ubuntu 22.04.
- Docker Compose deploy DGX Spark verificato.

## 5.2 Rischi & Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Latenza Llama-3.3-70B Q4_K_M troppo alta su DGX Spark | Media | Alto | Router agent: 8B per check rapidi, 70B solo per legal reasoning. Batching findings parallelo. |
| Falsi positivi PII multilingua | Alta | Medio | Ensemble regex + NER + LLM verifier, confidence threshold tunable, learning loop manuale |
| Drift policy versioning (rule cambia, cache stale) | Media | Alto | Semver obbligatorio policy, snapshot policy embedded in report per riproducibilità |
| OCR PaddleOCR fail su PDF qualità bassa | Media | Medio | Fallback Tesseract + pre-processing (deskew, denoise), warning UI se confidence OCR < 0.7 |
| Performance Chroma su corpus grande (>100k chunk) | Bassa | Medio | Path migrazione Qdrant pronta, benchmark precoce in F2 |
| Glass Box reasoning chain troppo verbosa | Media | Basso | Cap step LLM, summarization opzionale, lazy loading drawer |

## 5.3 KPI MVP

- **Precision findings ≥ 85%** su test set 50 contratti annotati IT.
- **Recall findings ≥ 80%** stesso test set.
- **Tempo analisi doc 20pp < 90s** P95.
- **Cache hit ratio ≥ 60%** dopo warmup.
- **Zero pacchetti rete uscenti** durante analisi (CI gate).
- **100% findings tracciabili** (evidence + policy_ref + reasoning).
- **Audit chain integrity** verificata daily, alert su mismatch.

## 5.4 Test Set Annotato

- 50 contratti IT (forniture, NDA, lavoro, fornitura servizi cloud, GDPR DPA).
- 20 contratti EN (NDA, MSA, SaaS).
- 10 documenti policy aziendali interne (regolamenti, code of conduct).
- Annotazione manuale ground truth da Compliance Officer (≥2 reviewer per accordo Cohen κ).

## 5.5 Path Multi-Tenant Post-MVP

Pianificato fase **F5+** (post-GA):
- Swap SQLite → Postgres.
- Keycloak OIDC live (multi-IdP).
- Qdrant cluster con namespace per tenant.
- Helm chart Kubernetes.
- Tenant isolation: row-level security, per-tenant encryption key.
- Quota & rate limiting per tenant.
- Billing hooks (usage-based pricing).

## 5.6 Compliance & Certificazioni Target

- **MVP:** allineamento ISO 27001 Annex A controlli logging, access control.
- **Post-MVP (F6):** audit ISO 27001, SOC2 Type II, GDPR DPIA prodotto.
