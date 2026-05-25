# Module: services/audit

Append-only audit log con hash chain Ed25519. Immutabile (trigger SQLite).

## Schema record

```
seq, ts, user_id, action, resource, payload_hash, prev_hash, entry_hash, signature
```

`entry_hash = SHA256(prev_hash || canonical_json({tenant_id, user_id, action, resource, payload_hash, prev_hash}))`
`signature = Ed25519_sign(entry_hash, master_key)`

## API

- `append_audit(db, action, user_id, resource, payload)` — appende record nuovo per tenant corrente (vedi [tenant.md](tenant.md)).
- `verify_chain(db) -> (ok, broken_seq?)` — valida chain del tenant corrente.
- Public key esposta via `/api/v1/info/pubkey`.

## Multi-tenant isolation

Ogni record include `tenant_id`. Chain hash include `tenant_id` in canonical JSON → chain di tenant A indipendente da tenant B. `prev_hash` lookup filtra per `tenant_id == current_tenant()`.

Tampering record di un tenant non rompe chain integrity di altri tenant.

## Storage chiave

- File: `storage/audit_ed25519.key` (mode 0600).
- Generata al primo avvio se mancante (warning log).
- Production: spostare in OS keychain (macOS Keychain / DPAPI / secret-service).

## Test

[`tests/test_audit_chain.py`](../../docheck-engine/tests/test_audit_chain.py) verifica append + integrità.

## Operativo

- Job daily: `verify_chain` → alert su mismatch.
- Backup: snapshot `storage/docheck.db` + `storage/audit_ed25519.key` (key cifrata in backup vault).
- Recovery: restore DB; chain validata automaticamente.
