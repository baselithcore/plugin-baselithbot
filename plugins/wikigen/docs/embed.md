# Chat widget embeddabile

Layer additivo che permette di iniettare la chat RAG su siti terzi via
floating widget JS — alternativa all'aprire l'app standalone. Stack:
token + origin allowlist + iframe-sandbox mini-app.

## Architettura

```text
host page (https://acme.com)
  └── <script src="https://wiki.example.com/embed.js"
              data-token="emb_xxx"
              data-position="bottom-right">
        │
        ├── crea floating button (vanilla JS, ~3 KB gzip)
        └── iframe sandbox → https://wiki.example.com/embed/?token=emb_xxx
              │
              └── React mini-app (~8 KB gzip + react chunks)
                    │
                    └── fetch /api/embed/chat/stream (same-origin)
                          │
                          └── verify_token(plaintext, origin)
                                ├── token_hash match
                                ├── Origin ∈ origin_allowlist
                                └── rate-limit (embed_id, ip)
```

L'iframe gira sull'origin del wiki, quindi le fetch verso
`/api/embed/*` sono **same-origin** — niente CORS lato browser. Il
controllo "chi può embedare" sta nell'`origin_allowlist` del token:
verify_token rifiuta se l'`Origin` HTTP header non è nell'allowlist.

## Setup admin

Prerequisito: ruolo con permesso `admin.embed.manage` (seed `superuser`

+ `admin` in mig 017).

1. Login admin → `/admin/embeds`.
2. **Nuovo widget** → slug, nome, origini autorizzate (una per riga),
   colore, posizione, rate-limit.
3. Backend genera `emb_<64-hex>` (256 bit entropy), salva solo
   `sha256(token)`. **Token plaintext mostrato UNA volta sola** — copialo
   subito in un password manager.
4. Incolla snippet HTML sul sito:

   ```html
   <script src="https://wiki.example.com/embed.js"
           data-token="emb_xxx..."
           data-position="bottom-right"
           data-color="#0ea5e9"
           data-label="Chat"></script>
   ```

5. Per emergenze (token leak) → **Ruota token** dalla detail row. Il
   vecchio plaintext smette di funzionare immediatamente.

## Schema DB (mig 017)

Tabella `embeds`:

| Column                  | Note                                              |
|-------------------------|---------------------------------------------------|
| `id`                    | UUID PK                                           |
| `slug`                  | UNIQUE per tenant_id                              |
| `name`, `description`   | UX admin                                          |
| `tenant_id`             | FK tenants, scope owner                           |
| `token_hash`            | sha256 hex del plaintext (UNIQUE)                 |
| `token_prefix`          | primi 12 char plaintext (display UI)              |
| `origin_allowlist`      | TEXT[] di origini (`https://host[:port]`)         |
| `theme`                 | JSONB (primary, position, font, ...)              |
| `welcome_message`       | string opzionale mostrata al primo turno          |
| `suggested_questions`   | JSONB array di chips iniziali                     |
| `rate_limit_per_minute` | INT (per `embed_id+ip`), 0 = no limit             |
| `is_enabled`            | BOOLEAN, kill-switch senza eliminare              |
| `created_by`            | FK users (nullable, SET NULL on delete)           |
| `last_used_at`          | aggiornato best-effort dalla pubblica `/config`   |

**RLS volutamente OFF.** Vedi docstring di `alembic/versions/017_embeds.py`:
verify_token pubblico avviene prima del tenant context, RLS bloccherebbe
il SELECT. Sicurezza garantita da: token unguessable (256-bit sha256
hash), filtro `WHERE tenant_id = %s` esplicito su tutti i query admin,
origin_allowlist deny-by-default.

## Endpoint pubblici

Tutti sotto `/api/embed/*`. `EmbedCORSMiddleware` (in `auth/middleware.py`)
risponde `Access-Control-Allow-Origin: *` + preflight su questi path.
Safe perché non si usano cookies — il token va in body.

### `POST /api/embed/config`

Body: `{ "embed_token": "emb_..." }`. Risponde `{ embed_id, name, theme,
welcome_message, suggested_questions, pack, rate_limit_per_minute }`.

Errori:

