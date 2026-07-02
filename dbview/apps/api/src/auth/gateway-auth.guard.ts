import { CanActivate, ExecutionContext, Injectable, Logger } from '@nestjs/common';
import type { FastifyRequest } from 'fastify';
import type { AuthPrincipal } from './auth.types.js';
import { AuthService } from './auth.service.js';
import {
  GATEWAY_SECRET_HEADER,
  GATEWAY_USER_HEADER,
  isGatewayMode,
  parseGatewayUser,
  verifyGatewaySecret,
} from './gateway.js';

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
@Injectable()
export class GatewayAuthGuard implements CanActivate {
  private readonly logger = new Logger('GatewayAuthGuard');

  constructor(private readonly auth: AuthService) {}

  canActivate(ctx: ExecutionContext): boolean {
    if (!isGatewayMode()) return true;

    const req = ctx.switchToHttp().getRequest<FastifyRequest & { user?: AuthPrincipal }>();
    if (req.user) return true;

    const secret = req.headers[GATEWAY_SECRET_HEADER] as string | undefined;
    if (!verifyGatewaySecret(secret)) return true; // defer to JWT guard

    const claims = parseGatewayUser(req.headers[GATEWAY_USER_HEADER] as string | undefined);
    if (!claims) return true; // authenticated proxy but no identity → defer

    try {
      this.auth.ensureGatewayUser(claims);
    } catch (err) {
      // Mirroring failure must not turn into a 500 storm; the principal is
      // still valid for this request (ownership FKs may lag one write).
      this.logger.warn(`gateway_mirror_failed user=${claims.id}: ${(err as Error).message}`);
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
}
