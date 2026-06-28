/** Scoped, token-driven styles for the Overview console — restrained + dense. */

export const OVERVIEW_STYLES = `
  .ov { display: flex; flex-direction: column; gap: 1.1rem; }
  .ov-loading { display: grid; place-items: center; padding: 4rem; }

  /* KPI strip — one panel, hairline-divided columns, no icon tiles */
  .ov-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    background: var(--admin-card-bg); border: 1px solid var(--admin-card-border);
    border-radius: var(--admin-radius-lg); box-shadow: var(--admin-card-shadow); overflow: hidden; }
  .ov-kpi { display: flex; flex-direction: column; gap: 0.32rem; padding: 1.05rem 1.25rem;
    border-left: 1px solid var(--admin-card-border); }
  .ov-kpi:first-child { border-left: none; }
  .ov-kpi-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em; color: var(--admin-text-subtle); }
  .ov-kpi-value { font-family: var(--admin-font-display); font-size: 1.7rem; font-weight: 700;
    line-height: 1; color: var(--admin-text); font-variant-numeric: tabular-nums; }
  .ov-kpi-sub { font-size: 0.74rem; color: var(--admin-text-muted); }

  .ov-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--admin-text-subtle); }
  .ov-dot.ok { background: var(--admin-success); }
  .ov-dot.warn { background: var(--admin-warning); }
  .ov-dot.bad { background: var(--admin-error); }

  .ov-grid { display: grid; gap: 1rem; grid-template-columns: 1.4fr 1fr; align-items: start; }
  .ov-card { padding: 1.1rem 1.25rem; }
  .ov-card-wide { grid-column: 1 / -1; }
  .ov-card-head { display: flex; align-items: baseline; justify-content: space-between;
    gap: 0.75rem; margin-bottom: 0.9rem; }
  .ov-card-head h3 { margin: 0; font-size: 0.9rem; font-weight: 650; }
  .ov-card-sub { font-size: 0.76rem; color: var(--admin-text-muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
  .ov-area { display: block; }
  .ov-axis { display: flex; justify-content: space-between; margin-top: 0.45rem;
    font-size: 0.68rem; color: var(--admin-text-subtle); font-family: var(--admin-font-mono); }

  /* thin solid meter */
  .ov-meter { display: block; width: 100%; height: 6px; border-radius: 9999px;
    background: var(--admin-surface-2); overflow: hidden; }
  .ov-meter-fill { display: block; height: 100%; border-radius: 9999px; background: var(--admin-accent); }
  .ov-meter-fill.tone-success { background: var(--admin-success); }
  .ov-meter-fill.tone-warning { background: var(--admin-warning); }
  .ov-meter-fill.tone-danger { background: var(--admin-error); }

  /* posture list */
  .ov-posture { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
  .ov-posture li { display: flex; align-items: center; gap: 0.75rem; padding: 0.62rem 0;
    border-top: 1px solid var(--admin-table-border); }
  .ov-posture li:first-child { border-top: none; }
  .ov-posture-label { display: flex; align-items: center; gap: 0.5rem; flex: 1;
    font-size: 0.85rem; color: var(--admin-text); }
  .ov-posture-meter { width: 108px; flex-shrink: 0; }
  .ov-posture-val { font-size: 0.85rem; font-weight: 600; color: var(--admin-text);
    font-variant-numeric: tabular-nums; min-width: 2.5ch; text-align: right; }

  /* compact data rows (roles / usage) */
  .ov-rows { display: flex; flex-direction: column; }
  .ov-row { display: grid; grid-template-columns: minmax(88px, 1fr) 1fr auto auto; align-items: center;
    gap: 0.7rem; padding: 0.5rem 0; border-top: 1px solid var(--admin-table-border); }
  .ov-row.ov-row-usage { grid-template-columns: minmax(120px, 1.4fr) 1fr auto; }
  .ov-row:first-child { border-top: none; }
  .ov-row-name { font-size: 0.83rem; color: var(--admin-text); overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; }
  .ov-row-meter { min-width: 56px; }
  .ov-row-val { font-size: 0.82rem; font-weight: 600; color: var(--admin-text);
    font-variant-numeric: tabular-nums; text-align: right; }
  .ov-row-pct { font-size: 0.76rem; color: var(--admin-text-subtle);
    font-variant-numeric: tabular-nums; width: 38px; text-align: right; }

  /* recent log */
  .ov-recent-list { list-style: none; margin: 0; padding: 0; }
  .ov-recent-list li { display: grid; grid-template-columns: 1fr auto auto; align-items: center;
    gap: 0.75rem; padding: 0.5rem 0; border-top: 1px solid var(--admin-table-border); }
  .ov-recent-list li:first-child { border-top: none; }
  .ov-recent-action { font-size: 0.82rem; font-weight: 500; color: var(--admin-text); font-family: var(--admin-font-mono); }
  .ov-recent-meta { font-size: 0.76rem; color: var(--admin-text-muted); }
  .ov-recent-time { font-size: 0.74rem; color: var(--admin-text-subtle); white-space: nowrap; font-variant-numeric: tabular-nums; }
  .ov-empty { font-size: 0.82rem; color: var(--admin-text-subtle); padding: 0.5rem 0; }

  @media (max-width: 900px) { .ov-grid { grid-template-columns: 1fr; } }
`;
