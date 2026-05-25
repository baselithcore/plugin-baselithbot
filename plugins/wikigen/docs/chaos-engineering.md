# Chaos Engineering

Drill di fault injection per validare resilienza pre-prod e training oncall. Scripts in [`scripts/chaos/`](../scripts/chaos/). **Run solo su staging, mai prod.**

## Drill disponibili

|Drill|Script|Inject|Atteso|
|-----|------|------|------|
|DB outage|[`drill_postgres_down.sh`](../scripts/chaos/drill_postgres_down.sh)|`docker stop postgres`|`/health/live` 200, `/health/ready` 503, `dependencies.postgres.ready=false`, recovery automatico al restart|
|Qdrant outage|[`drill_qdrant_down.sh`](../scripts/chaos/drill_qdrant_down.sh)|`docker stop qdrant`|`/health/ready` 503, retrieval fail graceful, recovery automatico|
|Ollama outage|[`drill_ollama_down.sh`](../scripts/chaos/drill_ollama_down.sh)|kill process / `iptables REJECT 11434`|chat 5xx no hang, ingest job FAILED, recovery dopo restart|
|Disk pressure|[`drill_disk_full.sh`](../scripts/chaos/drill_disk_full.sh)|`fallocate` riempie target dir|app non crasha, write fail graceful, cleanup ripristina|
|Memory pressure|[`drill_memory_pressure.sh`](../scripts/chaos/drill_memory_pressure.sh)|`docker update --memory 512m`|OOM kill → restart → live recover|

## Run

```bash
# Single drill
bash scripts/chaos/drill_postgres_down.sh

# Tutti (sequenza, non parallelo — ogni drill assume baseline pulita)
for d in scripts/chaos/drill_*.sh; do
    bash "$d" && echo "PASS: $d" || echo "FAIL: $d"
done
```

Exit code 0 = tutti i check pass. Exit code N = N check falliti.

## Cadenza

- Pre-release maggiore: tutta la suite su staging
- Mensile: drill DB + Qdrant (più frequenti realmente)
- Onboarding oncall: shadowing drill + post-mortem template

## Anatomia drill

Ogni script segue 4 fasi:

1. **Setup** — verifica baseline (live + ready entrambi 200)
2. **Inject** — fault deterministico (stop container, kill process, fallocate)
3. **Observe** — check graceful degradation (response code, log pattern)
4. **Recover** — ripristina + verifica ritorno baseline

Script usa `set -uo pipefail` (no `-e`) e tracking PASS/FAIL per ogni check; non si ferma al primo fail per dare visibilità completa.

## Estendere

Aggiungi un nuovo drill seguendo template `drill_postgres_down.sh`:

```bash
log "=== drill_<name> ==="
check "baseline X" curl ...
# inject
check "live still 200" ...
check "ready returns 503" ...
# recover
check "post-recovery ready" ...
log "=== summary: $PASS passed, $FAIL failed ==="
exit $FAIL
```

Aggiorna anche `scripts/chaos/README.md` + questo doc.

## Limitazioni

- Drill richiedono Docker stack — non riproducono fault di rete inter-DC, cert expiry, regression in upstream LLM provider
- Memory pressure assume container managed; bare-metal richiede ulimit + cgroup setup manuale
- Disk full drill è approssimativo: filesystem reale e quota si comportano diversamente
- Ollama drill su Mac usa launchctl/pkill; comportamento ≠ Linux iptables REJECT
