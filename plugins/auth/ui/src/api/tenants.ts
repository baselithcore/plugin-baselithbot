/**
 * Multi-tenancy API client — admin tenant/membership management and the
 * self-service tenant switcher. Mirrors plugins/auth admin_router/_tenants and
 * router/_tenant_routes.
 */

import { fetchWithAuth, handleResponse } from './client';
import type { MessageResponse, MyTenant, Tenant, TenantMember, TokenResponse } from '../types';

const ADMIN = '/api/admin/tenants';
const SELF = '/api/auth/tenants';

// ----- admin -----------------------------------------------------------------

export async function listTenants(): Promise<Tenant[]> {
  return handleResponse(await fetchWithAuth(ADMIN));
}

export async function createTenant(slug: string, name: string): Promise<Tenant> {
  return handleResponse(
    await fetchWithAuth(ADMIN, {
      method: 'POST',
      body: JSON.stringify({ slug, name }),
    })
  );
}

export async function setTenantStatus(
  tenantId: string,
  status: 'active' | 'suspended'
): Promise<MessageResponse> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/${tenantId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  );
}

export async function deleteTenant(tenantId: string): Promise<MessageResponse> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/${tenantId}`, { method: 'DELETE' }));
}

export async function listMembers(tenantId: string): Promise<TenantMember[]> {
  return handleResponse(await fetchWithAuth(`${ADMIN}/${tenantId}/members`));
}

export async function addMember(
  tenantId: string,
  userId: string,
  role = 'member'
): Promise<MessageResponse> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/${tenantId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role }),
    })
  );
}

export async function removeMember(tenantId: string, userId: string): Promise<MessageResponse> {
  return handleResponse(
    await fetchWithAuth(`${ADMIN}/${tenantId}/members/${userId}`, { method: 'DELETE' })
  );
}

// ----- self-service ----------------------------------------------------------

export async function myTenants(): Promise<MyTenant[]> {
  return handleResponse(await fetchWithAuth(SELF));
}

export async function switchTenant(tenantId: string): Promise<TokenResponse> {
  return handleResponse(
    await fetchWithAuth(`${SELF}/switch`, {
      method: 'POST',
      body: JSON.stringify({ tenant_id: tenantId }),
    })
  );
}
