/**
 * Security policy API client (org-wide MFA enforcement toggle).
 *
 * Per-user and per-group MFA requirements are managed through the users/groups
 * endpoints; this covers only the single "require MFA for everyone" switch.
 */

import { fetchWithAuth, handleResponse } from './client';

const API_BASE = '/api/admin/security';

export interface MfaPolicy {
  mfa_required_all: boolean;
}

export async function getMfaPolicy(): Promise<MfaPolicy> {
  const res = await fetchWithAuth(`${API_BASE}/mfa-policy`);
  return handleResponse<MfaPolicy>(res);
}

export async function setMfaPolicy(mfaRequiredAll: boolean): Promise<MfaPolicy> {
  const res = await fetchWithAuth(`${API_BASE}/mfa-policy`, {
    method: 'PUT',
    body: JSON.stringify({ mfa_required_all: mfaRequiredAll }),
  });
  return handleResponse<MfaPolicy>(res);
}
