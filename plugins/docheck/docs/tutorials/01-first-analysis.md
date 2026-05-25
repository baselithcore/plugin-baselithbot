# Tutorial 1 — Prima analisi end-to-end

Obiettivo: in **15 minuti**, da repository pulito a primo finding glass-box su un PDF reale.

Prerequisiti: macOS / Linux, Python 3.12, Node 20, pnpm 9, Ollama installato (`brew install ollama` o equivalente).

## Step 1 — Clone & install

```bash
git clone <repo-url> docheck
cd docheck

# Engine
cd docheck-engine
uv sync --extra dev
uv run alembic upgrade head

# UI
cd ../docheck-ui
pnpm install
```

## Step 2 — Avvia LLM locale

In un terminale separato:

```bash
ollama pull llama3.1:8b
ollama serve                         # http://127.0.0.1:11434
```

In alternativa, mock LLM (zero peso modello):

```bash
uv run --project docheck-engine python scripts/mock_llm.py
# poi in .env: DOCHECK_LLM_BASE_URL=http://127.0.0.1:8001/v1
```

## Step 3 — Seed admin + policy

```bash
cd docheck-engine
uv run python ../scripts/seed_admin.py
# Prompt interattivo:
#   Admin email: <tua-email>
#   Password (>=12 chars): <password che scegli>
# → stdout: "Created admin user: <email> (id=u-...)"
uv run python ../scripts/seed_policies.py
```

Re-run con stessa email = update password (idempotente). Password persa → re-run.

## Step 4 — Avvia engine

> **CWD convention**: engine si avvia **sempre** da `docheck-engine/`. Path `.env` sono relativi. CWD diverso → file storage diverso → DB/policy/audit fuori-sync.

Per dev locale (browser-based UI), abilita TCP loopback:

```bash
cd docheck-engine
echo 'DOCHECK_BIND_TCP=127.0.0.1:8765' >> .env
uv run python -m docheck.main
# → log: "docheck.startup version=0.1.0"
```

## Step 5 — Avvia UI

```bash
cd docheck-ui
pnpm dev                             # http://localhost:3000
```

Apri browser → `http://localhost:3000` → login con admin appena creato.

## Step 6 — Carica un documento

1. Sidebar → **Scan**.
2. Drag & drop un PDF (anche generico — un contratto NDA o privacy policy reale è ideale).
3. Limite 50MB. PDF, DOCX, XLSX, MD, TXT supportati.

L'upload calcola SHA-256, persiste in `storage/docs/<sha>`, registra audit `upload`.

## Step 7 — Lancia analisi

Dopo upload, click **Analizza**.

Cosa succede:

1. Parser estrae chunks (testo + bbox) → persistiti in `document_chunks`.
2. WebSocket `/ws/analysis/<doc_id>` apre stream eventi.
3. Pipeline LangGraph esegue: `classifier → structurer → [legal | technical | pii] (parallel) → synthesizer`.
4. Built-in deterministic policy (`DocCheck_Builtin`) sempre applicata + policy attive del tenant.
5. Output: report firmato Ed25519, score 0-100, breakdown per severity.

UI mostra `PhaseIndicator` (started → classifier → structurer → legal/tech/pii → synthesizer → done) e popolazione live di `FindingsPanel`.

Tempo target: ~30s per doc 5pp con Ollama 8B; ~90s 20pp su DGX 70B.

## Step 8 — Leggi un finding

Click su un finding nel panel di destra:

- **Highlight bbox** sul viewer (zoom-to evidence).
- **Severity** (FAIL/WARN/PASS/INFO) con colore.
- **Policy ref** — id + version + excerpt verbatim della clausola violata.
- **Confidence** — 0-1.
- **Reasoning drawer** — apri per vedere chain step-by-step (input dell'agente, retrieval result, output validato).

Glass-box guarantee: ogni finding ha `evidence.bbox` non-null e `policy_ref.excerpt` substring-matched contro retrieval. Niente allucinazioni.

## Step 9 — Verifica audit

Sidebar → **Audit**:

- Lista entry append-only: `upload`, `analyze`, `view_finding`, ...
- Click **Verify chain** → `GET /api/v1/audit/verify` → `{ok: true, total_entries: N}`.

Tampering tentativo: `sqlite3 storage/docheck.db "UPDATE audit_log SET payload_hash='x' WHERE seq=1"` → trigger `RAISE FAIL` → operazione respinta.

## Step 10 — Esporta report

Dal viewer report → **Export** → `report.json` (firmato) + `report.md`.

Verifica firma esterna:

```bash
curl http://localhost:8765/api/v1/info/pubkey
# → {"algorithm": "ed25519", "public_key": "<hex>"}
```

Usa la public key per validare `signature` nel JSON con qualsiasi tool Ed25519.

## Hai finito

Hai:

- Avviato stack engine + UI + LLM locale.
- Caricato e analizzato un documento.
- Letto finding glass-box con bbox + policy excerpt + reasoning.
- Verificato integrità audit chain.
- Esportato report firmato.

Prossimi passi:

- [Tutorial 2 — scrivi una policy](02-author-policy.md).
- [Spiegazione: come funziona la pipeline agentica](../explanation/agentic-flow.md).
- [Reference: API completa](../api/endpoints.md).

## Troubleshooting

| Sintomo | Causa probabile | Fix |
|---------|-----------------|-----|
| `503` su `/api/v1/health` | engine non avviato o socket path errato | log engine; verifica `DOCHECK_BIND_TCP` |
| WS connect fail | CORS browser dev | engine deve avere `app://docheck` o `http://localhost:3000` in allow-list (default ok) |
| "No active policies" 422 | seed non eseguito | `uv run python ../scripts/seed_policies.py` |
| Finding senza bbox | parser PDF fallback (no layout) | passa a PaddleOCR o testa su PDF text-based |
| LLM timeout | modello non caricato | `ollama list`; verifica `DOCHECK_LLM_REQUEST_TIMEOUT_S` |
| `Pipeline failed` 500 | LLM JSON output invalido + repair fallito | log engine `analyze.graph_failed`; abbassa temperature, retry |
