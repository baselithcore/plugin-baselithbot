/**
 * Groups admin API client (mig 015).
 *
 * Endpoint montati a `/api/admin/rbac/groups/*`. Gating server-side
 * via `require_permission(admin.group.manage)` — un 403 qui significa
 * permesso mancante, non sessione scaduta.
 *
 * Effective permissions: ogni utente eredita i permessi dei ruoli
 * associati ai gruppi a cui appartiene (UNION con `user_roles`
 * diretti). Aggregazione è server-side: la UI mostra solo la
 * membership, mai i perms direttamente. Vedi `AuthUser.permissions`.
 */

import { json } from './client';

export interface GroupSummary {
  id: string;
  slug: string;
  name: string;
  description: string;
  is_system: boolean;
  tenant_id: string;
  member_count: number;
  role_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GroupMember {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  added_at?: string | null;
  added_by?: string | null;
}

export interface GroupRoleEntry {
  id: string;
  slug: string;
  name: string;
  description: string;
  is_system: boolean;
  tenant_id: string | null;
  granted_at?: string | null;
  granted_by?: string | null;
}

export interface GroupDetail extends GroupSummary {
  members: GroupMember[];
  roles: GroupRoleEntry[];
}

export interface CreateGroupArgs {
  slug: string;
  name: string;
  description?: string;
}

export interface UpdateGroupArgs {
  name?: string;
  description?: string;
}

export interface AddMembersResult {
  status: string;
  added: string[];
  skipped: string[];
}

const BASE_PATH = '/admin/rbac/groups';

export const listGroups = (): Promise<GroupSummary[]> => json(BASE_PATH);

export const createGroup = (args: CreateGroupArgs): Promise<GroupSummary> =>
  json(BASE_PATH, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });

export const getGroup = (groupId: string): Promise<GroupDetail> =>
  json(`${BASE_PATH}/${encodeURIComponent(groupId)}`);

export const updateGroup = (
  groupId: string,
  args: UpdateGroupArgs
): Promise<GroupSummary> =>
  json(`${BASE_PATH}/${encodeURIComponent(groupId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });

export const deleteGroup = (
  groupId: string
): Promise<{ status: string; removed: boolean }> =>
  json(`${BASE_PATH}/${encodeURIComponent(groupId)}`, { method: 'DELETE' });

export const addMembers = (
  groupId: string,
  userIds: string[]
): Promise<AddMembersResult> =>
  json(`${BASE_PATH}/${encodeURIComponent(groupId)}/members`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_ids: userIds }),
  });

export const removeMember = (
  groupId: string,
  userId: string
): Promise<{ status: string; removed: boolean }> =>
  json(
    `${BASE_PATH}/${encodeURIComponent(groupId)}/members/${encodeURIComponent(userId)}`,
    { method: 'DELETE' }
  );

export const assignGroupRole = (
  groupId: string,
  roleId: string
): Promise<{ status: string; noop: boolean }> =>
  json(`${BASE_PATH}/${encodeURIComponent(groupId)}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role_id: roleId }),
  });

export const revokeGroupRole = (
  groupId: string,
  roleId: string
): Promise<{ status: string; removed: boolean }> =>
  json(
    `${BASE_PATH}/${encodeURIComponent(groupId)}/roles/${encodeURIComponent(roleId)}`,
    { method: 'DELETE' }
  );
