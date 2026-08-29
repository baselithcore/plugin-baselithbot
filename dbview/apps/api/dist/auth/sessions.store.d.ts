export interface StoredSession {
    id: string;
    tokenHash: string;
    familyId: string;
    userId: string;
    issuedAt: number;
    expiresAt: number;
    revokedAt: number | null;
    replacedBy: string | null;
    userAgent: string | null;
    ip: string | null;
}
export declare class SessionsStore {
    private byId;
    private byHash;
    private byUserId;
    private byFamilyId;
    private readonly filePath;
    constructor(filePath?: string);
    findByHash(hash: string): StoredSession | undefined;
    insert(s: StoredSession): void;
    update(s: StoredSession): void;
    revokeFamily(familyId: string, when: number): number;
    revokeAllForUser(userId: string, when: number): number;
    purgeExpired(now: number): number;
    private indexAdd;
    private indexRemove;
    private load;
    private persist;
}
//# sourceMappingURL=sessions.store.d.ts.map