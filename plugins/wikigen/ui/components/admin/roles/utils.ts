import type { PermissionEntry, RoleSummary } from '../../../lib/api/rbac';
import { groupForSlug, groupSortKey, type GroupMeta } from './permission_catalog';

export interface PermissionGroup {
  meta: GroupMeta;
  perms: PermissionEntry[];
}

export function groupPermissions(perms: PermissionEntry[]): PermissionGroup[] {
  const map = new Map<string, PermissionEntry[]>();
  for (const p of perms) {
    const g = groupForSlug(p.slug);
    const arr = map.get(g.id) ?? [];
    arr.push(p);
    map.set(g.id, arr);
  }
  return Array.from(map.entries())
    .map(([id, list]) => ({
      meta: groupForSlug(list[0].slug),
      perms: list.slice().sort((a, b) => a.slug.localeCompare(b.slug)),
      _sort: groupSortKey(id),
    }))
    .sort((a, b) => a._sort - b._sort)
    .map(({ meta, perms: ps }) => ({ meta, perms: ps }));
}

export interface RoleDiff {
  added: string[];
  removed: string[];
  total: number;
}

export function computeDiff(original: Set<string>, draft: Set<string>): RoleDiff {
  const added: string[] = [];
  const removed: string[] = [];
  for (const s of draft) if (!original.has(s)) added.push(s);
  for (const s of original) if (!draft.has(s)) removed.push(s);
  return { added, removed, total: added.length + removed.length };
}

export function dirtyRoleIds(
  roles: RoleSummary[],
  original: Record<string, Set<string>>,
  draft: Record<string, Set<string>>,
): string[] {
  const out: string[] = [];
  for (const r of roles) {
    const o = original[r.id] ?? new Set();
    const d = draft[r.id] ?? new Set();
    if (computeDiff(o, d).total > 0) out.push(r.id);
  }
  return out;
}

export function filterPermissions(
  perms: PermissionEntry[],
  query: string,
): PermissionEntry[] {
  const q = query.trim().toLowerCase();
  if (!q) return perms;
  return perms.filter(
    (p) => p.slug.toLowerCase().includes(q) || (p.description ?? '').toLowerCase().includes(q),
  );
}

export function isLocked(role: RoleSummary): boolean {
  return role.is_system && role.slug === 'superuser';
}
