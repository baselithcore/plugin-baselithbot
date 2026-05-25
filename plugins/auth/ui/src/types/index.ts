/**
 * Admin Panel Type Definitions
 */

export interface User {
  id: string;
  email: string;
  username: string | null;
  roles: string[];
  is_active: boolean;
  mfa_enabled: boolean;
  allowed_tabs: string[] | null;
  created_at: string | null;
  last_login: string | null;
  failed_login_attempts: number;
  is_locked: boolean;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  limit: number;
}

export interface CreateUserRequest {
  email: string;
  username?: string | null;
  password?: string;
  roles: string[];
  allowed_tabs?: string[] | null;
}

export interface CreateUserResponse {
  user: User;
  temporary_password: string | null;
}

export interface UpdateUserRequest {
  email?: string;
  username?: string | null;
  roles?: string[];
  is_active?: boolean;
  allowed_tabs?: string[] | null;
}

export interface ResetPasswordRequest {
  new_password?: string;
}

export interface ResetPasswordResponse {
  message: string;
  temporary_password: string | null;
}

export interface Session {
  id: string;
  user_id: string;
  user_email: string;
  created_at: string;
  expires_at: string;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}

export interface AuditEntry {
  id: string;
  action: string;
  actor_id: string;
  target_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogResponse {
  entries: AuditEntry[];
  total: number;
  page: number;
  limit: number;
}

export interface MessageResponse {
  message: string;
}

export type TabType = 'users' | 'sessions' | 'audit';

export const ROLES = ['admin', 'user', 'guest'] as const;
export type Role = (typeof ROLES)[number];

export interface PluginTab {
  id: string;
  label: string;
  plugin: string;
}
