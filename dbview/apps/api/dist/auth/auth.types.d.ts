import type { Role, UserPublic } from '@dbview/shared';
export interface AuthPrincipal {
    id: string;
    email: string;
    role: Role;
    source: 'jwt' | 'api-key' | 'gateway';
    mustChangePassword?: boolean;
    /** Tenancy scope key forwarded by a trusted gateway (see gateway.ts). */
    tenantKey?: string | null;
}
export declare function toPublicUser(u: {
    id: string;
    email: string;
    displayName: string | null;
    role: Role;
    isActive: boolean;
    createdAt: string;
    lastLoginAt: string | null;
    mustChangePassword: boolean;
}): UserPublic;
//# sourceMappingURL=auth.types.d.ts.map