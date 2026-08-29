import type { ConnectionConfig } from '@dbview/shared';
export interface StoredConnection extends ConnectionConfig {
    connectionStringCipher: string;
}
/**
 * Persistence schema versions:
 * - 1: pre-tenant-isolation. Some entries lack `ownerId`/`sharing` (legacy).
 *      All admins implicitly saw every connection — `private` meant nothing
 *      between admins.
 * - 2: ownership is enforced. `private` is strictly owner-only. Entries that
 *      were `private` under v1 are migrated to `admins` to preserve the
 *      operational expectation that other admins could see them.
 */
type SchemaVersion = 1 | 2;
export declare class ConnectionsStore {
    private connections;
    private legacyIds;
    private privateUpgradeIds;
    private loadedVersion;
    private readonly filePath;
    constructor(filePath?: string);
    list(): StoredConnection[];
    get(id: string): StoredConnection | undefined;
    upsert(c: StoredConnection): void;
    remove(id: string): boolean;
    /**
     * Returns ids of entries loaded without `ownerId`/`sharing` — they were
     * written before tenant isolation existed. Service backfills these on
     * boot using the first admin as fallback owner.
     */
    pendingLegacyIds(): string[];
    /**
     * Ids of v1 entries that were `sharing.mode === 'private'` at load time.
     * Under v1 semantics every admin still saw them; v2 makes `private` truly
     * owner-only, so to avoid a regression for installs with >1 admin these
     * are re-tagged `admins` by the service on first boot.
     */
    pendingPrivateUpgradeIds(): string[];
    loadedSchemaVersion(): SchemaVersion;
    private load;
    private persist;
}
export {};
//# sourceMappingURL=connections.store.d.ts.map