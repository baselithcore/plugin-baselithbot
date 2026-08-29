import { OnModuleInit } from '@nestjs/common';
import { type InviteRequest, type RegisterRequest, type UpdateUserRequest, type UserPublic } from '@dbview/shared';
import { type StoredUser } from './users.store.js';
import { type GatewayUser } from './gateway.js';
export interface LoginContext {
    ip: string | null;
    userAgent: string | null;
}
export interface LoginResult {
    accessToken: string;
    expiresIn: number;
    refreshToken: string;
    refreshExpiresAt: number;
    user: UserPublic;
}
export declare class AuthService implements OnModuleInit {
    private readonly logger;
    private readonly users;
    private readonly sessions;
    onModuleInit(): Promise<void>;
    /**
     * JIT-mirror a gateway-authenticated identity into the local users store so
     * ownership FKs (connections.ownerId, history.ownerId, llm credentials)
     * resolve. Rows carry an unverifiable password sentinel — they can never be
     * used for local login. Persisted only when a field actually drifts.
     */
    ensureGatewayUser(claims: GatewayUser): void;
    login(email: string, password: string, ctx: LoginContext): Promise<LoginResult>;
    rotate(rawRefresh: string, ctx: LoginContext): LoginResult;
    isRegistrationEnabled(): boolean;
    register(req: RegisterRequest, ctx: LoginContext): Promise<LoginResult>;
    logout(rawRefresh: string | null): void;
    getUser(id: string): StoredUser | undefined;
    listUsers(): UserPublic[];
    /**
     * Users visible to `principal` for admin listing / sharing pickers. In
     * gateway mode visibility is confined to the principal's tenancy scope key
     * (cross-tenant identities must never leak); locally it is the full list.
     */
    listUsersVisibleTo(principal: {
        tenantKey?: string | null;
    }): UserPublic[];
    /** Whether `userId` belongs to the same tenancy scope as `principal`. */
    sameTenant(userId: string, principal: {
        id: string;
        tenantKey?: string | null;
    }): boolean;
    invite(req: InviteRequest, actorId: string): Promise<UserPublic>;
    updateUser(id: string, req: UpdateUserRequest, actor: {
        id: string;
        role: 'admin' | 'user';
    }): Promise<UserPublic>;
    changePassword(userId: string, currentPassword: string, newPassword: string): Promise<UserPublic>;
    deleteUser(id: string, actorId: string): void;
    private issueSession;
    private bootstrapAdmin;
}
export declare const refreshCookieTtl: number;
//# sourceMappingURL=auth.service.d.ts.map