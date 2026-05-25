import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ForbiddenError } from '@dbview/shared';
import type { FastifyRequest } from 'fastify';
import type { Role } from '@dbview/shared';
import { IS_PUBLIC_KEY } from '../common/public.decorator.js';
import { ROLES_KEY } from './decorators.js';
import type { AuthPrincipal } from './auth.types.js';

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(ctx: ExecutionContext): boolean {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      ctx.getHandler(),
      ctx.getClass(),
    ]);
    if (isPublic) return true;

    const required = this.reflector.getAllAndOverride<Role[] | undefined>(ROLES_KEY, [
      ctx.getHandler(),
      ctx.getClass(),
    ]);
    if (!required || required.length === 0) return true;

    const req = ctx.switchToHttp().getRequest<FastifyRequest & { user?: AuthPrincipal }>();
    const user = req.user;
    if (!user) throw new ForbiddenError('Authentication required.');
    if (!required.includes(user.role)) {
      throw new ForbiddenError(`Requires role: ${required.join(' or ')}.`);
    }
    return true;
  }
}
