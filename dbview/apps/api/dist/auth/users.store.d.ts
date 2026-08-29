import type { Role } from '@dbview/shared';
export interface StoredUser {
    id: string;
    email: string;
    emailLower: string;
    passwordHash: string;
    displayName: string | null;
    role: Role;
    isActive: boolean;
    createdAt: string;
    lastLoginAt: string | null;
    mustChangePassword: boolean;
    /** 'gateway' for rows JIT-mirrored from a central IdP; absent = local. */
    source?: 'local' | 'gateway';
    /** Tenancy scope key of the mirroring gateway identity (see gateway.ts). */
    tenantKey?: string | null;
}
export declare class UsersStore {
    private byId;
    private byEmail;
    private readonly filePath;
    constructor(filePath?: string);
    list(): StoredUser[];
    count(): number;
    get(id: string): StoredUser | undefined;
    findByEmail(email: string): StoredUser | undefined;
    upsert(u: StoredUser): void;
    remove(id: string): boolean;
    private load;
    private persist;
}
//# sourceMappingURL=users.store.d.ts.map