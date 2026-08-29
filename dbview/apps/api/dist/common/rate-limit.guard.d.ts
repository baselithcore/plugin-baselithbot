import { CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
export interface RateLimitConfig {
    /** Max requests per window. */
    limit: number;
    /** Window in seconds. */
    windowSec: number;
}
export declare const RateLimit: (cfg: RateLimitConfig) => import("@nestjs/common").CustomDecorator<string>;
export declare class RateLimitGuard implements CanActivate {
    private readonly reflector;
    private readonly logger;
    private readonly buckets;
    constructor(reflector: Reflector);
    canActivate(ctx: ExecutionContext): boolean;
}
//# sourceMappingURL=rate-limit.guard.d.ts.map