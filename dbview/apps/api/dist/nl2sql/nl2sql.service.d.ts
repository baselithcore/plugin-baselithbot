import { type Nl2SqlRequest, type Nl2SqlResponse } from '@dbview/shared';
import { SchemaService } from '../schema/schema.service.js';
import { ConnectionsService } from '../connections/connections.service.js';
import { LlmGovernanceService } from '../llm/governance.service.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
export declare class Nl2SqlService {
    private readonly connections;
    private readonly schema;
    private readonly governance;
    private readonly logger;
    private readonly sqlValidator;
    private readonly cypherValidator;
    private readonly soqlValidator;
    private readonly sdcValidator;
    constructor(connections: ConnectionsService, schema: SchemaService, governance: LlmGovernanceService);
    translate(req: Nl2SqlRequest, principal: AuthPrincipal): Promise<Nl2SqlResponse>;
    private validate;
}
//# sourceMappingURL=nl2sql.service.d.ts.map