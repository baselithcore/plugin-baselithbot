import { OnModuleInit } from '@nestjs/common';
import { type ConnectionSummary, type CreateConnectionDto, type Dialect, type UpdateConnectionSharingDto, type UploadDumpRequest, type UploadDumpResponse } from '@dbview/shared';
import { EnginePool } from '../engine/engine-pool.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { AuthService } from '../auth/auth.service.js';
export declare class ConnectionsService implements OnModuleInit {
    private readonly auth;
    private readonly enginePool;
    private readonly logger;
    private readonly store;
    constructor(auth: AuthService, enginePool: EnginePool);
    onModuleInit(): void;
    list(principal: AuthPrincipal): ConnectionSummary[];
    get(id: string, principal: AuthPrincipal): ConnectionSummary;
    create(dto: CreateConnectionDto, principal: AuthPrincipal): Promise<ConnectionSummary>;
    updateSharing(id: string, dto: UpdateConnectionSharingDto, principal: AuthPrincipal): ConnectionSummary;
    remove(id: string, principal: AuthPrincipal): void;
    test(dto: CreateConnectionDto, principal: AuthPrincipal): Promise<{
        ok: true;
    }>;
    uploadDump(req: UploadDumpRequest): UploadDumpResponse;
    resolvePlain(id: string, principal: AuthPrincipal): {
        dialect: Dialect;
        connectionString: string;
    };
    /**
     * Read visibility. Ownership is enforced even for admins: `private` means
     * truly private to the owner. Other modes:
     *   - `admins` → every admin sees it (operational co-op default)
     *   - `all`    → every authenticated user sees it
     *   - `users`  → owner + explicitly listed userIds
     *
     * Mirrors `canResolve` — if you can see the summary you can also resolve
     * the credentials needed to run a query. Splitting them would only confuse
     * users (visible-but-unusable connections).
     */
    private canView;
    /**
     * Audit hook for admin mutations on connections they do not own. We
     * deliberately keep cross-admin mutation allowed for operational recovery
     * (deactivated owners, orphaned connections) but log the event so the
     * audit trail is explicit about who changed someone else's resource.
     */
    private logCrossAdminMutation;
    private requireById;
    private validateSharing;
    /**
     * Two-phase migration run on boot:
     *
     *   1. Pre-tenant-isolation entries (no `ownerId`/`sharing`) are re-attached
     *      to the first admin and locked down to `private`. Non-admins cannot
     *      inherit the previous global visibility; the owning admin can re-share
     *      via PATCH /api/connections/:id/sharing.
     *
     *   2. v1 `private` entries with a valid owner are re-tagged to `admins` so
     *      cross-admin visibility (the v1 implicit behavior) is preserved under
     *      v2 semantics where `private` is strictly owner-only. Without this,
     *      installations with multiple admins would silently lose access on
     *      upgrade. Owners can re-tighten to `private` at any time.
     */
    private backfillLegacyOwnership;
    private materialize;
    private assertReachable;
}
//# sourceMappingURL=connections.service.d.ts.map