# 9. Wireframe Spec Figma-Ready

Specifica handoff diretta a designer/frontend. Token-driven (vedi `08_design_tokens.yaml`), mappa 1:1 a shadcn/ui.

## 9.1 Frame Inventory

| Frame | Nome | Dimensione | Stato |
|-------|------|-----------|-------|
| F1 | Dashboard / Recent Documents | 1440×900 | MVP |
| F2 | Analysis Workspace (primaria) | 1440×900 | MVP |
| F3 | Finding Card (component) | 480×varies | MVP |
| F4 | Policy Manager Modal | 960×640 | MVP |
| F5 | Reasoning Drawer (Glass Box) | 420×900 | MVP |
| F6 | Audit Log Viewer (admin/DPO) | 1440×900 | MVP |
| F7 | Empty / Loading / Error States | 1440×900 | MVP |
| F8 | Settings | 1440×900 | MVP |
| F9 | Onboarding Wizard | 720×560 modal | MVP |

---

## F1 — Dashboard / Recent Documents

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Logo] doCheck   ●Llama-3.3 Ready   [Policies ▼]   [User Menu ▼]    │
├────┬─────────────────────────────────────────────────────────────────┤
│ 🏠 │                                                                 │
│ 📄 │   ┌──────────────────────────────────────────────────────┐      │
│ 📋 │   │       ⬆ Drop your document or click to upload          │      │
│ 📊 │   │       PDF · DOCX · XLSX · MD   (max 50MB)              │      │
│ ⚙  │   └──────────────────────────────────────────────────────┘      │
│    │                                                                 │
│    │   Recent Documents                                              │
│    │   ┌───────┐  ┌───────┐  ┌───────┐                              │
│    │   │ doc1  │  │ doc2  │  │ doc3  │     (cards 280×160)           │
│    │   │ 78/100│  │ 92/100│  │ 45/100│                              │
│    │   │ ❌3⚠5│  │ ✅50  │  │ ❌12⚠4│                              │
│    │   └───────┘  └───────┘  └───────┘                              │
└────┴─────────────────────────────────────────────────────────────────┘
```

- TopBar 56px
- Sidebar nav 56px collapsed (icons): Home, Documents, Policies, Audit, Settings
- Hero dropzone full-width 240px high, dashed border `border/strong`, hover state highlight `info`
- Grid recent docs 3 col, gap 16px, card 280×160:
  - Header: filename mono, ts relative
  - Center: ScoreGauge circolare 80px
  - Footer: badge severity counts

---

## F2 — Analysis Workspace (PRIMARIA)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Logo] doCheck  ●Llama-3.3 Ready  [Policies ▼ 4]  [User Menu ▼]     │ ← TopBar 56px
├──────────────────────────────────────┬───────────────────────────────┤
│ DOCUMENT VIEWER (60%)                │ FINDINGS PANEL (40%)          │
│ ┌─Toolbar 40px─────────────────────┐ │ ┌─ Summary ─────────────────┐ │
│ │ 🔍 [▣ Tree] ⊖⊕ Page 7/24 [Find]  │ │ │  Score: 78/100  [gauge]   │ │
│ └──────────────────────────────────┘ │ │  ❌3 FAIL · ⚠5 · ✅42     │ │
│ ┌──Tree──┬──Canvas pdf.js──────────┐ │ └───────────────────────────┘ │
│ │ Title  │                         │ │ [All|FAIL|WARN|PASS|Policy▼] │
│ │ ▾Art.7 │   Art. 7 — Recesso     │ │ ┌─Finding Card ▼ ──────────┐  │
│ │  ▾7.1  │   ▓▓▓highlighted ambra │◄├─│ ●FAIL GDPR-Art-13         │  │
│ │  ▾7.2  │   Lorem ipsum...       │ │ │ Riga 142-145              │  │
│ │ ▸Art.8 │                         │ │ │ ▾ Policy Ref              │  │
│ │ ▸Art.9 │   ▓▓▓highlighted rosso │ │ │   "Il titolare informa…"  │  │
│ │        │   Dolor sit amet...    │ │ │ [View] [Ask AI] [Mark]    │  │
│ │        │                         │ │ └───────────────────────────┘  │
│ │        │ [◄] [7/24] [►]         │ │ ┌─Finding Card ▶ ──────────┐  │
│ └────────┴─────────────────────────┘ │ │ ●WARN Branding-Footer    │  │
│                                      │ └───────────────────────────┘  │
│                                      │ ┌─Finding Card ▶ ──────────┐  │
│                                      │ │ ●PASS NDA-Clause-3.1     │  │
│                                      │ └───────────────────────────┘  │
│                                      │ ─────────────────────────────  │
│                                      │ [📥 Export Signed Report]      │
└──────────────────────────────────────┴───────────────────────────────┘
```

