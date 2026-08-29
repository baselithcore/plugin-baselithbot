import type { CreateHistoryEntryDto, HistoryEntry, ListHistoryQuery } from '@dbview/shared';
/**
 * JSON-file store for NL2Query history + favorites. Mirrors the
 * ConnectionsStore pattern: in-memory map, atomic write, tmp+rename.
 *
 * Each entry carries an `ownerId` — list/clear filter strictly by owner so
 * users only ever see their own history. Pre-tenant-isolation entries
 * without `ownerId` are backfilled to the first admin on boot (same as
 * `ConnectionsStore`).
 *
 * Entries are capped at MAX_ENTRIES; non-favorite oldest entries get
 * evicted first so a starred query is never lost to rotation.
 */
export declare class HistoryStore {
    private entries;
    private legacyIds;
    private byOwner;
    private readonly filePath;
    constructor(filePath?: string);
    list(query: ListHistoryQuery, ownerId: string): {
        entries: HistoryEntry[];
        total: number;
    };
    get(id: string): HistoryEntry | undefined;
    create(dto: CreateHistoryEntryDto, ownerId: string): HistoryEntry;
    setFavorite(id: string, favorite: boolean): HistoryEntry | undefined;
    remove(id: string): boolean;
    clear(ownerId: string, connectionId?: string): number;
    /**
     * Admin-only nuke: wipe every entry across all users, including favorites.
     * Bypasses the owner scope. Used by `DELETE /api/history/all`.
     */
    clearAll(): number;
    pendingLegacyIds(): string[];
    reassignOwner(id: string, ownerId: string): void;
    private indexAdd;
    private indexRemove;
    private evictIfOver;
    private load;
    private persist;
}
//# sourceMappingURL=history.store.d.ts.map