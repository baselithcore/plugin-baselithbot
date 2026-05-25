# Runbook — Key rotation

Procedura rotation chiavi crittografiche doCheck.

**Audience**: ops + security lead.
**Frequenza**: programmata annuale, o ad-hoc su sospetto compromise.
**Downtime atteso**: ≤ 5 min per chiave audit signing; transparent per JWT (refresh natural expiry).

## Chiavi gestite

| Chiave | Algoritmo | Storage | Uso |
|--------|-----------|---------|-----|
| Audit signing key | Ed25519 | `storage/audit_ed25519.key` (file 0600) → OS keychain post-GA | Firma audit chain entry + report |
| JWT signing key | Ed25519 (EdDSA) | OS keychain (`docheck`/`jwt`) | Firma access token |
| DB master key (SQLCipher) | random 256-bit | OS keychain (`DOCHECK_DB_KEY_KEYRING_*`) | Encryption SQLite at-rest |
| OIDC public key (Keycloak) | RS256/EdDSA | JWKS (`oidc_jwks_uri`) | Verifica token quando OIDC abilitato |

## Pre-requisiti per ogni rotation

- Backup DB + audit key corrente (cifrata GPG ops team).
- Verifica chain integrity prima: `GET /api/v1/audit/verify` → `ok=true`. Mai ruotare con chain broken.
- Finestra manutenzione comunicata.
- Accesso SSH bastion + permission keychain.

## Audit signing key (Ed25519)

**Critico**: chain è single-key. Rotation richiede append di un "key rollover" record che firma il switch e mantiene chain valida.

### Procedura

1. **Backup chiave corrente**:

   ```bash
   gpg --encrypt -r ops@example.invalid \
     -o /mnt/backup/audit_key_$(date +%Y%m%d_%H%M).gpg \
     /opt/docheck/storage/audit_ed25519.key
   ```

2. **Genera nuova chiave**:

   ```bash
   docker exec docheck-engine python -c "
   from nacl.signing import SigningKey
   k = SigningKey.generate()
   import sys, pathlib
   pathlib.Path('/data/storage/audit_ed25519.key.new').write_bytes(bytes(k))
   pathlib.Path('/data/storage/audit_ed25519.key.new').chmod(0o600)
   print('verify_key:', k.verify_key.encode().hex())
   "
   ```

3. **Append rollover record** (audit append speciale, action `key_rollover`, payload contiene `old_pubkey_hex`, `new_pubkey_hex`, firmato con **vecchia** chiave):

   ```bash
   curl -X POST http://localhost:8765/api/v1/admin/audit/key-rollover \
     -H "Authorization: Bearer <admin-jwt>" \
     -H "Content-Type: application/json" \
     -d '{"new_pubkey_hex": "<hex-from-step-2>"}'
   ```

   *(Endpoint amministrativo, presente solo in build admin tools — TODO pre-GA. Per ora: helper script `scripts/rotate_audit_key.py`.)*

4. **Swap file**:

   ```bash
   docker compose stop engine
   mv /opt/docheck/storage/audit_ed25519.key /opt/docheck/storage/audit_ed25519.key.old
   mv /opt/docheck/storage/audit_ed25519.key.new /opt/docheck/storage/audit_ed25519.key
   docker compose start engine
   ```

5. **Verifica chain**:

   ```bash
   curl http://localhost:8765/api/v1/audit/verify -H "Authorization: Bearer <admin-jwt>"
   # Atteso: {"ok": true, ...}
   ```

   `verify_chain` riconosce record `key_rollover` e usa pubkey corretta per validare entry pre/post-rollover.

6. **Notifica downstream** consumer di report firmati: nuova `verify_key` da `/info/pubkey`.

7. **Archivio chiave vecchia**: dopo 90 giorni di chain stabile, distruggi `.old` (ma mantieni backup GPG perpetuo per validazione storica).

### Migration da file → OS keychain

Pre-GA target: chiavi non più su filesystem.

```bash
# macOS (esempio)
security add-generic-password -s docheck -a audit -w "$(xxd -p -c 0 /opt/docheck/storage/audit_ed25519.key)"
# Aggiorna config: DOCHECK_AUDIT_KEY_BACKEND=keyring
# Restart engine
# Rimuovi file: shred -u /opt/docheck/storage/audit_ed25519.key
```

Linux: `secret-tool store --label="doCheck audit" service docheck account audit`. Windows: DPAPI via `keyring`.

## JWT signing key (EdDSA)

Rotation transparent: token vecchi continuano a verificare con kid pubblico nel JWKS finché non scadono naturalmente.

### Procedura

1. Genera nuovo keypair:

   ```bash
   docker exec docheck-engine python scripts/rotate_jwt_key.py --new-kid "$(date +%Y%m%d)"
   ```

2. Engine carica nuova chiave + mantiene vecchia in JWKS per `max_token_lifetime` (default 1h).

3. Dopo finestra grace, vecchia chiave rimossa automaticamente.

Nessun restart richiesto se il backend keystore supporta hot-reload (TODO: implementare).

## DB master key (SQLCipher)

Rotation richiede `PRAGMA rekey`:

```bash
docker compose stop engine
docker exec -it docheck-engine sqlcipher /data/storage/docheck.db <<EOF
PRAGMA key = '<old-master-key>';
PRAGMA rekey = '<new-master-key>';
EOF
# Aggiorna keyring con nuovo valore
keyring set docheck master <<<"<new-master-key>"
docker compose start engine
```

Verifica startup engine in log → no errore `cannot decrypt`.

## OIDC pubkey

Quando Keycloak ruota il signing key del realm:

- doCheck legge JWKS da `oidc_jwks_uri` con TTL cache (default 1h).
- Cache invalidata automaticamente al primo `kid` mismatch.
- Nessuna azione manuale richiesta.

Per forzare invalidazione: `POST /api/v1/system/cache/reset`.

## Compromise response

Se sospetto compromise (key leak, host compromise):

1. **Audit signing key**: rotation immediata + investigazione audit log per finestra di rischio. Tutti i report firmati nella finestra incerti devono essere ri-validati o re-firmati.
2. **JWT key**: rotation immediata. Force logout globale: invalida tutti i token vivi (table `revoked_tokens` o bump `min_iat` config).
3. **DB master key**: rotation immediata + valutazione se i dati sensibili erano accessibili a livello FS al momento del compromise.

Notifica DPO + security lead. Apri post-mortem entro 48h.

## Verifiche post-rotation (checklist)

- [ ] `GET /api/v1/audit/verify` → `ok=true`.
- [ ] `GET /api/v1/info/pubkey` riflette nuova chiave.
- [ ] Login utente test → JWT valido con nuovo kid.
- [ ] Lettura report storico firmato con vecchia chiave → ancora verificabile (chain rollover record presente).
- [ ] Backup nuova chiave cifrato GPG depositato.
- [ ] Log audit contiene `key_rollover` entry firmato.

## Vedi anche

- [explanation/security-model.md](../explanation/security-model.md) — strato crypto.
- [restore-audit.md](restore-audit.md) — se rotation lascia chain in stato inconsistente.
- [ADR-0008](../adr/0008-encryption-at-rest-strategy.md) — strategia encryption at-rest.
