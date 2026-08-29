var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable, Logger } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { GATEWAY_SECRET_HEADER, GATEWAY_USER_HEADER, isGatewayMode, parseGatewayUser, verifyGatewaySecret, } from './gateway.js';
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
let GatewayAuthGuard = class GatewayAuthGuard {
    auth;
    logger = new Logger('GatewayAuthGuard');
    constructor(auth) {
        this.auth = auth;
    }
    canActivate(ctx) {
        if (!isGatewayMode())
            return true;
        const req = ctx.switchToHttp().getRequest();
        if (req.user)
            return true;
        const secret = req.headers[GATEWAY_SECRET_HEADER];
        if (!verifyGatewaySecret(secret))
            return true; // defer to JWT guard
        const claims = parseGatewayUser(req.headers[GATEWAY_USER_HEADER]);
        if (!claims)
            return true; // authenticated proxy but no identity → defer
        try {
            this.auth.ensureGatewayUser(claims);
        }
        catch (err) {
            // Mirroring failure must not turn into a 500 storm; the principal is
            // still valid for this request (ownership FKs may lag one write).
            this.logger.warn(`gateway_mirror_failed user=${claims.id}: ${err.message}`);
        }
        req.user = {
            id: claims.id,
            email: claims.email,
            role: claims.role,
            source: 'gateway',
            tenantKey: claims.tenantKey,
        };
        return true;
    }
};
GatewayAuthGuard = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [AuthService])
], GatewayAuthGuard);
export { GatewayAuthGuard };
//# sourceMappingURL=gateway-auth.guard.js.map