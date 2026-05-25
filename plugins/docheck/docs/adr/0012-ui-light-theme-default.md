# ADR-0012: UI light theme as default, with dark + system toggle

**Status:** Accepted
**Date:** 2026-05-14

## Context

The doCheck UI shipped dark-only. Stakeholder review and accessibility
considerations (long-form document reading, side-by-side with PDF/Office
viewers, daylight office environments, prevailing enterprise convention) push
toward a light theme as the primary look. Dark must remain available — both
because some users prefer it and because the existing palette is well-tuned.

Implementation must:

- Avoid FOUC: the theme class must be set on `<html>` before first paint.
- Preserve all alpha utilities used across the codebase (`bg-status-info/10`,
  `border-status-success/40`, etc. — ~80 distinct alpha tokens).
- Not require a new runtime dependency.
- Keep semantic tokens (`bg-canvas`, `text-primary`, …) — no component-level
  fork between themes.

## Decision

1. **CSS variables as the single source of truth.** Every Tailwind color token
   resolves to `rgb(var(--name) / <alpha-value>)`. Two cascading scopes:
   - `:root` defines the **light** palette (default).
   - `.dark` overrides with the existing dark palette.
2. **Manual class-toggling** on `<html>` via a tiny module (`lib/theme.ts`).
   No `next-themes`. Storage in `localStorage["docheck-theme"]`. Supports
   `light | dark | system`.
3. **No-FOUC init script** injected in `<head>` reads localStorage and applies
   the class synchronously before the React tree mounts. Default = `light` if
   no preference stored. Content is a static module constant.
4. **Theme toggle UI** lives in `TopBar` (`ThemeToggle.tsx`) with
   Sun/Moon/Monitor icons. Sonner Toaster reads the resolved theme via the
   same hook.
5. **Document "paper" surfaces** (`PageView`) intentionally stay light in both
   themes — documents look like paper regardless of UI chrome.

## Consequences

**Positive**

- Adding/changing themes is a single-file edit (`app/globals.css`).
- All ~80 alpha utilities keep working — `rgb(var(--token) / <alpha>)` is
  opacity-preserving.
- Zero new dependencies.
- SSR-safe: server renders with no theme class, inline script sets it before
  paint, React hydrates with `suppressHydrationWarning` on `<html>`.

**Negative**

- A small inline script in `<head>` (static, no user input).
- Two color sets to maintain in lockstep. Drift mitigated by keeping them
  adjacent in `globals.css` with identical token names.

## Alternatives considered

- **`next-themes`** — adds a runtime dep and an extra provider for a problem
  solved in ~80 lines. Rejected.
- **Theme via Zustand store + effect** — works at runtime but causes FOUC
  because the class is applied after first paint. Rejected.
- **Per-component conditional classes (`dark:` only)** — would force the UI
  to be dark-by-default. Inverts the requirement. Rejected.
- **System-pref default** — would surprise enterprise users who expect light
  during work hours. Available as an explicit choice instead.

## Files touched

- `docheck-ui/tailwind.config.ts` — tokens via `rgb(var(--*) / <alpha-value>)`.
- `docheck-ui/app/globals.css` — `:root` (light) + `.dark` palettes; utility
  classes (`surface-elev`, `skeleton`, `gradient-border`, `kbd`, …) rewritten
  to consume vars.
- `docheck-ui/app/layout.tsx` — drop hardcoded `dark` class; inject init
  script.
- `docheck-ui/lib/theme.ts` — `useTheme()`, persistence, init script constant.
- `docheck-ui/components/ThemeToggle.tsx` — toggle menu.
- `docheck-ui/components/TopBar.tsx` — mount toggle.
- `docheck-ui/components/providers.tsx` — Toaster follows resolved theme.
- `docheck-ui/components/ui/ScoreGauge.tsx` — SVG strokes/text via vars.
