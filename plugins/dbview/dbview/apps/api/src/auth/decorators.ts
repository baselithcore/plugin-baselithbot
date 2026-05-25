import { SetMetadata, createParamDecorator, type ExecutionContext } from '@nestjs/common';
import type { FastifyRequest } from 'fastify';
import type { Role } from '@dbview/shared';
import type { AuthPrincipal } from './auth.types.js';

export const ROLES_KEY = 'dbview:roles';
export const Roles = (...roles: Role[]): MethodDecorator & ClassDecorator =>
  SetMetadata(ROLES_KEY, roles);

export const CurrentUser = createParamDecorator((_: unknown, ctx: ExecutionContext) => {
  const req = ctx.switchToHttp().getRequest<FastifyRequest & { user?: AuthPrincipal }>();
  return req.user;
});
