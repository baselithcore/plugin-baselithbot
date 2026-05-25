# systemd units

Unit/timer per backup automatici. Path-based, single-host single-process.
Multi-host: usa lo stesso schedule + S3 dedup, oppure un cron job centralizzato.

## Install

```bash
sudo cp deploy/systemd/llm-wiki-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llm-wiki-backup.timer
```

## Verifica

```bash
systemctl list-timers llm-wiki-backup.timer
systemctl status llm-wiki-backup.service
journalctl -u llm-wiki-backup.service -n 200 --no-pager
```

## Run manuale (drill restore)

```bash
sudo systemctl start llm-wiki-backup.service
ls -lh /srv/llm-wiki/backups/{postgres,qdrant,vaults}/
```

## Override env

Senza editare l'unit:

```bash
sudo systemctl edit llm-wiki-backup.service
# aggiungi:
# [Service]
# Environment=BACKUP_S3_BUCKET=llm-wiki-prod-backups
# Environment=BACKUP_RETENTION_DAYS=30
```

Oppure via `/srv/llm-wiki/.env` (chiavi `POSTGRES_PASSWORD`, `BACKUP_S3_BUCKET`, ecc.). Il
file deve essere KEY=VALUE plain — lo stesso `.env` dell'app va bene.

## Drill periodico

Run trimestrale: ripristina ultimo dump in DB scratch e verifica conteggi:

```bash
# DB di staging
POSTGRES_DB=llm_wiki_drill ./scripts/restore_postgres.sh /srv/llm-wiki/backups/postgres/latest.dump
psql -h localhost -p 5433 -U llm_wiki -d llm_wiki_drill -c "
  SELECT 'tenants' t, count(*) FROM tenants
  UNION ALL SELECT 'users', count(*) FROM users
  UNION ALL SELECT 'memories', count(*) FROM memories;
"
```
