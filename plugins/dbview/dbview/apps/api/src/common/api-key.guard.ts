import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { timingSafeEqual } from 'node:crypto';
import type { FastifyRequest } from 'fastify';
import { IS_PUBLIC_KEY } from './public.decorator.js';
import type { AuthPrincipal } from '../auth/auth.types.js';

/**
 * Optional service-to-service API key gate. Active when DBVIEW_API_KEY is set.
 * On match, attaches a synthetic admin principal so JWT guard can short-circuit.
 * Never throws — absence is handled by the JWT guard.
 */
@Injectable()
export class ApiKeyGuard implements CanActivate {
  private readonly expected = process.env.DBVIEW_API_KEY ?? '';

  constructor(private readonly reflector: Reflector) {}

  canActivate(ctx: ExecutionContext): boolean {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      ctx.getHandler(),
      ctx.getClass(),
    ]);
    if (isPublic) return true;

    if (!this.expected) return true; // no key configured, defer to JWT guard

    const req = ctx.switchToHttp().getRequest<FastifyRequest & { user?: AuthPrincipal }>();
    const provided = (req.headers['x-api-key'] as string | undefined) ?? '';
    if (provided && safeEqual(provided, this.expected)) {
      req.user = {
        id: 'service',
        email: 'service@dbview.local',
        role: 'admin',
        source: 'api-key',
      };
    }
    return true;
  }
}

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}
