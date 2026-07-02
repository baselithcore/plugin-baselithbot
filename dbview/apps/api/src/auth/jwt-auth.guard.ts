import { CanActivate, ExecutionContext, ForbiddenException, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { UnauthorizedError } from '@dbview/shared';
import type { FastifyRequest } from 'fastify';
import { IS_PUBLIC_KEY } from '../common/public.decorator.js';
import { ALLOW_PASSWORD_CHANGE_KEY } from '../common/password-change.decorator.js';
import { verifyAccessToken } from './tokens.js';
import type { AuthPrincipal } from './auth.types.js';

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(ctx: ExecutionContext): boolean {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      ctx.getHandler(),
      ctx.getClass(),
    ]);
    if (isPublic) return true;

    const req = ctx.switchToHttp().getRequest<FastifyRequest & { user?: AuthPrincipal }>();
    if (!req.user) {
      const header = req.headers.authorization;
      if (!header || !header.toLowerCase().startsWith('bearer ')) {
        throw new UnauthorizedError('Bearer access token required.');
      }
      const token = header.slice(7).trim();
      try {
        const claims = verifyAccessToken(token);
        req.user = {
          id: claims.sub,
          email: claims.email,
          role: claims.role,
          source: 'jwt',
          mustChangePassword: claims.mustChangePassword,
        };
      } catch {
        throw new UnauthorizedError('Invalid or expired access token.');
      }
    }

    if (req.user.mustChangePassword) {
      const allowed = this.reflector.getAllAndOverride<boolean>(ALLOW_PASSWORD_CHANGE_KEY, [
        ctx.getHandler(),
        ctx.getClass(),
      ]);
      if (!allowed) {
        throw new ForbiddenException({
          code: 'password_change_required',
          message: 'Password change required before accessing this resource.',
        });
      }
    }
    return true;
  }
}
