# Auth & RBAC

Ported from the agent-jira FastAPI design, reimplemented in NestJS/TypeScript. The contract is intentionally narrow: bearer-token JWT for users, opaque cookie-bound refresh tokens, and a single service-to-service API key for automation.

## Roles

Two roles, hardcoded:

- **`admin`** — full access. Manages connections, users, history (bulk clear), metrics endpoint.
- **`user`** — read NL2SQL, run queries, manage own history.

Everything is JWT-protected by default. Public routes opt out with `@Public()`. Admin routes opt in with `@Roles('admin')`. The guard chain runs `ApiKeyGuard → JwtAuthGuard → RolesGuard`.

## Password hashing

`argon2id` via [`argon2`](https://www.npmjs.com/package/argon2). OWASP 2024 baseline:

| Parameter   | Value        |
| ----------- | ------------ |
| Memory cost | 19 456 KiB   |
| Time cost   | 2 iterations |
| Parallelism | 1            |

The hash format is self-describing, so re-hashing on login is automatic if parameters ever change.

No bcrypt, no PBKDF2, no SHA fallback.

## Access tokens (JWT)

- Algorithm: HS256.
- Secret: `DBVIEW_JWT_SECRET`, **required**, minimum 32 chars. App refuses to start otherwise.
- TTL: `DBVIEW_JWT_ACCESS_TTL` seconds, default `900` (15 min).
- Issuer: `dbview-api`.
- Claims: `{ sub: userId, email, role }`.
- Transport: `Authorization: Bearer <token>`.
- Storage: **in-memory only on the frontend**. No localStorage. XSS-hardened.

## Refresh tokens

- Format: 48 random bytes, base64url-encoded.
- At rest: SHA-256 hash stored in `sessions.json`. The plaintext token is never persisted server-side.
- Transport: httpOnly + `Secure` (prod) + `SameSite=Strict` cookie `dbview_refresh`, path `/api/auth`.
- TTL: `DBVIEW_JWT_REFRESH_TTL` seconds, default `2592000` (30 days).

### Rotation

Every call to `POST /api/auth/refresh`:

1. Reads the cookie.
2. Hashes the presented token and looks it up.
3. Marks the old session `revoked: true`.
4. Issues a new refresh token in the same `family_id`.
5. Returns a fresh access token and replaces the cookie.

### Replay detection

If a presented token belongs to an _already-revoked_ session in a family, the entire family is revoked. The user is logged out everywhere, has to re-authenticate. This counters refresh-token theft.

The event is recorded as `dbview_auth_events_total{event="token_replay"}`.

## Service-to-service API key

`DBVIEW_API_KEY` (optional). When set, the `ApiKeyGuard` runs first.

- Header: `X-API-Key`.
- Comparison: `crypto.timingSafeEqual()` to prevent timing oracles.
- On match: injects a synthetic admin principal `{ id: 'service', email: 'service@dbview.local', role: 'admin', source: 'api-key' }`. JWT guard short-circuits, so subsequent guards see an admin.
- Cannot be deleted via the users API.

Use for Prometheus scrapes (`/api/metrics`), CI smoke tests, cron jobs. Don't ship it to browsers.

## Bootstrap admin

Runs in `AuthService.onModuleInit()` if `users.json` is empty:

- If `DBVIEW_ADMIN_EMAIL` and `DBVIEW_ADMIN_PASSWORD` are set (password ≥12 chars), creates admin with those credentials.
- Otherwise generates a random 18-byte base64url password, prints it once to the log, and flags the user `mustChangePassword: true`. Login is rejected until rotated.

Default email: `admin@dbview.local`.

## Registration

Invite-only by default. Admin creates users via `POST /api/auth/users`.

Self-signup can be enabled via `DBVIEW_ALLOW_REGISTRATION=true`. The login page reads `GET /api/auth/config` to know whether to show the signup tab.

## Sessions storage

`sessions.json` (mode `0600`, atomic write):

```ts
{
  version: 1,
  sessions: [
    {
      id: string,              // session UUID
      familyId: string,        // rotation chain identifier
      userId: string,
      tokenHashSha256: string, // hex digest of the refresh token
      expiresAt: number,       // epoch ms
      revoked: boolean,
      createdAt: number,
      lastUsedAt: number,
    }
  ]
}
```

Sessions are reloaded on startup. Expired ones are pruned lazily on touch.

## Rate limits (recap)

| Endpoint             | Limit         |
| -------------------- | ------------- |
| `/api/auth/login`    | 5 / 60s / IP  |
| `/api/auth/register` | 5 / 60s / IP  |
| `/api/auth/refresh`  | 30 / 60s / IP |

Failed login attempts are logged at info level with the IP and email; brute-force protection beyond rate limits is left to upstream WAFs.

## Environment summary

| Variable                    | Required | Default              | Notes                 |
| --------------------------- | -------- | -------------------- | --------------------- |
| `DBVIEW_JWT_SECRET`         | ✅       | —                    | ≥32 chars             |
| `DBVIEW_JWT_ACCESS_TTL`     |          | `900`                | seconds               |
| `DBVIEW_JWT_REFRESH_TTL`    |          | `2592000`            | seconds               |
| `DBVIEW_ADMIN_EMAIL`        |          | `admin@dbview.local` |                       |
| `DBVIEW_ADMIN_PASSWORD`     |          | random + must-change | ≥12 chars if supplied |
| `DBVIEW_ALLOW_REGISTRATION` |          | `false`              |                       |
| `DBVIEW_API_KEY`            |          | —                    | service principal     |
