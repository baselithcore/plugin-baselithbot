/**
 * RBAC API Client — roles, permissions, per-tab access policy, and the
 * caller's own permissions/tabs.
 */

import type {
  AccessibleTab,
  GroupCreateRequest,
  GroupMember,
  MePermissions,
  RbacGroup,
  RbacPermission,
  RbacRole,
  RoleCreateRequest,
  RoleUpdateRequest,
  TabPolicy,
} from '../types';
import { fetchWithAuth, handleResponse } from './client';

const ADMIN = '/api/admin/rbac';
const ME = '/api/auth/access';

// ----- permissions & roles -------------------------------------------------

export async function listPermissions(): Promise<RbacPermission[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/permissions`));
}

export async function listRoles(): Promise<RbacRole[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/roles`));
}

export async function createRole(data: RoleCreateRequest): Promise<RbacRole> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/roles`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  );
}

export async function updateRole(roleId: string, data: RoleUpdateRequest): Promise<RbacRole> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/roles/${roleId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  );
}

export async function deleteRole(roleId: string): Promise<void> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/roles/${roleId}`, { method: 'DELETE' }));
}

export async function setRolePermissions(roleId: string, permissions: string[]): Promise<RbacRole> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/roles/${roleId}/permissions`, {
      method: 'PUT',
      body: JSON.stringify({ permissions }),
    })
  );
}

export async function grantPermission(roleId: string, slug: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/roles/${roleId}/permissions/${encodeURIComponent(slug)}`, {
      method: 'POST',
    })
  );
}

export async function revokePermission(roleId: string, slug: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/roles/${roleId}/permissions/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
    })
  );
}

// ----- user <-> role -------------------------------------------------------

export async function getUserRoles(userId: string): Promise<RbacRole[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/users/${userId}/roles`));
}

export async function assignUserRole(userId: string, roleId: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/users/${userId}/roles`, {
      method: 'POST',
      body: JSON.stringify({ role_id: roleId }),
    })
  );
}

export async function revokeUserRole(userId: string, roleId: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/users/${userId}/roles/${roleId}`, {
      method: 'DELETE',
    })
  );
}

// ----- tab access policy ---------------------------------------------------

export async function listTabs(): Promise<TabPolicy[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/tabs`));
}

export async function refreshTabs(): Promise<TabPolicy[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/tabs/refresh`, { method: 'POST' }));
}

export async function setTabRestricted(
  plugin: string,
  tabId: string,
  restricted: boolean
): Promise<TabPolicy> {
  return handleResponse(
    await fetchWithAuth(
      `${ADMIN}/tabs/${encodeURIComponent(plugin)}/${encodeURIComponent(tabId)}/restricted`,
      { method: 'PUT', body: JSON.stringify({ restricted }) }
    )
  );
}

// ----- self-service --------------------------------------------------------

export async function getMyPermissions(): Promise<MePermissions> {
  return handleResponse(await fetchWithAuth(`${ME}/permissions`));
}

export async function getMyTabs(): Promise<AccessibleTab[]> {
  return handleResponse(await fetchWithAuth(`${ME}/tabs`));
}

// ----- groups --------------------------------------------------------------

export async function listGroups(): Promise<RbacGroup[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/groups`));
}

export async function createGroup(data: GroupCreateRequest): Promise<RbacGroup> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/groups`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  );
}

export async function deleteGroup(groupId: string): Promise<void> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/groups/${groupId}`, { method: 'DELETE' }));
}

export async function listGroupMembers(groupId: string): Promise<GroupMember[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/groups/${groupId}/members`));
}

export async function addGroupMember(groupId: string, userId: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/groups/${groupId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    })
  );
}

export async function removeGroupMember(groupId: string, userId: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
    })
  );
}

export async function assignGroupRole(groupId: string, roleId: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/groups/${groupId}/roles`, {
      method: 'POST',
      body: JSON.stringify({ role_id: roleId }),
    })
  );
}

export async function revokeGroupRole(groupId: string, roleId: string): Promise<void> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/groups/${groupId}/roles/${roleId}`, {
      method: 'DELETE',
    })
  );
}
