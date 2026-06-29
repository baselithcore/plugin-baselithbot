/**
 * Console navigation model.
 *
 * The sidebar groups every admin surface into four task-oriented sections
 * (Identity, Access, Monitoring, Organization) the way Auth0 / Cloudflare do.
 * Ids are the existing `TabType` values so routing and the central RBAC
 * `(plugin, tab_id)` keys stay stable; labels/descriptions are i18n keys.
 */

import {
  LayoutDashboard,
  Users,
  Shield,
  Users2,
  Lock,
  Globe,
  Key,
  Activity,
  Building2,
  CreditCard,
  Puzzle,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { TabType } from '../../types';

export interface NavItem {
  id: TabType;
  icon: LucideIcon;
  labelKey: string;
  descKey: string;
}

export interface NavGroup {
  id: string;
  labelKey: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'general',
    labelKey: 'nav.group.general',
    items: [
      {
        id: 'overview',
        icon: LayoutDashboard,
        labelKey: 'nav.overview',
        descKey: 'nav.desc.overview',
      },
    ],
  },
  {
    id: 'identity',
    labelKey: 'nav.group.identity',
    items: [
      { id: 'users', icon: Users, labelKey: 'nav.users', descKey: 'nav.desc.users' },
      { id: 'roles', icon: Shield, labelKey: 'nav.roles', descKey: 'nav.desc.roles' },
      { id: 'groups', icon: Users2, labelKey: 'nav.groups', descKey: 'nav.desc.groups' },
    ],
  },
  {
    id: 'access',
    labelKey: 'nav.group.access',
    items: [
      { id: 'access', icon: Lock, labelKey: 'nav.access', descKey: 'nav.desc.access' },
      { id: 'sso', icon: Globe, labelKey: 'nav.sso', descKey: 'nav.desc.sso' },
    ],
  },
  {
    id: 'monitoring',
    labelKey: 'nav.group.monitoring',
    items: [
      { id: 'sessions', icon: Key, labelKey: 'nav.sessions', descKey: 'nav.desc.sessions' },
      { id: 'audit', icon: Activity, labelKey: 'nav.audit', descKey: 'nav.desc.audit' },
    ],
  },
  {
    id: 'organization',
    labelKey: 'nav.group.organization',
    items: [
      { id: 'tenants', icon: Building2, labelKey: 'nav.tenants', descKey: 'nav.desc.tenants' },
      { id: 'budget', icon: CreditCard, labelKey: 'nav.budget', descKey: 'nav.desc.budget' },
      { id: 'plugins', icon: Puzzle, labelKey: 'nav.plugins', descKey: 'nav.desc.plugins' },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/** Resolve the nav descriptor for an active tab (falls back to the first item). */
export const findNavItem = (id: TabType): NavItem =>
  NAV_ITEMS.find((i) => i.id === id) ?? NAV_ITEMS[0];

/** Resolve the group an active tab belongs to (for the top-bar breadcrumb). */
export const findNavGroup = (id: TabType): NavGroup =>
  NAV_GROUPS.find((g) => g.items.some((i) => i.id === id)) ?? NAV_GROUPS[0];
