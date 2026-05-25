/**
 * Auth API Client
 *
 * API client for authentication endpoints.
 */

const API_BASE = '/api/auth';

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface MFARequiredResponse {
  mfa_required: boolean;
  temp_token: string;
}

export interface MFAVerifyRequest {
  temp_token: string;
  code: string;
}

export interface UserInfo {
  id: string;
  email: string;
  username: string | null;
  roles: string[];
  mfa_enabled: boolean;
  allowed_tabs: string[] | null;
}

export interface MFASetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code: string | null;
  backup_codes: string[];
}

export type LoginResponse = TokenResponse | MFARequiredResponse;

export function isMFARequired(response: LoginResponse): response is MFARequiredResponse {
  return !!(response as any).mfa_required;
}

/**
 * Login with email or username and password.
 */
export async function login(identifier: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ identifier, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
}

/**
 * Verify MFA code.
 */
export async function verifyMFA(tempToken: string, code: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/mfa/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ temp_token: tempToken, code }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'MFA verification failed' }));
    throw new Error(error.detail || 'MFA verification failed');
  }

  return response.json();
}

/**
 * Logout and invalidate refresh token.
 */
export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/logout`, {
    method: 'POST',
    credentials: 'include',
  });
}

/**
 * Refresh access token.
 */
export async function refreshToken(): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/refresh`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Session expired');
  }

  return response.json();
}

/**
 * Get current user info.
 */
export async function getCurrentUser(accessToken: string): Promise<UserInfo> {
  const response = await fetch(`${API_BASE}/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to get user info');
  }

  return response.json();
}

/**
 * Setup MFA.
 */
export async function setupMFA(accessToken: string): Promise<MFASetupResponse> {
  const response = await fetch(`${API_BASE}/mfa/setup`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to setup MFA');
  }

  return response.json();
}

/**
 * Enable MFA with verification code.
 */
export async function enableMFA(accessToken: string, code: string): Promise<void> {
  const response = await fetch(`${API_BASE}/mfa/enable?code=${encodeURIComponent(code)}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to enable MFA' }));
    throw new Error(error.detail || 'Failed to enable MFA');
  }
}

/**
 * Get available plugin tabs from backend.
 */
import { PluginTab } from '../types';

export async function getPluginTabs(accessToken: string): Promise<PluginTab[]> {
  const adminApiBase = '/api/admin';
  const response = await fetch(`${adminApiBase}/plugins/tabs`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    credentials: 'include',
  });

  if (!response.ok) {
    console.error('Failed to fetch plugin tabs');
    return [];
  }

  return response.json();
}
