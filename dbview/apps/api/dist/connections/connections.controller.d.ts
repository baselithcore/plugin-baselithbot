import { type ConnectionSummary, type UploadDumpResponse } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { ConnectionsService } from './connections.service.js';
export declare class ConnectionsController {
    private readonly svc;
    constructor(svc: ConnectionsService);
    list(principal: AuthPrincipal): ConnectionSummary[];
    get(id: string, principal: AuthPrincipal): ConnectionSummary;
    create(dto: unknown, principal: AuthPrincipal): Promise<ConnectionSummary>;
    updateSharing(id: string, body: unknown, principal: AuthPrincipal): ConnectionSummary;
    test(dto: unknown, principal: AuthPrincipal): Promise<{
        ok: true;
    }>;
    uploadDump(dto: unknown): UploadDumpResponse;
    remove(id: string, principal: AuthPrincipal): {
        ok: true;
    };
}
//# sourceMappingURL=connections.controller.d.ts.map