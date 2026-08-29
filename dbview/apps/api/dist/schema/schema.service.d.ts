import { type UnifiedSchema } from '@dbview/shared';
import { ConnectionsService } from '../connections/connections.service.js';
import { EnginePool } from '../engine/engine-pool.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
export declare class SchemaService {
    private readonly connections;
    private readonly enginePool;
    private readonly logger;
    private readonly cache;
    constructor(connections: ConnectionsService, enginePool: EnginePool);
    getGraph(connectionId: string, principal: AuthPrincipal, force?: boolean): Promise<UnifiedSchema>;
    invalidate(connectionId: string): void;
}
//# sourceMappingURL=schema.service.d.ts.map