import { type ExecuteQueryResponse } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { QueryService } from './query.service.js';
export declare class QueryController {
    private readonly svc;
    constructor(svc: QueryService);
    execute(body: unknown, principal: AuthPrincipal): Promise<ExecuteQueryResponse>;
    sample(body: unknown, principal: AuthPrincipal): Promise<ExecuteQueryResponse>;
}
//# sourceMappingURL=query.controller.d.ts.map