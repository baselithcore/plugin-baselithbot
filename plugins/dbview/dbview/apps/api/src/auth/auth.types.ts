import type { Role, UserPublic } from '@dbview/shared';

export interface AuthPrincipal {
  id: string;
  email: string;
  role: Role;
  source: 'jwt' | 'api-key';
  mustChangePassword?: boolean;
}

export function toPublicUser(u: {
  id: string;
  email: string;
  displayName: string | null;
  role: Role;
  isActive: boolean;
  createdAt: string;
  lastLoginAt: string | null;
  mustChangePassword: boolean;
}): UserPublic {
  return {
    id: u.id,
    email: u.email,
    displayName: u.displayName,
    role: u.role,
    isActive: u.isActive,
    createdAt: u.createdAt,
    lastLoginAt: u.lastLoginAt,
    mustChangePassword: u.mustChangePassword,
  };
}
