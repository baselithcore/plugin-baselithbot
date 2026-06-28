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
  mfa_required: boolean;
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
  mfa_required?: boolean;
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

export interface TokenResponse {
  access_token: string;
  expires_in: number;
}

// ----- multi-tenancy ---------------------------------------------------------

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  status: string;
  member_count: number;
}

export interface TenantMember {
  user_id: string;
  email: string | null;
  username: string | null;
  role: string;
  is_default: boolean;
}

export interface MyTenant {
  id: string;
  slug: string;
  name: string;
  status: string;
  role: string;
  is_default: boolean;
}

export type TabType =
  | 'overview'
  | 'users'
  | 'sessions'
  | 'audit'
  | 'roles'
  | 'groups'
  | 'access'
  | 'sso'
  | 'tenants'
  | 'budget';

export const ROLES = ['admin', 'user', 'guest'] as const;
export type Role = (typeof ROLES)[number];

export interface PluginTab {
  id: string;
  label: string;
  plugin: string;
}

// ---------------------------------------------------------------------------
// RBAC
// ---------------------------------------------------------------------------

export interface RbacPermission {
  slug: string;
  description: string;
  category: string;
}

export interface RbacRole {
  id: string;
  slug: string;
  name: string;
  description: string;
  is_system: boolean;
  permissions: string[];
}

export interface RoleCreateRequest {
  slug: string;
  name: string;
  description?: string;
}

export interface RoleUpdateRequest {
  name: string;
  description?: string;
}

/** Predefined, non-privileged permission bundle to pre-fill a new custom role. */
export interface RoleTemplate {
  slug: string;
  name: string;
  description: string;
  permissions: string[];
}

export interface TabPolicy {
  plugin: string;
  tab_id: string;
  label: string;
  restricted: boolean;
  /** Platform-infrastructure plugin (manifest `system: true`): admin-only by
   * default, can only be granted per role — never opened to everyone. */
  system?: boolean;
}

export interface AccessibleTab extends TabPolicy {
  allowed: boolean;
}

export interface MePermissions {
  permissions: string[];
}

export interface RbacGroup {
  id: string;
  slug: string;
  name: string;
  description: string;
  is_system: boolean;
  mfa_required: boolean;
  member_count: number;
  roles: string[];
}

export interface GroupMember {
  id: string;
  email: string;
  username: string | null;
}

export interface GroupCreateRequest {
  slug: string;
  name: string;
  description?: string;
  mfa_required?: boolean;
}

export interface GroupUpdateRequest {
  name: string;
  description?: string;
  mfa_required?: boolean;
}
