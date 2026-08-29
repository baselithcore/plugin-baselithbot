import { CanActivate, ExecutionContext } from '@nestjs/common';
import { AuthService } from './auth.service.js';
/**
 * Trusted-gateway authentication. Registered as the FIRST global guard so a
 * verified forwarded identity short-circuits the JWT guard (which honours an
 * already-attached `req.user`), exactly like ApiKeyGuard does.
 *
 * Never throws: on missing/invalid gateway headers it simply defers — the
 * request continues unauthenticated and JwtAuthGuard applies its normal
 * policy (@Public passes, everything else 401s). Inert unless gateway mode
 * is enabled (see gateway.ts).
 */
export declare class GatewayAuthGuard implements CanActivate {
    private readonly auth;
    private readonly logger;
    constructor(auth: AuthService);
    canActivate(ctx: ExecutionContext): boolean;
}
//# sourceMappingURL=gateway-auth.guard.d.ts.map