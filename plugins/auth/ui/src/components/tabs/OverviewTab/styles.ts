/** Scoped, token-driven styles for the Overview dashboard. */

export const OVERVIEW_STYLES = `
  .ov { display: flex; flex-direction: column; gap: 1.25rem; }
  .ov-loading { display: grid; place-items: center; padding: 4rem; }

  .ov-stats { display: grid; gap: 0.9rem; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); }
  .ov-stat { display: flex; align-items: center; gap: 0.8rem; padding: 1rem 1.1rem;
    background: var(--admin-card-bg); border: 1px solid var(--admin-card-border);
    border-radius: var(--admin-radius-lg); box-shadow: var(--admin-card-shadow); }
  .ov-stat-ico { display: grid; place-items: center; width: 40px; height: 40px; flex-shrink: 0;
    border-radius: 0.6rem; background: var(--admin-accent-soft); color: var(--admin-accent); }
  .ov-stat.tone-success .ov-stat-ico { background: hsla(150,60%,45%,0.14); color: var(--admin-success); }
  .ov-stat.tone-warning .ov-stat-ico { background: hsla(35,90%,55%,0.16); color: var(--admin-warning); }
  .ov-stat.tone-danger .ov-stat-ico { background: var(--admin-error-bg); color: var(--admin-error); }
  .ov-stat-body { display: flex; flex-direction: column; min-width: 0; }
  .ov-stat-value { font-family: var(--admin-font-display); font-size: 1.5rem; font-weight: 700;
    line-height: 1.1; color: var(--admin-text); font-variant-numeric: tabular-nums; }
  .ov-stat-label { font-size: 0.8rem; color: var(--admin-text-muted); }
  .ov-stat-hint { font-size: 0.72rem; color: var(--admin-text-subtle); margin-top: 0.1rem; }

  .ov-grid { display: grid; gap: 1rem; grid-template-columns: repeat(2, 1fr); }
  .ov-card { padding: 1.1rem 1.25rem; }
  .ov-card-wide { grid-column: 1 / -1; }
  .ov-card-head { display: flex; align-items: baseline; justify-content: space-between;
    gap: 0.75rem; margin-bottom: 0.85rem; }
  .ov-card-head h3 { margin: 0; font-size: 0.95rem; }
  .ov-card-sub { font-size: 0.78rem; color: var(--admin-text-muted); white-space: nowrap; }
  .ov-card-foot { margin: 0.6rem 0 0; font-size: 0.8rem; color: var(--admin-text-muted); text-align: center; }
  .ov-axis { display: flex; justify-content: space-between; margin-top: 0.4rem;
    font-size: 0.68rem; color: var(--admin-text-subtle); font-family: var(--admin-font-mono); }
  .ov-area { display: block; }

  .ov-bars { display: flex; flex-direction: column; gap: 0.55rem; }
  .ov-bar-row { display: grid; grid-template-columns: minmax(64px, 28%) 1fr auto; align-items: center; gap: 0.6rem; }
  .ov-bar-label { font-size: 0.8rem; color: var(--admin-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ov-bar-track { height: 8px; border-radius: 9999px; background: var(--admin-surface-2); overflow: hidden; }
  .ov-bar-fill { display: block; height: 100%; border-radius: 9999px; background: var(--admin-accent-gradient); }
  .ov-bar-val { font-size: 0.78rem; font-weight: 600; color: var(--admin-text-muted); font-variant-numeric: tabular-nums; }

  .ov-donut { position: relative; display: flex; flex-direction: column; align-items: center; }
  .ov-donut svg { display: block; }
  .ov-donut-center { position: absolute; top: 48px; left: 0; right: 0; text-align: center;
    transform: translateY(-50%); pointer-events: none; }
  .ov-donut-center strong { display: block; font-family: var(--admin-font-display);
    font-size: 1.25rem; color: var(--admin-text); }
  .ov-donut-center span { font-size: 0.64rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--admin-text-subtle); }

  .ov-recent-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
  .ov-recent-list li { display: grid; grid-template-columns: 1fr auto auto; align-items: center;
    gap: 0.75rem; padding: 0.55rem 0; border-top: 1px solid var(--admin-table-border); }
  .ov-recent-list li:first-child { border-top: none; }
  .ov-recent-action { font-size: 0.85rem; font-weight: 500; color: var(--admin-text); }
  .ov-recent-meta { font-size: 0.76rem; color: var(--admin-text-muted); }
  .ov-recent-time { font-size: 0.74rem; color: var(--admin-text-subtle); white-space: nowrap; }
  .ov-empty { font-size: 0.82rem; color: var(--admin-text-subtle); padding: 0.5rem 0; }

  @media (max-width: 820px) { .ov-grid { grid-template-columns: 1fr; } }
`;
