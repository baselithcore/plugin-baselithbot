# Operations & Maintenance

Runbook operativo. Per deploy iniziale → [`deployment.md`](deployment.md). Per dashboard e alert → [`observability.md`](observability.md).

## Routine giornaliera

| Cosa | Strumento | Soglia attenzione |
| ---- | --------- | ----------------- |

| Salute servizi | Grafana "App Metrics" + alertmanager | error rate > 1% |
| Backup completati | log cron / S3 listing | mancato → rerun + alert |
| Job ingest stuck | `/api/ingest/raw/jobs?status=running` | running > 30min |
| Disk usage | node-exporter dashboard | > 80% |
| Audit anomalie | Loki query `level=WARN` su `auth.*` | spike inatteso |

## Routine settimanale

```bash
# 1. Doctor pre-flight
python -m llm_wiki doctor --strict --json

# 2. Vacuum + analyze Postgres
psql -h localhost -p 5433 -U llm_wiki -d llm_wiki <<SQL
VACUUM (ANALYZE, VERBOSE);
REINDEX TABLE memories;
SQL

# 3. Cleanup token scaduti
psql -h localhost -p 5433 -U llm_wiki -d llm_wiki <<SQL
DELETE FROM refresh_tokens WHERE expires_at < NOW() - INTERVAL '7 days';
DELETE FROM setup_invitations WHERE used_at IS NULL AND expires_at < NOW() - INTERVAL '30 days';
SQL

# 4. Verifica integrità Qdrant
curl http://localhost:6333/collections/<APP_DOMAIN>-wiki | jq

# 5. Aggiornamenti OS (se attivati unattended)
sudo unattended-upgrades --dry-run --debug
```

## Routine mensile

| Attività | Note |
| -------- | ---- |

| Test restore Postgres | Su host staging, da backup random degli ultimi 7 giorni |
| Test restore Qdrant | Verifica chunk count + spot-check query |
| Rotazione `SECRET_KEY` | Programmata (invalida tutti i JWT, comunica downtime) |
| Audit event review | Loki/Grafana dashboard "Auth & Security" |
| Capacity review | Trend disco / connessioni DB / RAM |
| Aggiornamenti dipendenze | `pip list --outdated`, `npm outdated` |

## Backup

Script pronti in [`scripts/`](../scripts/):

| Script                | Cosa                                                      | Output                                                        |
| --------------------- | --------------------------------------------------------- | ------------------------------------------------------------- |
| `backup_postgres.sh`  | `pg_dump -Fc` compresso + sha256                          | `backups/postgres/llm_wiki-<TS>.dump` + `latest.dump` symlink |
| `backup_qdrant.sh`    | snapshot REST API per ogni collection + sha256            | `backups/qdrant/<coll>-<TS>.snapshot`                         |
| `backup_vaults.sh`    | tar.zst di `vaults/` + `domains/`                         | `backups/vaults/vaults-<TS>.tar.zst`                          |
| `restore_postgres.sh` | `pg_restore --clean --if-exists` (verifica sha256)        | richiede conferma `yes` o `FORCE=1`                           |
| `restore_qdrant.sh`   | upload snapshot via `/snapshots/upload?priority=snapshot` | idem                                                          |

Tutti rispettano `BACKUP_RETENTION_DAYS` (default 14) e fanno sync opzionale su `BACKUP_S3_BUCKET` se `aws-cli` configurato.

Schedule via systemd timer in [`deploy/systemd/`](../deploy/systemd/) — daily 02:30 UTC con jitter 15min:

```bash
sudo cp deploy/systemd/llm-wiki-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llm-wiki-backup.timer
systemctl list-timers llm-wiki-backup.timer
```

### Postgres logical (giornaliero)

```bash
# Manuale
./scripts/backup_postgres.sh

# Override retention
BACKUP_RETENTION_DAYS=30 ./scripts/backup_postgres.sh

# Sync S3
BACKUP_S3_BUCKET=llm-wiki-prod-backups ./scripts/backup_postgres.sh
```

### Postgres WAL (continuous, PITR)

Setup `wal-g`:

```bash
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'wal-g wal-push %p'
restore_command = 'wal-g wal-fetch %f %p'
```

Base backup settimanale:

```bash
wal-g backup-push /var/lib/postgresql/16/main
```

Restore PITR:

```bash
wal-g backup-fetch /var/lib/postgresql/16/main LATEST
# In recovery.conf:
recovery_target_time = '2026-05-02 14:30:00 UTC'
```

### Qdrant snapshot

```bash
# Tutte le collection
./scripts/backup_qdrant.sh

# Solo selezionate
QDRANT_COLLECTIONS=insurance-wiki,legal-wiki ./scripts/backup_qdrant.sh
```

Restore (DESTRUCTIVE — rimpiazza collection):

```bash
./scripts/restore_qdrant.sh insurance-wiki ./backups/qdrant/insurance-wiki-<TS>.snapshot
```

### Vaults (`wiki/` + `raw/`)

```bash
./scripts/backup_vaults.sh
```

