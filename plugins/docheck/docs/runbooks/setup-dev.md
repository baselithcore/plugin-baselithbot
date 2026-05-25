# Runbook: Setup Dev Environment

## Prerequisiti

- Python 3.12+, `uv` installato.
- Node 20+, `pnpm 9+`.
- **MVP usa SQLite plain** + FS-level encryption (LUKS/FileVault/BitLocker). Vedi [ADR-0008](../adr/0008-encryption-at-rest-strategy.md).
- Optional DB-level encryption (extra `[encryption]`):
    - macOS: `brew install sqlcipher`
    - Linux: `sudo apt-get install libsqlcipher-dev`
    - Install: `uv sync --extra encryption`
    - Activate: `DOCHECK_DB_ENCRYPTION_ENABLED=true`
- Server vLLM raggiungibile (locale o DGX Spark) o stub OpenAI-compatible per dev.

## Engine

> **CWD convention**: avvia engine **sempre** da `docheck-engine/`. Path in `.env` sono relativi (`./storage/...`). CWD diverso → file storage diverso → DB/audit fuori-sync. Docker/systemd fissano `WorkingDirectory` automaticamente.

```bash
cd docheck-engine
cp .env.example .env
uv sync --extra dev
uv run alembic upgrade head
uv run python ../scripts/seed_admin.py       # crea admin (prompt email + pw ≥12 char)
uv run python ../scripts/seed_policies.py    # seed policy IT/EU
uv run python -m docheck.main                # avvia su Unix socket
```

Per dev browser-based:

```bash
DOCHECK_BIND_TCP=127.0.0.1:8765 uv run python -m docheck.main
```

## UI

```bash
cd docheck-ui
pnpm install
pnpm dev                                      # http://localhost:3000
# in altro terminale:
pnpm electron:dev
```

## LLM stub locale (CPU dev, no GPU)

Opzione A — **Mock LLM** (consigliato per dev offline rapido):

```bash
uv run python scripts/mock_llm.py    # binds 127.0.0.1:8000
```

Risposte canned per ciascun agent. Engine già configurato per `DOCHECK_LLM_BASE_URL=http://127.0.0.1:8000/v1`.

Opzione B — **Ollama**:

```bash
ollama serve
ollama pull llama3.1:8b-instruct-q4_K_M
DOCHECK_LLM_BASE_URL=http://127.0.0.1:11434/v1 uv run python -m docheck.main
```

Opzione C — **vLLM** (DGX Spark): vedi [docker/compose.yml](../../docker/compose.yml).

## Reset DB / Storage

```bash
rm -rf docheck-engine/storage
uv run alembic upgrade head
uv run python scripts/seed_policies.py
```

## Troubleshooting

- **`pysqlcipher3` install fail** → installa `libsqlcipher-dev` system-wide.
- **PaddleOCR slow first run** → scarica modelli su disco al primo OCR (warmup ~30s).
- **Embedding model download lento** → pre-cache `BAAI/bge-m3` con `huggingface-cli download`.
