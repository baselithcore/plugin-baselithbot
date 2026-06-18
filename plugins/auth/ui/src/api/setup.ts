/**
 * First-run setup API client.
 *
 * Backs the initial-admin wizard shown when a fresh install has no account yet.
 * Both endpoints are public (the system has no user to authenticate yet);
 * `/initialize` is fail-closed server-side once any user exists.
 */

const API_BASE = '/api/auth';

export interface SetupStatus {
  needs_setup: boolean;
}

export interface SetupInitializePayload {
  email: string;
  password: string;
  username?: string;
}

export interface SetupTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/** Whether the first-run wizard should be shown (empty user table). */
export async function getSetupStatus(): Promise<SetupStatus> {
  const response = await fetch(`${API_BASE}/setup/status`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to read setup status');
  }
  return response.json();
}

/** Create the initial admin and receive a logged-in access token. */
export async function initializeAdmin(
  payload: SetupInitializePayload,
): Promise<SetupTokenResponse> {
  const response = await fetch(`${API_BASE}/setup/initialize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Setup failed' }));
    throw new Error(error.detail || 'Setup failed');
  }
  return response.json();
}