Output `tar.zst` (zstd -19) che include `vaults/` + `domains/` (config + prompts + `.synth.meta.json`). `raw/` è read-only by convention → rebuilds idempotenti dopo restore. `wiki/` contiene output LLM = riproducibile da `raw/` se persi (al costo di reingest).

Restic in alternativa per dedup cross-snapshot:

```bash
restic -r s3:.../vaults backup /srv/llm-wiki/vaults --tag daily
restic -r s3:.../vaults forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
```

### `.env` + Domain Packs

Encrypt + git:

```bash
# Setup (una volta)
sops --pgp <KEY-ID> .env > .env.enc
git add .env.enc

# Edit
sops .env.enc

# Decrypt al deploy
sops -d .env.enc > .env
```

## Restore disaster

### Scenario: Postgres irrecuperabile

```bash
# 1. Stop app
sudo systemctl stop llm-wiki

# 2. Drop + recreate DB
psql -h localhost -p 5433 -U postgres <<SQL
DROP DATABASE llm_wiki;
CREATE DATABASE llm_wiki OWNER llm_wiki;
SQL

# 3. Restore dump (script verifica sha256, richiede conferma)
./scripts/restore_postgres.sh ./backups/postgres/latest.dump
# o non-interattivo:
FORCE=1 ./scripts/restore_postgres.sh ./backups/postgres/llm_wiki-<TS>.dump

# 4. Verifica
psql ... -c "SELECT COUNT(*) FROM users;"
psql ... -c "SELECT COUNT(*) FROM conversations;"

# 5. Restart
sudo systemctl start llm-wiki
```

### Scenario: Qdrant data loss

Opzione A — restore snapshot (preferita):

```bash
# vedi Backup §Qdrant snapshot
```

Opzione B — reingest da `raw/`:

```bash
# Drop collection
curl -X DELETE "http://localhost:6333/collections/<APP_DOMAIN>-wiki"

# Restart app → al boot ricrea collection vuota
sudo systemctl restart llm-wiki

# Reingest tutti i PDF in raw/
for pdf in /srv/llm-wiki/vaults/<domain>/raw/*.pdf; do
  python -m llm_wiki ingest "$pdf"
done
```

### Scenario: corruption pack

```bash
# Pack source ancora in git → reset
cd domains/<pack>
git checkout HEAD -- pack.yaml schema.yaml prompts/

# Pack scaffolded user → ripristina da backup vault
```

## Manutenzione utenti / RBAC

### Reset password admin

```bash
python -m llm_wiki create-superuser \
  --email admin@example.com \
  --password "<nuova>" \
  --force-update
```

(`--force-update` aggiorna password se utente esiste; default refuse)

In alternativa SQL diretto (emergenza):

```bash
NEW_HASH=$(python -c "from llm_wiki.auth.passwords import hash_password; print(hash_password('NewPass123'))")
psql ... -c "UPDATE users SET password_hash='$NEW_HASH', password_must_change=TRUE WHERE email='admin@example.com';"
```

### Sospendere utente

```sql
UPDATE users SET is_active = FALSE WHERE email = 'user@example.com';
-- + revoca tutti i refresh
DELETE FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE email='user@example.com');
```

### Lista permessi effettivi di un utente

```sql
SELECT DISTINCT p.slug
FROM user_roles ur
JOIN role_permissions rp ON rp.role_id = ur.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE ur.user_id = (SELECT id FROM users WHERE email = 'user@example.com');
```

### GDPR right to erasure

```bash
USER_ID=$(psql -At ... -c "SELECT id FROM users WHERE email = 'user@example.com';")

psql ... <<SQL
-- Cascade automatico per refresh_tokens, conversations, messages, memories
DELETE FROM users WHERE id = '$USER_ID';

-- Anonimizza audit (mantiene cronologia eventi)
UPDATE audit_events SET user_id = NULL WHERE user_id = '$USER_ID';
SQL
```

## Manutenzione ingest

### Riavviare un job fallito

```bash
JOB_ID=...
curl -X POST "http://127.0.0.1:8000/api/ingest/raw/jobs/$JOB_ID/retry" \
  -H "Authorization: Bearer <admin-token>"
```

### Forzare reingest singola pagina

```bash
# Cancella source page corrente
rm /srv/llm-wiki/vaults/<domain>/wiki/<folder>/<slug>.md

# Riprocessa
python -m llm_wiki ingest /srv/llm-wiki/vaults/<domain>/raw/<file>.pdf
```

### Pulire `.new.md` / `.needs-review.md` accumulate

```bash
find /srv/llm-wiki/vaults/<domain>/wiki -name "*.new.md" -mtime +7 -delete
find /srv/llm-wiki/vaults/<domain>/wiki -name "*.needs-review.md" -mtime +30
# inspect prima di delete
```

## Switch Domain Pack

```bash
# Con app accesa: scrivi via admin API
curl -X POST http://127.0.0.1:8000/api/admin/tenants/medical/activate \
  -H "Authorization: Bearer <superuser>"

# Riavvia (single-tenant per processo: nuovo APP_DOMAIN richiede restart)
sudo systemctl restart llm-wiki
```

