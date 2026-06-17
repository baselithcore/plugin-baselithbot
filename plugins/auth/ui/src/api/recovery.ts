/**
 * Public self-service recovery API client (forgot/reset password, email
 * verification, invitation acceptance). No auth required.
 */

const API_BASE = '/api/auth';

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export interface MessageResponse {
  message: string;
}

export interface InviteInfo {
  email: string;
  roles: string[];
}

export function forgotPassword(identifier: string): Promise<MessageResponse> {
  return postJson('/forgot-password', { identifier });
}

export function resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
  return postJson('/reset-password', { token, new_password: newPassword });
}

export function verifyEmail(token: string): Promise<MessageResponse> {
  return postJson('/verify-email', { token });
}

export function resendVerification(email: string): Promise<MessageResponse> {
  return postJson('/resend-verification', { email });
}

export async function getInvitation(token: string): Promise<InviteInfo> {
  const res = await fetch(`${API_BASE}/invitations/accept?token=${encodeURIComponent(token)}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Invitation not found' }));
    throw new Error(err.detail || 'Invitation not found');
  }
  return res.json();
}

export interface AcceptInvitePayload {
  token: string;
  password: string;
  username?: string;
  full_name?: string;
}

export function acceptInvitation(payload: AcceptInvitePayload): Promise<unknown> {
  return postJson('/invitations/accept', payload);
}
