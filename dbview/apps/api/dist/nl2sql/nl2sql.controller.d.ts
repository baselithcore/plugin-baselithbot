import { type Nl2QueryAskResponse, type Nl2SqlResponse } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { Nl2SqlService } from './nl2sql.service.js';
import { Nl2QueryAskService } from './ask.service.js';
export declare class Nl2SqlController {
    private readonly svc;
    private readonly ask;
    constructor(svc: Nl2SqlService, ask: Nl2QueryAskService);
    translate(body: unknown, principal: AuthPrincipal): Promise<Nl2SqlResponse>;
    askEndpoint(body: unknown, principal: AuthPrincipal): Promise<Nl2QueryAskResponse>;
}
//# sourceMappingURL=nl2sql.controller.d.ts.map