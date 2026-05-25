# ADR-0002: SQLCipher + Ed25519 Hash-Chained Audit Log

**Status:** Accepted
**Date:** 2026-05-03

## Context

Audit trail enterprise richiede:

- Immutabilità (no tampering retroattivo).
- Non-ripudio firme.
- Verificabilità integrità chain end-to-end.
- Compatibilità local-first (no servizi cloud-based).

## Decision

- Persistenza in **SQLCipher** (SQLite con cifratura AES-256, KDF PBKDF2-HMAC-SHA512).
- Master key custodita in OS keychain (macOS Keychain / Windows DPAPI / Linux secret-service).
- Tabella `audit_log` con trigger `BEFORE UPDATE/DELETE` → `RAISE FAIL`.
- Ogni record include: `prev_hash`, `entry_hash = SHA256(prev_hash || canonical(row))`, `signature = Ed25519(entry_hash)`.
- Public verifying key esposto via `/api/v1/info/pubkey` per validazione esterna.

## Consequences

**Positive**

- Tampering rilevabile (job giornaliero ricalcola chain).
- Firma Ed25519 fast (64-byte signatures), curve25519 production-grade.
- Zero dipendenza esterna runtime.

**Negative**

- pysqlcipher3 build native richiede `libsqlcipher-dev`.
- Master key recovery → richiede backup mnemonic durante setup wizard.

## Alternatives Considered

- **Postgres + pgcrypto**: violerebbe local-first MVP. Path multi-tenant futuro.
- **Append-only log file (jsonl)**: meno query-friendly, no FK integrity con altre tabelle.
- **HMAC chain**: simmetrica → no non-ripudio. Scartato.
