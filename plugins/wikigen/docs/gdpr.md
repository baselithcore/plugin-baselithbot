# GDPR / DSAR & Audit Retention

Implementazione tecnica dei diritti GDPR Art. 15 (accesso) e Art. 17 (cancellazione) + retention audit log conforme ISO 27001 A.12.4.

## Endpoint utente

|Metodo|Path|Articolo|Auth|Rate limit|
|------|----|--------|----|----------|
|`GET`|`/api/me/export`|Art. 15 — accesso|`require_user`|user|
|`DELETE`|`/api/me`|Art. 17 — cancellazione|`require_user`|user|

### Export (DSAR)

```bash
curl -H "Authorization: Bearer $TOKEN" https://wiki.example.com/api/me/export > my-data.json
```

Output JSON struttura stabile (schema_version=1):

```json
{
  "exported_at": "2026-05-02T18:30:00+00:00",
  "schema_version": 1,
  "user": { "id": "...", "email": "...", "display_name": "...", ... },
  "conversations": [ { "id": "...", "title": "...", "messages": [...] } ],
  "memories": [ ... ],
  "feedback": [ ... ],
  "audit_events": [ ... ]
}
```

`password_hash` mai esportato. Limit 1000 righe per tabella (paginabile in v2 se serve).

### Delete (Right to Erasure)

```bash
curl -X DELETE -H "Authorization: Bearer $TOKEN" https://wiki.example.com/api/me
# 204 No Content su successo
# 409 Conflict se è l'unico superuser
# 500 se DELETE fallisce (DB issue)
```

Cascata:

- `refresh_tokens.user_id FK CASCADE` → tutti i refresh dell'utente eliminati
- `conversations.user_id FK CASCADE` → conversazioni + (cascata) `messages`
- `memories.user_id FK CASCADE` → tutte le memorie personali
- `feedback.user_id FK CASCADE` → feedback dato dall'utente
- `user_roles` / `user_domains` → grant rimossi
- `audit_events.user_id FK SET NULL` → traccia anonimizzata sopravvive

Il campo `audit_events.user_id` impostato a `NULL` mantiene la sequenza eventi per dimostrare GDPR Art. 5(2) accountability anche post-cancellazione, senza più collegare l'evento alla persona.

### Audit DSAR

Ogni richiesta DSAR (export o delete) emette evento:

- `gdpr.export` — payload `{conversations, memories, feedback, audit_events}` (conteggi, non contenuto)
- `gdpr.delete` — payload `{email_hash}` (SHA-256 trunc 16 dell'email pre-delete)

Fonte di prova in caso di audit ispettivo (Garante / DPA).

## Last-superuser protection

`DELETE /api/me` rifiuta con 409 se l'utente è l'unico possessore del system role `superuser`. Mitigazione: promuovere prima un altro utente.

```bash
curl -X POST .../api/admin/users/$NEW_ADMIN_ID/roles \
  -d '{"role_slug":"superuser"}' -H "Authorization: Bearer $SU_TOKEN"
```

## Audit log integrity (ISO 27001 A.12.4)

Migration [`010_audit_append_only`](../alembic/versions/010_audit_append_only.py) applica:

1. **Trigger `BEFORE UPDATE OR DELETE`** su `audit_events` — solleva `insufficient_privilege` su qualunque modifica, anche da superuser SQL diretto.
2. **Eccezione FK CASCADE SET NULL** — il trigger consente UPDATE solo se cambiano esclusivamente `user_id` o `tenant_id` da non-NULL a NULL (cascade legittimo dopo delete utente/tenant).
3. **Eccezione prune controllato** — `prune_audit_events(retention_days)` SECURITY DEFINER imposta `set_config('audit.allow_prune', 'true', true)` in transazione locale; il trigger riconosce il flag e permette DELETE.
4. **Self-audit del prune** — la funzione registra in `audit_events` un evento `audit.prune` con `{removed, retention_days}` per chain of custody.

### Bypass impossibili (in design)

|Vettore|Risultato|
|-------|---------|
|`UPDATE audit_events SET kind='tampered' ...`|`ERROR: audit_events is append-only`|
|`DELETE FROM audit_events WHERE kind='auth.login.failed'`|stesso errore|
|`TRUNCATE audit_events`|TRUNCATE non passa per trigger di riga; mitigare con permission grant separata (vedi sotto)|

### Postgres role hardening (mig 011)

[`011_audit_role_hardening`](../alembic/versions/011_audit_role_hardening.py) defense-in-depth oltre il trigger:

- `app_runtime` ottiene SOLO `SELECT, INSERT` su `audit_events` (no UPDATE/DELETE/TRUNCATE)
- TRUNCATE non passa per trigger di riga: la revoke a livello permessi è l'unica protezione
- `EXECUTE` su `prune_audit_events()` revocato da `app_runtime` e `PUBLIC`. Solo DBA / job dedicato (con credenziali separate) lo invoca

Per attivare il role applicativo: setta `POSTGRES_USER=app_runtime` con password dedicata. Setup base in mig 006 (RLS), audit hardening in 011.

## Retention pruning

[`scripts/audit_retention.sh`](../scripts/audit_retention.sh) chiama `prune_audit_events($AUDIT_RETENTION_DAYS)`.

**Default retention 730 giorni (2 anni)** — bilanciamento tra:

- GDPR Art. 5(1)(e) — minimizzazione (no retention indefinito)
- ISO 27001 A.18.1.3 — records preservation (almeno 1 anno tipicamente)
- Standard finanziari (es. PSD2) — fino a 5 anni se applicabile

Override:

```bash
AUDIT_RETENTION_DAYS=1825 ./scripts/audit_retention.sh    # 5 anni
```

Min ammesso: 30 giorni (rifiuto duro lato funzione SQL).

### Schedule

[`deploy/systemd/llm-wiki-audit-retention.{service,timer}`](../deploy/systemd/) — settimanale Domenica 03:30 UTC.

```bash
sudo cp deploy/systemd/llm-wiki-audit-retention.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llm-wiki-audit-retention.timer
```

## Compliance mapping

|Requisito|Implementazione|
|---------|---------------|
|GDPR Art. 15 (right to access)|`GET /api/me/export`|
|GDPR Art. 17 (right to erasure)|`DELETE /api/me`|
|GDPR Art. 5(1)(c) (minimizzazione)|`audit_events` retention 2 anni default|
|GDPR Art. 5(2) (accountability)|audit log immutabile + anonimizzato post-delete|
|GDPR Art. 32 (security of processing)|RBAC + RLS + audit immutabile|
|ISO 27001 A.12.4 (audit log integrity)|trigger append-only + chain of custody su prune|
|ISO 27001 A.18.1.3 (records retention)|retention configurabile, default 2 anni|
|SOC2 CC7.2 (anomaly detection)|tutti gli eventi auth/admin auditati|

## Test

`tests/test_gdpr_db.py` (Postgres-required, 6 test):

- cascade owned rows
- audit user_id SET NULL
- UPDATE audit_events bloccato
- DELETE audit_events bloccato
- prune retention min 30
- prune self-audit logged

```bash
pytest tests/test_gdpr_db.py -v
```