CLI equivalente:

```bash
python -m llm_wiki pack activate medical
sudo systemctl restart llm-wiki
```

## Upgrade dipendenze

```bash
# Backend
pip list --outdated
pip install -e ".[hybrid,ingest,obs]" --upgrade
pytest tests/                # smoke test
alembic upgrade head         # se nuove migrations

# Frontend
cd frontend
npm outdated
npm update
npm run build
npm run lint && npx tsc --noEmit
```

## Monitorare costi LLM

Se usi OpenAI:

```bash
# Telemetria già esposta via wiki_events_total{name="llm.openai.tokens"}
```

Grafana panel:

```promql
sum by (model) (rate(wiki_events_total{name=~"llm\\.openai\\.tokens.*"}[1h])) * 3600
```

Cap mensile: alert quando proiezione 30g > budget.

## Troubleshooting

### App non parte

```bash
journalctl -u llm-wiki -n 100
# Errori comuni:
#  - "SECRET_KEY too short" → genera nuovo token urlsafe(48)
#  - "DATABASE_URL invalid" → verifica formato
#  - "Pack not found" → APP_DOMAIN non scaffoldato; rimuovi APP_DOMAIN dal .env per setup mode
```

### Latenza chat alta improvvisa

Check in ordine:

1. Ollama keep-alive: `curl http://localhost:11434/api/ps` — modello in VRAM?
2. Qdrant load: dashboard "RAG Performance" panel "retrieval latency".
3. DB pool waiting: `pg_pool_connections{state="waiting"} > 0`?
4. CPU steal (VM): `top` colonna `st`.

### Loop ingest infinito

Sintomo: `INGEST_CRITIC_MAX_ITER > 1` + linter fallisce sempre.

```bash
# Forza salvataggio "needs-review" senza loop
INGEST_CRITIC_MAX_ITER=1 python -m llm_wiki ingest <pdf>
```

Poi correggi a mano i file `.needs-review.md`.

### Refresh token replay storm

Spike di `auth.refresh.replay_detected` → possibile attacco o bug client. Mitigazione immediata:

```sql
-- Revoca tutti i refresh dell'utente sospetto
DELETE FROM refresh_tokens WHERE user_id = '<id>';
-- L'utente sarà forzato a re-login (e-mail + password)
```

Indaga via `audit_events` filter `event_type = 'auth.refresh.replay_detected' AND user_id = '...'`.

### `429` su utente legittimo

Aumenta limit per scope:

```ini
RATE_LIMIT_USER_PER_MINUTE=300
```

Restart. Per single-user con uso anomalo (script), considera RBAC custom + bypass mirato.

### RLS blocca admin query

Errore: `permission denied for table conversations` da uno script admin.

```python
# Usa connessione con role privilegiato
from llm_wiki.db.connection import with_admin_role

async with with_admin_role() as conn:
    # query cross-tenant
    ...
```

E logga l'evento in `audit_events` con `event_type='admin.cross_tenant_query'`.

## Pre-flight checks (`doctor`)

```bash
python -m llm_wiki doctor --strict --json
```

Output JSON:

```json
{
  "checks": [
    {"name": "domain_pack", "status": "ok", "detail": "legal loaded"},
    {"name": "vault", "status": "ok", "writable": true},
    {"name": "qdrant", "status": "ok", "url": "http://localhost:6333"},
    {"name": "llm_provider", "status": "ok", "vendor": "ollama"},
    {"name": "postgres", "status": "ok", "schema_version": "009"},
    {"name": "secret_key", "status": "warn", "detail": "below recommended length"},
    {"name": "env_conflicts", "status": "ok"}
  ],
  "exit_code": 0
}
```

Codici exit:

- `0` — ok
- `1` — warning (ignorato senza `--strict`)
- `2` — errore bloccante

Integrabile in pipeline CI/CD pre-deploy.

## Logbook events di interesse

Loki query template:

```logql
{job="llm-wiki", level=~"WARN|ERROR"} != "REDACTED"

{job="llm-wiki"} | json | event_type="auth.login.failed" | rate(1m) > 0.1

{job="llm-wiki"} | json | latency_ms > 2000
```

Tracciare in dashboard:

- p99 chat latency
- ingest failure rate
- audit volume per event_type
- token refresh anomalies

## Quando contattare sviluppatori

| Sintomo                               | Sì/No                                    |
| ------------------------------------- | ---------------------------------------- |
| Crash ricorrenti dopo restart         | Sì                                       |
| RLS violation > 0 in audit            | Sì (incident)                            |
| Migration fallisce a metà             | Sì (DB locked)                           |
| Linter ingest sempre fallisce su pack | Sì (regressione)                         |
| Latenza graduale degradata            | Capacity → no, codice → forse            |
| OOM su worker                         | Capacity → no (più RAM/scale), leak → sì |

Allegare sempre: `doctor --json`, journalctl ultime 200 linee, dashboard screenshot del periodo, esempio richiesta riproducibile.
