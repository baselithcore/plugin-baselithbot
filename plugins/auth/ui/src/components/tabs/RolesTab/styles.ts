/** Scoped styles for the Roles screen (kept out of the components for LOC). */

export const ROLES_STYLES = `
  .roles-tab { display: flex; flex-direction: column; gap: 1.25rem; padding-bottom: 4.5rem; }
  .role-create { display: flex; gap: 0.5rem; flex-wrap: wrap; padding: 1rem; align-items: center; }
  .role-create .admin-select { min-width: 180px; }
  .roles-grid { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; align-items: start; }
  .roles-list { display: flex; flex-direction: column; gap: 0.5rem; }
  .role-item { text-align: left; padding: 0.75rem; border-radius: 0.5rem;
    background: var(--admin-surface, hsla(220,25%,15%,0.5)); border: 1px solid transparent;
    cursor: pointer; display: flex; flex-direction: column; gap: 0.25rem; color: var(--admin-text); }
  .role-item.active { border-color: var(--admin-accent); }
  .role-item-main { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
  .role-item-name { font-weight: 600; }
  .role-item-meta { font-size: 0.75rem; color: var(--admin-text-muted); }
  .role-badge { font-size: 0.65rem; padding: 0.1rem 0.4rem; border-radius: 9999px; text-transform: uppercase; }
  .role-badge.sys { background: var(--admin-violet-soft); color: var(--admin-violet); }
  .role-badge.custom { background: hsla(200,80%,50%,0.18); color: var(--admin-accent); }
  .role-detail { padding: 1.25rem; }
  .role-detail-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .role-detail-head h3 { margin: 0 0 0.25rem; }
  .role-slug { font-size: 0.75rem; color: var(--admin-text-muted); }
  .role-wildcard { color: var(--admin-success); font-weight: 500; }
  .perm-groups { display: flex; flex-direction: column; gap: 0.75rem; }
  .perm-group { border: 1px solid var(--admin-border, hsla(220,25%,40%,0.25)); border-radius: 0.6rem; overflow: hidden; }
  .perm-group-head { display: flex; align-items: center; gap: 0.6rem; width: 100%;
    padding: 0.6rem 0.75rem; background: var(--admin-surface-2); cursor: pointer;
    border: none; color: var(--admin-text); text-align: left; }
  .perm-group-head:hover { background: var(--admin-border); }
  .perm-group-title { display: flex; flex-direction: column; gap: 0.1rem; flex: 1; }
  .perm-group-title strong { font-size: 0.85rem; }
  .perm-group-title span { font-size: 0.72rem; color: var(--admin-text-muted); }
  .perm-group-count { font-size: 0.72rem; color: var(--admin-text-muted); }
  .perm-bulk { display: flex; gap: 0.25rem; }
  .perm-bulk button { font-size: 0.68rem; padding: 0.15rem 0.5rem; border-radius: 0.35rem;
    border: 1px solid var(--admin-border, hsla(220,25%,40%,0.4)); background: transparent;
    color: var(--admin-text-muted); cursor: pointer; }
  .perm-bulk button:hover { color: var(--admin-text); border-color: var(--admin-accent); }
  .perm-group-body { padding: 0.5rem 0.75rem; display: flex; flex-direction: column; gap: 0.15rem; }
  .perm-row { display: grid; grid-template-columns: 24px 200px 1fr; align-items: center; gap: 0.5rem;
    padding: 0.25rem 0; cursor: pointer; }
  .perm-row.changed { background: hsla(45,90%,55%,0.08); border-radius: 0.35rem; }
  .perm-check { width: 20px; height: 20px; border-radius: 0.35rem; border: 1px solid var(--admin-border, hsla(220,25%,40%,0.4));
    background: transparent; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #fff; }
  .perm-check.on { background: var(--admin-accent); border-color: var(--admin-accent); }
  .perm-slug { font-family: var(--admin-font-mono, monospace); font-size: 0.78rem; color: var(--admin-text); }
  .perm-desc { font-size: 0.78rem; color: var(--admin-text-muted); }
  .diff-badge { font-size: 0.62rem; padding: 0.05rem 0.35rem; border-radius: 9999px;
    background: hsla(45,90%,55%,0.18); color: var(--admin-warning); }
  .save-bar { position: sticky; bottom: 0; margin-top: 0.5rem; display: flex; align-items: center;
    justify-content: space-between; gap: 1rem; padding: 0.75rem 1rem; border-radius: 0.6rem;
    background: var(--admin-surface, hsla(220,25%,15%,0.96)); border: 1px solid var(--admin-accent);
    box-shadow: 0 -4px 16px hsla(220,40%,5%,0.35); }
  .save-bar-msg { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; color: var(--admin-text); }
  .save-bar-actions { display: flex; gap: 0.5rem; }
  @media (max-width: 820px) { .roles-grid { grid-template-columns: 1fr; } }
`;
