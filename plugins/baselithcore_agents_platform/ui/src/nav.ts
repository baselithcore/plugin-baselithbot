/** Shared dashboard navigation, consumed by both the router and the sidebar. */

/** Plugin id — must match get_ui_tabs()[].plugin (metadata.name). */
export const PLUGIN = 'baselithcore_agents_platform';

export interface NavItem {
  /** Router path. */
  to: string;
  /** Tab id — must match a get_ui_tabs()[].id for central RBAC gating. */
  id: string;
  label: string;
  /** Exact-match the index route. */
  end?: boolean;
}

export const NAV: NavItem[] = [
  { to: '/', id: 'builder', label: 'Builder', end: true },
  { to: '/agents', id: 'agents', label: 'Agents' },
  { to: '/runs', id: 'runs', label: 'Runs' },
  { to: '/schedules', id: 'schedules', label: 'Schedules' },
  { to: '/docs', id: 'docs', label: 'Docs · MCP' },
  { to: '/models', id: 'models', label: 'Models' },
];
