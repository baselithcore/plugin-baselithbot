# Runbook — Restore audit chain dopo incidente

Procedura recovery quando `GET /api/v1/audit/verify` ritorna `ok=false` o si sospetta tampering / corruzione del log immutabile.

**Audience**: ops + security lead + DPO.
**Severity**: alta. L'audit chain è prova di non-ripudio. Una rottura va trattata come incidente di sicurezza.
**Goal**: ripristinare integrity verificabile, identificare causa, documentare gap inevitabile.

## Pre-flight

**Non agire d'impulso**. Prima di qualsiasi operazione:

1. **Stop engine writes**:
   ```bash
   docker compose stop engine
   # Tenants in produzione: comunica downtime al cliente.
   ```

2. **Snapshot DB e key correnti** (forensic copy, read-only):
   ```bash
   FORENSIC=/mnt/forensic/docheck/$(date +%Y%m%d_%H%M)
   mkdir -p "$FORENSIC"
   cp /opt/docheck/storage/docheck.db "$FORENSIC/docheck.db.orig"
   cp /opt/docheck/storage/audit_ed25519.key "$FORENSIC/audit_ed25519.key.orig"
   sha256sum "$FORENSIC"/* > "$FORENSIC/sha256.txt"
   chmod -R 0400 "$FORENSIC"
   ```

3. **Apri ticket incidente** + notifica DPO entro 24h se è coinvolto trattamento PII (GDPR Art. 33 — assess applicability).

## Step 1 — Diagnosi

### Identifica il punto di rottura

```bash
docker compose start engine
curl http://localhost:8765/api/v1/audit/verify \
  -H "Authorization: Bearer <admin-jwt>"
# {"ok": false, "broken_seq": 1042, "total_entries": 1543}
```

`broken_seq` = primo seq con hash chain inconsistente.

### Esamina record adiacenti

```bash
for seq in 1041 1042 1043; do
  curl -s "http://localhost:8765/api/v1/audit/$seq" \
    -H "Authorization: Bearer <admin-jwt>" | jq .
done
```

Confronta `prev_hash`, `entry_hash` ricalcolato manualmente, `signature` validation.

### Possibili cause

| Causa | Indicatore | Severity |
|-------|-----------|----------|
| **Tampering deliberato** | UPDATE/DELETE su `audit_log` (trigger fail dovrebbe averlo bloccato) | Critical — security incident |
| **Corruzione DB** | Disk error log host, `PRAGMA integrity_check` fail | High |
| **Bug applicativo** | Anomalia in code path append (race, bug canonicalization) | Medium — fixable, gap reale |
| **Restore parziale** | Chain riprende dopo restore con prev_hash inatteso | Medium — recovery procedure mismatch |
| **Key mismatch post-rotation** | Rollover record assente o malformato | Medium — vedi [rotate-keys.md](rotate-keys.md) |

## Step 2 — Recovery strategy

### Caso A — Corruzione DB / restore needed

1. Identifica ultimo backup con chain valida:
   ```bash
   for d in /mnt/backup/docheck/*/; do
     ts=$(basename "$d")
     # Restore DB temp + verify
     cp "$d/docheck.db" /tmp/test.db
     # Esegui verify in container ephemeral
     docker run --rm -v /tmp/test.db:/data/test.db docheck-engine:0.1.0 \
       python -c "from docheck.services import audit; ..."
     # log esito
   done
   ```

2. Restore DB da snapshot ok:
   ```bash
   docker compose stop engine
   cp /opt/docheck/storage/docheck.db /opt/docheck/storage/docheck.db.broken
   cp /mnt/backup/docheck/<good-date>/docheck.db /opt/docheck/storage/docheck.db
   docker compose start engine
   curl http://localhost:8765/api/v1/audit/verify  # → ok=true
   ```

