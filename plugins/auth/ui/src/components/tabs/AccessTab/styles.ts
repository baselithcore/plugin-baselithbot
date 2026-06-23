/** Scoped styles for the redesigned Access Control screen. */

export const ACCESS_STYLES = `
  .access-tab { display: flex; flex-direction: column; gap: 1rem; }

  .mfa-card { display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    padding: 0.9rem 1.1rem; border-radius: 0.75rem;
    background: linear-gradient(180deg, hsla(220,25%,17%,0.55), hsla(220,25%,13%,0.55));
    border: 1px solid var(--admin-border, hsla(220,25%,40%,0.3)); }
  .mfa-info { display: flex; align-items: center; gap: 0.75rem; color: var(--admin-text); }
  .mfa-info .mfa-ico { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 0.6rem;
    background: hsla(150,60%,45%,0.14); color: var(--admin-success, #4ade80); flex-shrink: 0; }
  .mfa-title { font-weight: 600; font-size: 0.92rem; }
  .mfa-hint { color: var(--admin-text-muted); font-size: 0.8rem; }
  .switch { position: relative; width: 46px; height: 26px; border-radius: 9999px; flex-shrink: 0;
    border: none; cursor: pointer; background: var(--admin-border, hsla(220,25%,40%,0.4)); transition: background 0.2s; }
  .switch.on { background: var(--admin-success, #22c55e); }
  .switch:disabled { opacity: 0.6; cursor: wait; }
  .switch-knob { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%;
    background: #fff; transition: transform 0.2s; box-shadow: 0 1px 3px hsla(0,0%,0%,0.4); }
  .switch.on .switch-knob { transform: translateX(20px); }

  .access-groups { display: flex; flex-direction: column; gap: 0.85rem; }
  .pgroup { border: 1px solid var(--admin-border, hsla(220,25%,40%,0.28)); border-radius: 0.8rem; overflow: hidden;
    background: var(--admin-surface, hsla(220,25%,14%,0.45)); }
  .pgroup-head { display: flex; align-items: center; gap: 0.75rem; width: 100%; padding: 0.85rem 1rem;
    background: transparent; border: none; cursor: pointer; color: var(--admin-text); text-align: left; }
  .pgroup-head:hover { background: hsla(220,25%,50%,0.06); }
  .pgroup-ico { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 0.55rem;
    background: hsla(220,80%,62%,0.15); color: var(--admin-accent); flex-shrink: 0; }
  .pgroup-meta { display: flex; flex-direction: column; gap: 0.1rem; flex: 1; min-width: 0; }
  .pgroup-name { font-weight: 600; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; }
  .pgroup-slug { font-family: monospace; font-size: 0.72rem; color: var(--admin-text-muted); }
  .pgroup-count { font-size: 0.72rem; color: var(--admin-text-muted); padding: 0.15rem 0.55rem;
    border-radius: 9999px; background: hsla(220,25%,50%,0.12); white-space: nowrap; }
  .sys-badge { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.04em; padding: 0.1rem 0.4rem;
    border-radius: 9999px; background: hsla(265,80%,62%,0.18); color: #b59bff; }

  .tabrow { padding: 0.75rem 1rem; border-top: 1px solid var(--admin-border, hsla(220,25%,40%,0.18)); }
  .tabrow-main { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
  .tabrow-id { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
  .tabrow-label { font-weight: 500; font-size: 0.9rem; color: var(--admin-text); }
  .tabrow-slug { font-family: monospace; font-size: 0.7rem; color: var(--admin-text-muted); }

  .seg { display: inline-flex; padding: 0.2rem; border-radius: 0.6rem; gap: 0.15rem; flex-shrink: 0;
    background: hsla(220,25%,50%,0.1); border: 1px solid var(--admin-border, hsla(220,25%,40%,0.25)); }
  .seg button { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.7rem; font-size: 0.78rem;
    border: none; background: transparent; color: var(--admin-text-muted); border-radius: 0.45rem; cursor: pointer; }
  .seg button:hover { color: var(--admin-text); }
  .seg button.on.open { background: hsla(150,60%,45%,0.2); color: var(--admin-success, #4ade80); }
  .seg button.on.restricted { background: hsla(35,90%,55%,0.2); color: #f5a623; }

  .tabrow-roles { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.65rem;
    padding-top: 0.65rem; border-top: 1px dashed var(--admin-border, hsla(220,25%,40%,0.2)); }
  .tabrow-roles-label { font-size: 0.72rem; color: var(--admin-text-muted); margin-right: 0.25rem; }
  .role-chip { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.25rem 0.6rem; font-size: 0.76rem;
    border-radius: 9999px; cursor: pointer; border: 1px solid var(--admin-border, hsla(220,25%,40%,0.4));
    background: transparent; color: var(--admin-text-muted); transition: all 0.15s; }
  .role-chip:hover { border-color: var(--admin-accent); color: var(--admin-text); }
  .role-chip.on { background: var(--admin-accent); border-color: var(--admin-accent); color: #fff; }
  .role-chip.admin { cursor: default; background: hsla(265,80%,62%,0.16); border-color: transparent; color: #c4b1ff; }
  .role-chip.admin:hover { border-color: transparent; color: #c4b1ff; }
  .tabrow-roles-empty { font-size: 0.74rem; color: var(--admin-text-muted); font-style: italic; }

  .access-empty { text-align: center; padding: 2.5rem 1rem; color: var(--admin-text-muted); }
  @media (max-width: 720px) {
    .tabrow-main { flex-direction: column; align-items: flex-start; }
    .access-search input { min-width: 0; width: 100%; }
  }
`;
