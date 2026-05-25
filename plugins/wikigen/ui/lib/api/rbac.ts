/**
 * RBAC admin API client (Fase 7).
 *
 * Endpoint montati a `/api/admin/rbac/*`. Gating server-side via
 * `require_permission(admin.user.manage)` — un 403 qui significa
 * permesso mancante, non sessione scaduta.
 */

import { json } from './client';

export interface PermissionEntry {
  slug: string;
  description: string;
}

export interface RoleSummary {
  id: string;
  slug: string;
  name: string;
  description: string;
  is_system: boolean;
  tenant_id: string | null;
}

export interface RoleDetail extends RoleSummary {
  permissions: string[];
}

export interface DomainGrant {
  domain_slug: string;
  role_id: string | null;
  role_slug: string | null;
}

export interface UserWithRoles {
  id: string;
  email: string;
  display_name: string;
  tenant_id: string;
  role: string;
  is_active: boolean;
  roles: RoleSummary[];
  domains: string[];
  domain_grants: DomainGrant[];
}

export const listPermissions = (): Promise<PermissionEntry[]> =>
  json('/admin/rbac/permissions');

export const listRoles = (): Promise<RoleSummary[]> => json('/admin/rbac/roles');

export const getRoleDetail = (roleId: string): Promise<RoleDetail> =>
  json(`/admin/rbac/roles/${encodeURIComponent(roleId)}`);

export const listUsersWithRoles = (): Promise<UserWithRoles[]> =>
  json('/admin/rbac/users');

export const setRolePermissions = (
  roleId: string,
  permissions: string[]
): Promise<RoleDetail> =>
  json(`/admin/rbac/roles/${encodeURIComponent(roleId)}/permissions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ permissions }),
  });

export const assignRole = (
  userId: string,
  roleId: string
): Promise<{ status: string; noop: boolean }> =>
  json(`/admin/rbac/users/${encodeURIComponent(userId)}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role_id: roleId }),
  });

export const revokeRole = (
  userId: string,
  roleId: string
): Promise<{ status: string; removed: boolean }> =>
  json(
    `/admin/rbac/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(roleId)}`,
    { method: 'DELETE' }
  );

export const grantDomain = (
  userId: string,
  domainSlug: string,
  roleId?: string
): Promise<{ status: string; applied: boolean }> =>
  json(`/admin/rbac/users/${encodeURIComponent(userId)}/domains`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain_slug: domainSlug, role_id: roleId ?? null }),
  });

export const revokeDomain = (
  userId: string,
  domainSlug: string
): Promise<{ status: string; removed: boolean }> =>
  json(
    `/admin/rbac/users/${encodeURIComponent(userId)}/domains/${encodeURIComponent(domainSlug)}`,
    { method: 'DELETE' }
  );

// --- user lifecycle (rbac_lifecycle.py router) ----------------------------

export interface CreateUserArgs {
  email: string;
  password: string;
  display_name?: string;
  role_slug?: string | null;
  tenant_name?: string;
}

export interface CreatedUser {
  status: string;
  user_id: string;
  tenant_id: string;
  email: string;
  role_slug: string | null;
  password_must_change: boolean;
}

export const createUser = (args: CreateUserArgs): Promise<CreatedUser> =>
  json('/admin/rbac/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });

export const setUserActive = (
  userId: string,
  isActive: boolean
): Promise<{ status: string; is_active: boolean }> =>
  json(`/admin/rbac/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  });

export const deleteUser = (
  userId: string
): Promise<{ status: string; removed: boolean }> =>
  json(`/admin/rbac/users/${encodeURIComponent(userId)}`, { method: 'DELETE' });