**Componenti:**
- Resizable split (60/40 default), min 40% / max 80% per pane
- Document Viewer:
  - Toolbar 40px: zoom, page nav, search, toggle structure tree, toggle annotations
  - Sidebar tree 200px collapsibile
  - Canvas pdf.js + SVG overlay highlight bbox
  - Highlight on click finding: fade-in 200ms, soft pulse 1x
- Findings Panel:
  - Sticky header con Summary card
  - Filter chips height 28px, gap 6px
  - Virtual list (`react-virtuoso`)
  - Sticky footer con Export button primary

---

## F3 — Finding Card (component spec)

```
┌──────────────────────────────────────────────────┐ ← border-left 3px severity
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

**Variants:**
- Severity: `fail` | `warn` | `pass` | `info`
- State: `default` | `hover` (bg `panel_elev`) | `expanded` | `selected` (outline `info` 2px)
- Density: `compact` (96px) | `expanded` (240-320px)

---

## F4 — Policy Manager Modal (960×640)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Policy Manager                                              [✕]      │
├──────────────────────────────────────────────────────────────────────┤
│  [Default IT (preset)] [EU] [World] [Custom]    [+ Import Policy]    │
├──────────────────────────────────────────────────────────────────────┤
│  ☑ │ id                  │ title                   │ ver  │ updated  │
│  ☑ │ IT_GDPR_2026        │ GDPR Italia             │ v3.0 │ 2026-04  │
│  ☑ │ IT_Codice_Civile    │ Codice Civile Contratti │ v1.2 │ 2026-03  │
│  ☐ │ EU_AI_Act_2024      │ EU AI Act               │ v1.0 │ 2026-01  │
│  ┌─Preview rule─────────────────────────────────────────────────────┐ │
│  │ GDPR-Art-13 · severity=FAIL                                      │ │
│  │ "Il titolare informa l'interessato del periodo di…"              │ │
│  └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│                                              [Cancel] [Save selection]│
└──────────────────────────────────────────────────────────────────────┘
```

- Tabs sticky top, default `Default IT`
- Tabella checkbox + columns sortable
- Right pane preview rule list mono font
- Footer fixed: Cancel (ghost) + Save (primary)
- Import flow: upload PDF/MD/YAML → progress indexing → toast success

---

## F5 — Reasoning Drawer (Glass Box)

```
┌──────────────────────────────────┐ ← drawer 420px right slide-in
│  ●FAIL · GDPR-Art-13      [✕]    │
├──────────────────────────────────┤
│  Reasoning Trace                  │
│                                   │
│  ◉ Step 1 · LegalComplianceAgent │
│  │  retrieve_policy("retention",  │
│  │    "IT_GDPR")                  │
│  │  → 3 hits: [GDPR-Art-13,       │
│  │     GDPR-Art-5, GDPR-Art-30]   │
│  │                                │
│  ◉ Step 2 · thought               │
│  │  "chunk c-42 mentions purpose  │
│  │   but not retention period"   │
│  │                                │
│  ◉ Step 3 · check_clause_presence │
│  │  ("data_retention")            │
│  │  → present: false              │
│  │                                │
│  ◉ Step 4 · verdict               │
│      severity=FAIL conf=0.92      │
│                                   │
├──────────────────────────────────┤
│  [Copy JSON] [Export trace]       │
└──────────────────────────────────┘
```

- Slide-in da destra animation 320ms
- Timeline verticale steps con marker icona
- Tool calls espandibili (chip click → expand input/output)
- Thoughts in italic muted
- Footer: copy reasoning JSON, export trace markdown

---

## F6 — Audit Log Viewer (admin/DPO)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Audit Log              [Verify chain integrity]                      │
├──────────────────────────────────────────────────────────────────────┤
│ Filtri: [User ▼] [Action ▼] [Date range] [Resource search]          │
├──────────────────────────────────────────────────────────────────────┤
│ seq │ ts                  │ user        │ action       │ resource    │
│ 142 │ 2026-05-03 10:12:00 │ g.ippolito  │ analyze      │ doc:abc...  │
│ 141 │ 2026-05-03 10:11:45 │ g.ippolito  │ upload       │ doc:abc...  │
│ 140 │ 2026-05-03 09:30:00 │ admin       │ policy_act…  │ policy:...  │
│ ⚠139│ 2026-05-03 08:00:00 │ admin       │ ...          │ ...         │ ← chain break
│ ... │                                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

