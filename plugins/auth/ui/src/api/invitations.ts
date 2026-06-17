/** Admin invitations + user lifecycle API client (cookie-authenticated). */

const API_BASE = '/api/admin';

async function call<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export interface Invitation {
  id: string;
  email: string;
  roles: string[];
  expires_at: string | null;
  accepted_at: string | null;
  created_at: string | null;
}

export function inviteUser(email: string, roles: string[]): Promise<Invitation> {
  return call('/invitations', { method: 'POST', body: JSON.stringify({ email, roles }) });
}

export function listInvitations(): Promise<Invitation[]> {
  return call('/invitations');
}

export function revokeInvitation(id: string): Promise<{ message: string }> {
  return call(`/invitations/${id}`, { method: 'DELETE' });
}

export function setUserStatus(
  userId: string,
  statusValue: 'active' | 'suspended' | 'deactivated'
): Promise<{ message: string }> {
  return call(`/users/${userId}/status`, {
    method: 'POST',
    body: JSON.stringify({ status: statusValue }),
  });
}
