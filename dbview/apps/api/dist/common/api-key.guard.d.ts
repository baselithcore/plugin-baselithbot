import { CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
/**
 * Optional service-to-service API key gate. Active when DBVIEW_API_KEY is set.
 * On match, attaches a synthetic admin principal so JWT guard can short-circuit.
 * Never throws — absence is handled by the JWT guard.
 */
export declare class ApiKeyGuard implements CanActivate {
    private readonly reflector;
    private readonly expected;
    constructor(reflector: Reflector);
    canActivate(ctx: ExecutionContext): boolean;
}
//# sourceMappingURL=api-key.guard.d.ts.map