# Chaos Drills

Scenari di fault injection controllata per validare resilienza pre-prod e training oncall. Ogni drill ha:

1. **Setup** — stato iniziale atteso
2. **Inject** — fault deliberato
3. **Observe** — cosa misurare (response code, log, metriche)
4. **Recover** — ripristino + verifica

Eseguire **solo su staging**. Mai prod.

## Drill list

|Drill|Script|Durata|Blast radius|
|-----|------|------|------------|
|DB connection loss|[`drill_postgres_down.sh`](drill_postgres_down.sh)|~3min|Auth + memorie + conv 503; chat read-only OK|
|Qdrant down|[`drill_qdrant_down.sh`](drill_qdrant_down.sh)|~3min|Retrieval fail; chat → no_hits fallback|
|Ollama down|[`drill_ollama_down.sh`](drill_ollama_down.sh)|~3min|Chat 500; ingest job stuck|
|Disk full|[`drill_disk_full.sh`](drill_disk_full.sh)|~5min|Ingest write fail; log rotation kick|
|Memory pressure|[`drill_memory_pressure.sh`](drill_memory_pressure.sh)|~2min|Worker OOM kill + restart|

## Run

```bash
# Tutti
for d in scripts/chaos/drill_*.sh; do
    bash "$d" || echo "FAIL: $d"
done

# Singolo
bash scripts/chaos/drill_postgres_down.sh
```

## Prerequisiti

- Docker Compose stack attivo
- App locale su :8000
- `curl`, `jq`, `docker`
