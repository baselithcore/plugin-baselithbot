# ADR-0003: MVP Auth — Token = User ID

**Status:** Accepted (MVP only — supersede in F4)
**Date:** 2026-05-03

## Context

MVP target = workstation singola. RBAC enforcement comunque richiesto per:
- Validare flusso permission matrix end-to-end.
- Auditare azioni con `principal.user_id` reale (non "system").
- Predisporre swap a OIDC senza refactor route signatures.

## Decision

- Login endpoint `POST /auth/login` con email + password (argon2id).
- Risposta include `token` opaco — MVP equivale a `user_id`.
- Header `X-User-Id: <token>` su ogni request.
- `current_principal` dependency risolve user dal DB e calcola roles.
- `require(resource, action)` enforcer RBAC.

## Consequences

**Positive**
- Flusso completo (login → permission check → audit con user reale) testabile subito.
- Refactor a JWT/OIDC = swap solo `current_principal` impl.
- Nessuna sessione persistita server-side (stateless).

**Negative**
- Token = user_id → no scadenza, no revoca puntuale (logout client-side only).
- Nessuna protezione replay.
- Vulnerabilità se header logged in chiaro.

**Mitigazioni MVP**
- Trasporto solo Unix socket o loopback TCP.
- Audit log ogni login (timestamp, email).
- Migrazione obbligatoria a JWT firmato Ed25519 entro F4 hardening.

## Alternatives Considered

- **JWT firmato fin da MVP**: overhead implementativo, no benefit reale workstation singola.
- **Session cookie**: richiede CSRF protection extra, complicazioni Electron.
- **mTLS workstation**: overkill MVP single-user.
