# Red Agent — UI Schema (Cyber-Modern Dark Mode)

Standalone React 18 + Vite SPA, mounted at `/red-agent/ui`. Built with
`npm run build` into `ui/dist/` (mirrors the `baselithbot` packaging
pattern). The UI is plugin-scoped: it never imports from another
plugin's UI bundle.

## Tech stack

| Layer            | Choice                                                  |
| ---------------- | ------------------------------------------------------- |
| Framework        | React 18 + TypeScript + Vite                            |
| State            | Zustand (UI), TanStack Query (server cache + WebSocket) |
| Auth             | JWT bearer from `plugins/auth` (refresh-cookie aware)   |
| Theme            | Tailwind CSS + custom design tokens (see below)         |
| Graph view       | Cytoscape.js (compound nodes, fcose layout)             |
| Charts           | ECharts (heatmap, severity timeline)                    |
| Realtime         | Native WebSocket → `/red-agent/ws/scans/{id}`           |
| Routing          | React Router 6                                          |
| Tables / virtual | TanStack Table + react-virtuoso                         |

## Design tokens

```css
--bg-base:      #0a0e14;  /* deep cyan-black */
--bg-elevated:  #11161f;
--bg-overlay:   #161c27;
--surface-line: #1f2937;
--text-primary: #e5f1ff;
--text-muted:   #6b7a90;
--accent-neon:  #00ffd1;  /* primary highlights */
--accent-warn:  #ffb000;
--accent-fail:  #ff3860;
--accent-info:  #4cc9f0;
--severity-info:     #4cc9f0;
--severity-low:      #2dd4bf;
--severity-medium:   #ffb000;
--severity-high:     #ff7a18;
--severity-critical: #ff3860;
--font-display: "JetBrains Mono Variable", ui-monospace;
--font-body:    "Inter Variable", system-ui;
--radius-md:    8px;
--shadow-glow:  0 0 24px rgba(0,255,209,0.18);
```

Visual rules: monochrome base + neon accents only on actionable state;
glow effect reserved for critical/active scans; reduced motion via
`prefers-reduced-motion`.

## Layout

```text
┌────────────────────────────────────────────────────────────────┐
│  Topbar: tenant switch · target search · profile · notifications│
├──────────────┬─────────────────────────────────────────────────┤
│ Left rail    │  Main canvas                                    │
│  · Dashboard │                                                 │
│  · Scans     │                                                 │
│  · Findings  │                                                 │
│  · Graph     │                                                 │
│  · Reports   │                                                 │
│  · Settings  │                                                 │
└──────────────┴─────────────────────────────────────────────────┘
```

## Routes / views

| Route                          | View                  | Purpose                                                        |
| ------------------------------ | --------------------- | -------------------------------------------------------------- |
| `/`                            | DashboardOverview     | KPI tiles, severity heatmap, latest scans timeline             |
| `/scans`                       | ScansList             | Virtualized table of scans with filters + status pills         |
| `/scans/new`                   | ScanWizard            | 3-step wizard: target → scope check → scanner selection        |
| `/scans/:id`                   | ScanDetail            | Live progress, per-scanner panel, finding stream, raw logs     |
| `/findings`                    | FindingsExplorer      | Faceted search (severity, CWE, scanner, target)                |
| `/findings/:id`                | FindingDetail         | Evidence, payload, remediation, replay-in-sandbox button       |
| `/graph`                       | AttackSurfaceGraph    | Cytoscape canvas: Target↔Endpoint↔Service↔Vulnerability        |
| `/reports`                     | ReportsHub            | SARIF / PDF / CSV export, retention policy                     |
| `/settings/scope`              | ScopePolicyEditor     | Allowlist domains/CIDRs, bug-bounty programs                   |
| `/settings/integrations`       | IntegrationsPanel     | Auth plugin RBAC mapping, FalkorDB, sandbox provider           |

## Component tree (essentials)

```jsx
<App>
  <ThemeProvider tokens="cyber-dark">
    <AuthGate role="security_operator|viewer">
      <AppShell>
        <Topbar />
        <SideNav />
        <Routes>
          <DashboardOverview>
            <KpiTile metric="open_critical" />
            <KpiTile metric="scans_24h" />
            <SeverityHeatmap />
            <ScanTimeline />
            <RecentFindingsFeed />
          </DashboardOverview>
          <ScansList />
          <ScanWizard>
            <Step.Target />
            <Step.ScopeCheck />     // calls /red-agent/guardrails/preflight
            <Step.Scanners />
            <Step.IntensityHITL />  // shows HITL warning if active/intrusive
          </ScanWizard>
          <ScanDetail>
            <ScanHeader />
            <LiveProgress wsChannel="scan:{id}" />
            <ScannerLane name="nmap" />
            <ScannerLane name="nuclei" />
            <ScannerLane name="zap" />
            <FindingsStream />
          </ScanDetail>
          <AttackSurfaceGraph>
            <CytoscapeCanvas
              nodeShapes={{ Target: hexagon, Service: diamond,
                            Endpoint: round-rect, Vulnerability: octagon }}
              edgeStyles={{ HAS_VULN: neon-fail, EXPOSES: neon-info }}
              layout="fcose"
            />
            <NodeInspector />
            <SeverityFilterRail />
          </AttackSurfaceGraph>
        </Routes>
      </AppShell>
    </AuthGate>
  </ThemeProvider>
</App>
```

## Cytoscape graph styling (excerpt)

```js
{
  selector: 'node[label="Vulnerability"][severity="critical"]',
  style: {
    'background-color': 'var(--severity-critical)',
    'border-color':     'var(--accent-fail)',
    'box-shadow':       'var(--shadow-glow)',
    'shape':            'octagon',
  },
},
{
  selector: 'edge[type="HAS_VULN"]',
  style: {
    'line-color':       'var(--severity-high)',
    'curve-style':      'bezier',
    'target-arrow-shape':'triangle',
  },
},
```

## Realtime contract

WebSocket frame:

```json
{ "type": "finding", "scan_id": "<uuid>", "finding": { ... } }
{ "type": "status",  "scan_id": "<uuid>", "status": "running|completed|failed" }
{ "type": "log",     "scan_id": "<uuid>", "scanner": "nmap", "line": "..." }
```

## Accessibility

- Full keyboard navigation; visible focus rings on neon accent.
- WCAG AA contrast minimum on all text/severity badges.
- Reduced-motion fallback disables glow + cytoscape animations.
- All severity also encoded with shape + label, never color alone.
