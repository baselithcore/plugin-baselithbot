import { type HistoryEntry, type ListHistoryResponse } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { HistoryService } from './history.service.js';
export declare class HistoryController {
    private readonly svc;
    constructor(svc: HistoryService);
    list(q: unknown, principal: AuthPrincipal): ListHistoryResponse;
    toggleFavorite(id: string, body: unknown, principal: AuthPrincipal): HistoryEntry;
    clearAll(): {
        removed: number;
    };
    remove(id: string, principal: AuthPrincipal): {
        ok: true;
    };
    clear(principal: AuthPrincipal, connectionId?: string): {
        removed: number;
    };
}
//# sourceMappingURL=history.controller.d.ts.map