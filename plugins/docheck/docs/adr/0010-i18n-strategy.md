# ADR-0010: Strategia i18n (multilingua) UI con italiano default

**Status:** Accepted
**Date:** 2026-05-03

## Context

L'attuale UI Next.js (`docheck-ui/`) ha stringhe hardcoded miste IT/EN sparse nei
componenti. Il prodotto è destinato a clienti enterprise italiani: serve italiano
come lingua canonica con possibilità di switch a inglese (utenza internazionale,
demo, screenshot documentazione).

Vincoli tecnici da rispettare:

- `next.config.js` usa `output: "export"` (build statica per Electron desktop).
  Le funzionalità middleware-based di Next.js (incluso routing locale via
  middleware) **non sono compatibili** con static export.
- Glass-box: `policy_ref.excerpt` è verbatim dalla policy sorgente — **non deve
  mai passare attraverso translation layer** (vincolo CLAUDE.md §5).
- LOC budget 500/file (CLAUDE.md §1).
- Stack frontend già fissato: Next.js 15, React 19, Tailwind, shadcn/ui, Zustand,
  TanStack Query (CLAUDE.md §3).

## Decision

Adottare **`next-intl` v4** in modalità *client-only* (no `[locale]` segment, no
middleware), con locale persistito client-side.

Architettura:

1. **Catalog**: `messages/it.json` (canonico), `messages/en.json`. Struttura
   namespaced per area: `common`, `nav`, `topbar`, `audit`, `viewer`, `policy`,
   `findings`, `scan`, `settings`, `errors`.
2. **Locale store**: Zustand slice `localeSlice` con persistence localStorage
   (key `docheck.locale`). Default `it`. Hydration-safe (SSR fallback `it`).
3. **Provider**: `NextIntlClientProvider` montato in `components/providers.tsx`,
   `locale` e `messages` reattivi al locale store.
4. **Switcher**: `<LocaleSwitcher>` in `TopBar` (dropdown IT/EN).
5. **Formattazione**: `useFormatter()` per date/numeri. ICU MessageFormat per
   plurali italiani.
6. **Backend coupling**:
   - Endpoint che producono testo UI-bound emettono `i18n_key` + `i18n_params`,
     non stringhe localizzate. Frontend risolve.
   - Excerpt policy, contenuto documento, output LLM → restano lingua sorgente.
     Mai tradurre.
   - `Accept-Language` header inviato dal client per messaggi error catalog
     server-side (FastAPI exception handler con catalog IT/EN minimo).
7. **Migrazione incrementale**: pilot su `Sidebar` + `TopBar`, poi area per area.
   Stringhe non ancora migrate restano hardcoded — nessun big-bang.

## Consequences

### Positive

- Italiano come lingua canonica, allineato al target enterprise IT.
- Compatibile con `output: "export"` (no middleware required).
- Tipizzazione chiavi catalog via `next-intl` typegen (errori a compile time).
- Glass-box preservato: excerpt/reasoning passano sempre raw, mai tradotti.
- Migrazione incrementale: zero regressione su feature esistenti.

### Negative

- No URL locale-prefixed (`/it/audit` vs `/en/audit`) — accettabile per app
  desktop Electron, non SEO-bound.
- Catalog client-bundled aumenta payload (~5-10KB/locale) — mitigato namespace
  splitting on-demand se necessario.
- Locale persistence solo localStorage (no sync server-side multi-device) — MVP
  sufficiente; post-MVP aggiungere `users.locale` con sync.

### Neutral

- Backend richiede catalog parallelo per error messages — costo basso (file
  YAML/JSON), riusabile per export PDF report localizzato in futuro.

## Alternatives considered

1. **`next-intl` con `[locale]` routing + middleware**:
   incompatibile con `output: "export"`. Scartata.

2. **`react-i18next`**:
   API meno integrata con App Router/RSC, type-safety inferiore, comunità Next.js
   sta convergendo su `next-intl`. Scartata.

3. **`next-international`**:
   library più giovane, ecosistema minore, type inference comparabile a
   `next-intl` ma meno feature (formatter, plurali ICU). Scartata.

4. **Lingui (`@lingui/core`)**:
   workflow basato su macro Babel/SWC, build pipeline più invasiva, overkill per
   2 locali. Scartata.

5. **Custom hook + JSON dict**:
   minimo overhead ma reinvent della ruota: niente plurali ICU, niente
   formatter, niente type-safety. Scartata.

## Implementation notes

- Pilot files: `components/Sidebar.tsx`, `components/TopBar.tsx`.
- Catalog seed estratto dalle stringhe attualmente hardcoded.
- Test regressione: snapshot rendering con locale `it` deve corrispondere allo
  stato pre-migrazione (stesse stringhe IT/EN già presenti).
- Type-check (`pnpm type-check`) deve passare dopo ogni step di migrazione.
