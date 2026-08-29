import { CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
export declare class JwtAuthGuard implements CanActivate {
    private readonly reflector;
    constructor(reflector: Reflector);
    canActivate(ctx: ExecutionContext): boolean;
}
//# sourceMappingURL=jwt-auth.guard.d.ts.map