/**
 * Users API Client
 */

import type {
  User,
  UserListResponse,
  CreateUserRequest,
  CreateUserResponse,
  UpdateUserRequest,
  ResetPasswordRequest,
  ResetPasswordResponse,
  MessageResponse,
} from '../types';

const API_BASE = '/api/admin';

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = sessionStorage.getItem('auth_access_token');

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    credentials: 'include',
  });

  if (response.status === 401) {
    // Token expired or invalid - redirect to login
    window.location.href = '/auth/login';
    throw new Error('Session expired');
  }

  return response;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

export async function listUsers(
  page = 1,
  limit = 20,
  includeInactive = false,
  search?: string
): Promise<UserListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    include_inactive: includeInactive.toString(),
  });

  if (search) {
    params.set('search', search);
  }

  const response = await fetchWithAuth(`${API_BASE}/users?${params}`);
  return handleResponse<UserListResponse>(response);
}

export async function getUser(userId: string): Promise<User> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}`);
  return handleResponse<User>(response);
}

export async function createUser(data: CreateUserRequest): Promise<CreateUserResponse> {
  const response = await fetchWithAuth(`${API_BASE}/users`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return handleResponse<CreateUserResponse>(response);
}

export async function updateUser(userId: string, data: UpdateUserRequest): Promise<User> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  return handleResponse<User>(response);
}

export async function deleteUser(userId: string): Promise<MessageResponse> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}`, {
    method: 'DELETE',
  });
  return handleResponse<MessageResponse>(response);
}

export async function resetPassword(
  userId: string,
  data?: ResetPasswordRequest
): Promise<ResetPasswordResponse> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}/reset-password`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  });
  return handleResponse<ResetPasswordResponse>(response);
}

export async function unlockUser(userId: string): Promise<MessageResponse> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}/unlock`, {
    method: 'POST',
  });
  return handleResponse<MessageResponse>(response);
}

export async function revokeSessions(userId: string): Promise<MessageResponse> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}/revoke-sessions`, {
    method: 'POST',
  });
  return handleResponse<MessageResponse>(response);
}

export async function disableMFA(userId: string): Promise<MessageResponse> {
  const response = await fetchWithAuth(`${API_BASE}/users/${userId}/mfa`, {
    method: 'DELETE',
  });
  return handleResponse<MessageResponse>(response);
}
