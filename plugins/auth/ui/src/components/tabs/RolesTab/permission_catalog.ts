/**
 * Permission-category presentation metadata for the Roles matrix.
 *
 * Labels and descriptions are NOT hardcoded here — they come from the i18n
 * catalog (`roles.permissionCategories.*`, `roles.categoryDescriptions.*`,
 * `roles.permissionDescriptions.*`) so the matrix stays fully localized
 * (en + it). This module only owns the non-translatable bits: which icon and
 * what display order each permission category gets. Categories mirror the
 * backend ``auth_permissions.category`` values.
 */

import {
  Activity,
  Dot,
  LayoutGrid,
  type LucideIcon,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  Users,
  UsersRound,
} from 'lucide-react';

export const CATEGORY_ICONS: Record<string, LucideIcon> = {
  system: ShieldAlert,
  users: Users,
  groups: UsersRound,
  rbac: ShieldCheck,
  sessions: Activity,
  audit: ScrollText,
  tab: LayoutGrid,
  general: Dot,
};

const CATEGORY_ORDER = ['system', 'users', 'groups', 'rbac', 'sessions', 'audit', 'tab', 'general'];

export function categoryIcon(id: string): LucideIcon {
  return CATEGORY_ICONS[id] ?? CATEGORY_ICONS.general;
}

export function categorySortKey(id: string): number {
  const i = CATEGORY_ORDER.indexOf(id);
  return i === -1 ? 998 : i;
}

/** Stable-sorted category ids by display order, then alphabetically. */
export function sortedCategories(ids: string[]): string[] {
  return [...ids].sort((a, b) => categorySortKey(a) - categorySortKey(b) || a.localeCompare(b));
}
