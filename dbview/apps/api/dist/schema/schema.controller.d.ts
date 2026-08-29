import type { UnifiedSchema } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { SchemaService } from './schema.service.js';
export declare class SchemaController {
    private readonly svc;
    constructor(svc: SchemaService);
    get(connectionId: string, principal: AuthPrincipal, refresh?: string): Promise<UnifiedSchema>;
}
//# sourceMappingURL=schema.controller.d.ts.map