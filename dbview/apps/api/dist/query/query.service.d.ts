import { type ExecuteQueryRequest, type ExecuteQueryResponse, type SampleRequest } from '@dbview/shared';
import { ConnectionsService } from '../connections/connections.service.js';
import { SchemaService } from '../schema/schema.service.js';
import { EnginePool } from '../engine/engine-pool.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
export declare class QueryService {
    private readonly connections;
    private readonly schema;
    private readonly enginePool;
    private readonly sqlValidator;
    private readonly cypherValidator;
    private readonly soqlValidator;
    private readonly sdcValidator;
    constructor(connections: ConnectionsService, schema: SchemaService, enginePool: EnginePool);
    /**
     * Run a function with a query engine, preferring a pooled instance when the
     * dialect supports it. Non-pooled engines are closed after use; pooled ones
     * stay open and are managed by `EnginePool`.
     */
    private withEngine;
    sample(req: SampleRequest, principal: AuthPrincipal): Promise<ExecuteQueryResponse>;
    execute(req: ExecuteQueryRequest, principal: AuthPrincipal): Promise<ExecuteQueryResponse>;
}
//# sourceMappingURL=query.service.d.ts.map