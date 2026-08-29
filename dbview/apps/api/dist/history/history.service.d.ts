import { OnModuleInit } from '@nestjs/common';
import type { CreateHistoryEntryDto, HistoryEntry, ListHistoryQuery, ListHistoryResponse } from '@dbview/shared';
import { AuthService } from '../auth/auth.service.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
export declare class HistoryService implements OnModuleInit {
    private readonly auth;
    private readonly logger;
    private readonly store;
    constructor(auth: AuthService);
    onModuleInit(): void;
    list(query: ListHistoryQuery, principal: AuthPrincipal): ListHistoryResponse;
    /**
     * Non-throwing record. Logs and swallows on failure so a flaky disk
     * never breaks the user-facing NL2Query flow.
     */
    record(dto: CreateHistoryEntryDto, ownerId: string): HistoryEntry | null;
    setFavorite(id: string, favorite: boolean, principal: AuthPrincipal): HistoryEntry;
    remove(id: string, principal: AuthPrincipal): void;
    clear(principal: AuthPrincipal, connectionId?: string): {
        removed: number;
    };
    clearAll(): {
        removed: number;
    };
    private requireOwned;
    private backfillLegacyOwnership;
}
//# sourceMappingURL=history.service.d.ts.map