+ 401: token invalido o Origin assente/non-allowlisted.
+ 503: Postgres disabilitato (setup mode).

### `POST /api/embed/chat`

Body: `{ embed_token, message, history?, limit? }`. Stateless
(nessuna conversation persistita lato server). `history` arriva dal
client (localStorage).

Risponde `{ answer, sources, hits, memories: 0 }`.

### `POST /api/embed/chat/stream`

NDJSON streaming, stesso shape del main `/api/chat/stream` ma senza
eventi `conversation` / `message_id` (no persistenza). Eventi emessi:
`agent`, `step`, `hits`, `token`, `sources`, `done`, `error`.

## Endpoint admin

Tutti sotto `/api/admin/embeds/*`. Gated `admin.embed.manage` +
`rate_limit=admin`. Filtrano per `actor.tenant_id`.

+ `GET /` → list
+ `POST /` → create (response include `embed_token` plaintext)
+ `GET /{id}` → detail
+ `PATCH /{id}` → update (name/description/origin_allowlist/theme/...)
+ `DELETE /{id}` → delete
+ `POST /{id}/rotate-token` → new plaintext, vecchio invalidato

Audit events: `embed.created`, `embed.updated`, `embed.deleted`,
`embed.token.rotated`.

## Sicurezza

1. **Token unguessable.** 256 bit entropy. `secrets.token_hex(32)` →
   sha256 storage. Plaintext mai loggato.
2. **Origin allowlist.** `verify_token(token, origin)` rifiuta:
   + origin assente,
   + origin non in allowlist,
   + allowlist vuota (deny-by-default).
3. **Rate limit.** `(embed_id, ip)` bucket. Default 30 req/min, max
   600. Usa lo stesso backend (`memory` / `redis`) del rate-limiter
   globale.
4. **No cookies, no JWT.** Embed è 100% token-in-body. `Access-Control-
   Allow-Credentials` deliberatamente unset.
5. **CSP rilassato SOLO sui path embed.** `SecurityHeadersMiddleware`
   path-aware: `/embed/*` e `/embed.js` ricevono `frame-ancestors *`;
   tutti gli altri path mantengono `frame-ancestors 'none'`.
6. **iframe sandbox.** Il widget loader imposta
   `sandbox="allow-scripts allow-same-origin allow-forms"`. NO
   `allow-popups`, NO `allow-top-navigation` — l'iframe non può
   navigare il host page.
7. **Audit append-only.** Tutte le mutation (create/update/delete/
   rotate) finiscono in `audit_events`.

## Persistenza conversazione

Lato server: nessuna. L'embed è stateless — niente record in
`conversations` / `messages`.

Lato client (iframe): `localStorage` chiave `wiki_embed_history_<prefix>`
con gli ultimi 40 turni. Reset via bottone "Reset" dell'header del
widget.

## Deployment

1. Build frontend completo:

   ```bash
   cd frontend
   npm run build
   # → dist/index.html (SPA)
   # → dist/embed/index.html (iframe mini-app)
   # → dist/embed.js (widget loader)
   ```

2. Servire il contenuto di `dist/` via reverse proxy (nginx,
   CloudFront, ...). Il loader recupera l'origin dal proprio
   `<script src>`, quindi gli URL sono auto-relativi.

3. Backend deploy: applicare mig 017 (`alembic upgrade head`).

4. Configurare nel proxy il pass-through di `/api/embed/*` al backend
   FastAPI (stesso pattern di `/api/*`).

## Limiti noti

+ **No multi-tenant cross-pack.** Un widget vive nel tenant in cui è
  stato creato; il pack RAG è quello del processo (`APP_DOMAIN`). Per
  servire pack diversi servono processi distinti.
+ **No fonti deep-link.** Le source page citate nello stream sono
  visibili come metadata ma non aperte (l'iframe non può navigare il
  host page e l'app full non è accessibile senza login).
+ **Bundle size.** Il mini-app embed pesa ~8 KB ma carica anche le
  chunk React/markdown condivise (~100 KB markdown + ~57 KB react). Per
  un widget più leggero si potrebbe forkare ulteriormente la chain
  (no markdown rendering, solo text plain).
