import type { TabId } from '../types';

export interface NavItem {
  id: TabId;
  key: string;
  icon: string;
}

export interface NavGroup {
  labelKey: string;
  items: NavItem[];
}

// Grouped navigation matching a GRC information architecture: posture overview,
// then one group per regulatory pillar.
export const NAV: NavGroup[] = [
  { labelKey: 'group.overview', items: [{ id: 'overview', key: 'tab.overview', icon: '◈' }] },
  {
    labelKey: 'group.incidents',
    items: [
      { id: 'incidents', key: 'tab.incidents', icon: '▲' },
      { id: 'dora', key: 'tab.dora', icon: '⚡' },
    ],
  },
  { labelKey: 'group.data', items: [{ id: 'dsr', key: 'tab.dsr', icon: '⚲' }] },
  { labelKey: 'group.thirdparty', items: [{ id: 'thirdparty', key: 'tab.thirdparty', icon: '⛓' }] },
  { labelKey: 'group.ai', items: [{ id: 'transparency', key: 'tab.transparency', icon: '✦' }] },
];