- Tabella append-only, paginazione 50/page
- Riga corrotta highlighted `status/danger` con icona shield-off + tooltip
- Button `Verify chain integrity` → spinner → toast result + dialog dettaglio se fail
- Export CSV/JSON (audit signed)

---

## F7 — Empty / Loading / Error States

**Empty findings:**
```
┌─────────────────────────────────────┐
│         ✓                            │
│   Nessuna violazione rilevata        │
│   Documento conforme alle policy     │
│         selezionate.                 │
└─────────────────────────────────────┘
```

**Loading streaming:**
```
┌─────────────────────────────────────┐
│  ⟳ Analisi in corso · 14/187 chunk  │
│  ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░  7%           │
│  ┌─────────────────────────────┐    │
│  │ ░░░░░░░░░░░ skeleton ░░░░░░│    │
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░│    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**Error:**
```
┌─────────────────────────────────────┐
│  ⚠ Errore durante l'analisi         │
│  Code: ENGINE_TIMEOUT                │
│  Il modello non risponde.            │
│  [Riprova] [Apri audit log]          │
└─────────────────────────────────────┘
```

---

## F8 — Settings

Tabs:
- **Engine** — model primary/fallback, temperature, max tokens
- **OCR** — engine selector (PaddleOCR default), pre-processing toggles
- **Storage** — retention TTL, vault path, encrypted volume status
- **Audit** — signing key info, chain integrity job schedule
- **Appearance** — theme (dark default), language (IT/EN)
- **About** — engine version, model versions, signature pubkey export

---

## F9 — Onboarding Wizard (primo avvio)

Steps:
1. Welcome + privacy assurance ("All processing local")
2. Model setup (download Llama-3.3-70B, progress bar, ~40GB)
3. Default policy selection (preset IT pre-checked)
4. First admin user creation (email, password argon2id)
5. Encryption key setup (generated, stored OS keychain, export backup mnemonic)
6. Done → redirect Dashboard

---

## 9.2 Componenti shadcn/ui Mapping

| Componente shadcn | Uso | Custom |
|-------------------|-----|--------|
| `Button` | CTA, actions | Variants: primary, ghost, destructive |
| `Badge` | Severity, status | Custom severity variants |
| `Card` | Findings, dashboard tiles | - |
| `Tabs` | Policy manager, settings | - |
| `Dialog` | Modal Policy Manager, confirm | - |
| `Sheet` | Reasoning Drawer | side=right, w=420 |
| `Tooltip` | Hints, ARIA | - |
| `Command` | Policy multiselect search | - |
| `ScrollArea` | Panels scroll | - |
| `Progress` | Loading streaming | indeterminate variant |
| `Toast` (sonner) | Notifications | - |
| `Resizable` (`react-resizable-panels`) | Split 60/40 | - |
| `Avatar` | User menu | - |
| `DropdownMenu` | User menu, filters | - |
| `Checkbox` | Policy selection | - |
| `Tree` (custom) | Document structure sidebar | nuovo componente |

**Componenti custom nuovi:**
- `FindingCard` — wrapper Card con severity variant
- `DocumentViewer` — wrap pdf.js + SVG overlay highlight
- `ReasoningTimeline` — vertical timeline steps
- `ScoreGauge` — SVG circular gauge
- `HighlightOverlay` — SVG bbox overlay component
- `StatusPill` — model status indicator topbar

---

## 9.3 Stati Interattivi Obbligatori (Figma variants)

Ogni componente: `default`, `hover`, `focus-visible` (ring info 2px), `active`, `disabled`, `loading`.
Severity: `pass`, `warn`, `fail`, `info`.

## 9.4 Accessibility Checklist

- Contrast AA verificato (axe-core CI gate).
- Focus ring sempre visibile.
- ARIA: `role="list"` findings, `role="listitem"` card, `aria-expanded`, drawer `role="dialog"` + focus trap.
- Keyboard shortcuts:
  - `J/K` next/prev finding
  - `Enter` espandi finding
  - `V` view in document
  - `R` toggle reasoning drawer
  - `Esc` close drawer/modal
  - `Cmd/Ctrl+K` command palette
  - `Cmd/Ctrl+E` export report
- Screen reader: severity announce `aria-label="Violazione critica, GDPR articolo 13, riga 142"`.
- Reduced motion: respect `prefers-reduced-motion` → disable highlights pulse, drawer slide.
