# 3. Schema UI/UX

Layout 60/40 split asimmetrico. Dark mode default `#09090B`. Componenti shadcn/ui custom-themed.

## 3.1 Layout Principale (Analysis Workspace)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Logo] doCheck   ●Llama-3.3 Ready   [Policies ▼]   [User Menu ▼]    │ ← TopBar 56px
├──────────────────────────────────────┬───────────────────────────────┤
│ DOCUMENT VIEWER (60%)                │ FINDINGS PANEL (40%)          │
│                                      │                               │
│  📄 contratto_fornitore_v3.pdf       │ ┌─ Summary Card ────────────┐ │
│  Pages: 24 · Chunks: 187             │ │ ❌ 3 FAIL · ⚠ 5 · ✅ 42   │ │
│                                      │ │ Score: 78/100             │ │
│  ┌──────────────────────────────┐    │ └───────────────────────────┘ │
│  │ Art. 7 — Recesso             │    │                               │
│  │ ▓▓▓▓▓ highlighted ambra ▓▓▓▓ │◄───┤ ▼ FAIL · GDPR-Art-13          │
│  │ Lorem ipsum dolor sit amet   │    │   Riga 142-145                │
│  │ consectetur adipiscing...    │    │   Missing data retention      │
│  │                              │    │   ┌─ Policy Ref [+] ───────┐  │
│  │ ▓▓▓▓▓ highlighted rosso ▓▓▓▓ │    │   │ "Il titolare informa…" │  │
│  └──────────────────────────────┘    │   └────────────────────────┘  │
│                                      │   [Ask AI] [Suggest Fix]      │
│  [◄ Prev] [Page 7/24] [Next ►]       │                               │
│                                      │ ▶ WARN · Branding-Footer      │
│                                      │ ▶ PASS · NDA-Clause-3.1       │
│                                      │                               │
│                                      │ ─────────────────────────     │
│                                      │ [📥 Export Signed Report]     │
└──────────────────────────────────────┴───────────────────────────────┘
```

## 3.2 TopBar

- Logo + nome prodotto (sinistra)
- Model status pill: `● Llama-3.3 Ready` (verde) / `◐ Loading` (ambra) / `○ Offline` (rosso)
- Policy multiselect button con counter (`Policies · 4 active`)
- User avatar + dropdown (Profile, Audit, Logout)

## 3.3 Document Viewer (60%)

- Toolbar 40px: zoom, page nav, search, toggle structure tree
- Canvas PDF render via `pdf.js` con overlay SVG per highlight bbox
- Sidebar collapsibile 200px structure tree (nested articoli/clausole)
- Highlight overlay opacità 15%:
  - FAIL: `rgba(239,68,68,0.15)` rosso
  - WARN: `rgba(245,158,11,0.18)` ambra
  - INFO: `rgba(59,130,246,0.15)` blu

## 3.4 Findings Panel (40%)

- Sticky header: Summary card (score gauge, counts severity)
- Filter chips: All / FAIL / WARN / PASS / By policy
- Virtual list findings (`react-virtuoso`). Card 96px collapsed → 240px expanded
- Footer sticky: `Export Signed Report` primary button

## 3.5 Finding Card

```
┌──────────────────────────────────────────────────┐
│ [●FAIL]  GDPR-Art-13           Riga 142–145  ⓘ  │ ← header 32px
│ Manca clausola retention dati personali           │ ← title 18px semibold
│ Confidence 92% · IT_GDPR_2026@v3                  │ ← meta 12px muted
│ ─────────────────────────────────────────────    │
│ ▾ Policy reference                                │ ← collapsible
│   "Il titolare informa l'interessato del periodo │
│    di conservazione…"                             │ ← mono 12px box bg-elev
│ ─────────────────────────────────────────────    │
│ 💡 Suggestion: aggiungi clausola conservazione   │
│ [View in document] [Ask AI] [Mark reviewed]       │ ← actions ghost
└──────────────────────────────────────────────────┘
```

- Border-left 3px color severity
- Hover: `bg-panel-elev`
- Click: scroll viewer + outline strong evidence

## 3.6 Interazioni Chiave

- **Click finding → scroll+highlight** — pannello sinistro auto-scroll al `bbox`. Animazione 200ms ease-out.
- **Reverse-link** — click su paragrafo evidenziato → filter findings panel su quel chunk.
- **Reasoning Drawer** — pulsante 🔍 per finding apre drawer destro 420px con `trace` agente step-by-step (tool calls, retrieval results, LLM thoughts).
- **Policy Panel (modal 960×640)** — tab `Default IT` (preselected) | `EU` | `World` | `Custom`.
- **Streaming UX** — WebSocket alimenta findings progressivamente. Skeleton shimmer + counter live.

## 3.7 Stati Semantici (Badge)

- `Success #10B981` (Conforme)
- `Warning #F59E0B` (Da verificare)
- `Danger #EF4444` (Violazione)
- `Info #3B82F6` (Citazione)

Icone Lucide: `CheckCircle2`, `AlertTriangle`, `XCircle`, `Info`.

## 3.8 Tipografia

- Body UI: `Inter` 14px
- Estratti policy / codice: `JetBrains Mono` 12px
- Density medium, line-height 1.5

## 3.9 Accessibilità (WCAG AA)

- Contrast ratio verificato (text/secondary su bg/panel = 5.2:1).
- Focus ring sempre visibile: `outline: 2px solid #3B82F6; offset: 2px`.
- ARIA: findings list `role="list"`, finding card `role="listitem"` + `aria-expanded`.
- Drawer `role="dialog"` con focus trap.
- Keyboard shortcuts: `J/K` nav findings, `Enter` espandi, `V` view in document, `Esc` chiudi drawer.
- Screen reader: severity announce `aria-label="Violazione critica, GDPR articolo 13, riga 142"`.

## 3.10 Empty / Loading / Error States

- **Empty findings:** illustrazione minimale, copy "Nessuna violazione rilevata. Documento conforme alle policy selezionate."
- **Loading streaming:** skeleton cards + counter live "Analisi in corso · 14/187 chunk".
- **Error:** panel rosso soft, retry CTA, link audit log.

## 3.11 Schermate Secondarie

- **Dashboard / Recent Documents** — hero dropzone + grid recent docs (3 col).
- **Policy Manager Modal** — tabs scope, tabella import, preview rule mono.
- **Audit Log Viewer** (Admin/DPO) — filtri user/action/date, riga corrotta evidenziata, button `Verify chain integrity`.
- **Settings** — model config, retention TTL, OCR engine, theme, lingua UI.