3. **Gap documentation**: tutti gli eventi fra il backup e il punto di rottura sono **persi dall'audit chain**. Documenta il gap in un audit append speciale:

   ```bash
   curl -X POST http://localhost:8765/api/v1/admin/audit/gap-record \
     -H "Authorization: Bearer <admin-jwt>" \
     -H "Content-Type: application/json" \
     -d '{
       "gap_start_ts": "2026-05-04T10:00:00Z",
       "gap_end_ts": "2026-05-04T15:30:00Z",
       "broken_seq": 1042,
       "rationale": "DB corruption, restored from backup <date>. Eventi non recuperabili dalla chain. Cross-reference: filesystem audit + application logs.",
       "incident_ticket": "SEC-2026-042"
     }'
   ```
   *(TODO endpoint admin pre-GA. Per ora: helper `scripts/audit_gap_record.py`.)*

### Caso B — Tampering deliberato

1. **Non restorare immediatamente**. Preserva forensic snapshot.
2. Notifica security lead + legal counsel.
3. Indaga: chi aveva accesso al DB? Quali credenziali compromesse? Path attaccante?
4. Una volta identificato e contenuto: rotation completa chiavi ([rotate-keys.md](rotate-keys.md)) + restore da backup pre-tampering + gap record con riferimento incidente.
5. Post-mortem obbligatorio.

### Caso C — Bug applicativo

1. Identifica commit responsabile (`git bisect` su test E2E con dataset che riproduce).
2. Patch + nuovo deploy.
3. Per chain corrente: append gap record indicando che la rottura è dovuta a bug non a tampering. Se il bug ha prodotto entry tecnicamente invalide ma in buona fede, valutare:
   - Append "amendment" record che esplicita le entry coinvolte.
   - Mai ri-scrivere entry esistenti (immutabilità sacrosanta — il fix è additivo, non distruttivo).

### Caso D — Key rollover malformato

Vedi [rotate-keys.md](rotate-keys.md) procedura. Se rollover record manca o ha pubkey errata, l'unica recovery è restore pre-rotation + nuovo rollover correttamente eseguito.

## Step 3 — Verifica integrity post-recovery

```bash
# Engine running
curl http://localhost:8765/api/v1/audit/verify \
  -H "Authorization: Bearer <admin-jwt>"
# → {"ok": true, "broken_seq": null, "total_entries": N}

# Spot check 5 entry random + ultimo
curl http://localhost:8765/api/v1/audit/log?limit=5&offset=0 -H "..."
curl http://localhost:8765/api/v1/audit/<latest_seq> -H "..."

# Verifica firma report storici cross-reference
for r in <list-recent-reports>; do
  curl http://localhost:8765/api/v1/reports/$r -H "..." > /tmp/r.json
  python scripts/verify_report.py /tmp/r.json  # custom verifier
done
```

## Step 4 — Audit dell'incidente

L'incidente stesso è evento auditable. Append entry final:

- Action: `incident_recovery`
- Resource: `audit_chain`
- Payload: `{ticket, root_cause, gap_seq_range, recovery_method, signed_by_lead}`

Questo record diventa parte della chain — la chain stessa documenta come è stata recuperata.

## Step 5 — Post-mortem

Entro 5 giorni dal recovery:

- Root cause analysis.
- Action items (testing gap, monitoring miglioramento, processo).
- Aggiornamento questo runbook se la procedura è migliorata.

## Prevenzione

- Backup giornaliero + verifica restorability mensile (test automatizzato che ripristina backup random e fa verify).
- Monitoring: alert su `verify` fail (poll ogni 1h).
- DB integrity check programmato: `PRAGMA integrity_check;` settimanale.
- Multi-tenant: verifica per-tenant chain indipendente, fail di un tenant non blocca altri.

## Vedi anche

- [explanation/security-model.md](../explanation/security-model.md) — disegno audit chain.
- [rotate-keys.md](rotate-keys.md) — quando recovery coinvolge chiavi.
- [deploy-dgx.md](deploy-dgx.md) — backup setup.
- [SECURITY.md](../../SECURITY.md) — disclosure.
