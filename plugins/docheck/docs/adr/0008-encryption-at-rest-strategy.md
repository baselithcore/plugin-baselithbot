# ADR-0008: Encryption-at-Rest Strategy

**Status:** Accepted (revisita F4 hardening)
**Date:** 2026-05-03

## Context

ADR-0002 specificava SQLCipher come encryption-at-rest. In install reale problema:

- `pysqlcipher3` build-from-source richiede header `sqlcipher/sqlite3.h` di sistema.
- `sqlcipher3-binary` ultimo wheel supporta solo Python ≤ 3.11. Python 3.12 non disponibile.
- Cliente enterprise può comunque richiedere encryption DB-level per compliance (es. ISO 27001 A.10).

Tradeoff: bloccare install MVP per pochi utenti che vogliono encryption native, o usare strato OS (LUKS/FileVault/BitLocker) sufficiente per ~80% dei deploy.

## Decision

**Default MVP:** SQLite plain + **FS-level encryption** (responsabilità OS deploy).

- macOS dev: FileVault.
- Linux server: LUKS volume montato su `storage/`.
- Windows: BitLocker.
- Docker: volume cifrato sul host.

**Optional extra `[encryption]`:**

```bash
# Pre-req sistema:
brew install sqlcipher              # macOS
apt-get install libsqlcipher-dev    # Linux

# Install:
uv sync --extra encryption
DOCHECK_DB_ENCRYPTION_ENABLED=true uv run python -m docheck.main
```

`db/session.py` carica driver SQLCipher solo se flag attivo + import lazy:

```python
if settings.db_encryption_enabled:
    import sqlcipher3  # noqa: F401  - registers SQLAlchemy dialect
    dsn = f"sqlite+sqlcipher://:{master_key}@/{db_path}"
else:
    dsn = f"sqlite+aiosqlite:///{db_path}"
```

**Audit log immutabilità:** continua a essere garantita da trigger SQLite (no-update/no-delete) + Ed25519 hash chain — non dipende da encryption.

**Audit signing key:** sempre custodita in OS keychain (macOS Keychain / Windows DPAPI / Linux secret-service via `keyring` lib) — file 0600 fallback dev.

## Consequences

**Positive**

- MVP install zero-friction su Python 3.12.
- Compliance-grade deploy ottenibile con FS encryption (riconosciuto da ISO 27001 / SOC2).
- Path encryption native pronto per cliente che la richiede esplicitamente.

**Negative**

- Default install non protegge da attaccante con FS read access.
- Documentazione deve essere chiara: FS encryption obbligatoria in prod.
- Test integration encryption on richiede setup dedicato (skippato in CI default).

## Mitigazioni

- Runbook deploy: `sudo cryptsetup luksFormat /dev/sdX` step obbligatorio pre-install.
- Helm chart: `storageClassName` con CSI encryption-at-rest (es. `aws-ebs-encrypted`).
- Settings UI mostra warning se `db_encryption_enabled=false` + FS check non rilevato.

## Alternatives Considered

- **Force `pysqlcipher3` con build deps**: blocca install Python 3.12 senza brew, friction alta.
- **Solo SQLCipher, no fallback**: scartato — incompatibile Python 3.12 wheel ecosystem oggi.
- **Postgres + TDE**: scope multi-tenant (F5), non MVP single-tenant workstation.
- **Custom AES wrapper file-level**: reinventare crypto = no-go.

## Revisione

Re-evaluate quando:

- Wheel SQLCipher supporta Python 3.12 (atteso 2026 H2).
- Cliente enterprise richiede esplicitamente DB-level encryption (attivare extra).
- Audit certification (SOC2 Type II) richiede.
