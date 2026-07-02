import { Body, Controller, Delete, Get, Param, Patch, Post } from '@nestjs/common';
import {
  ForbiddenError,
  InviteRequestSchema,
  UpdateUserRequestSchema,
  type InviteRequest,
  type UpdateUserRequest,
  type UserPublic,
} from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { AuthService } from './auth.service.js';
import { CurrentUser, Roles } from './decorators.js';
import { isGatewayMode } from './gateway.js';
import type { AuthPrincipal } from './auth.types.js';

/** In gateway (SSO) mode the user directory is owned by the central IdP. */
function assertLocalUserManagement(): void {
  if (isGatewayMode()) {
    throw new ForbiddenError('Users are managed by the central identity provider.');
  }
}

@Controller('auth/users')
@Roles('admin')
export class UsersController {
  constructor(private readonly auth: AuthService) {}

  @Get()
  list(@CurrentUser() actor: AuthPrincipal): UserPublic[] {
    return this.auth.listUsersVisibleTo(actor);
  }

  @Post()
  invite(
    @Body(new ZodPipe(InviteRequestSchema)) body: InviteRequest,
    @CurrentUser() actor: AuthPrincipal
  ): Promise<UserPublic> {
    assertLocalUserManagement();
    return this.auth.invite(body, actor.id);
  }

  @Patch(':id')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(UpdateUserRequestSchema)) body: UpdateUserRequest,
    @CurrentUser() actor: AuthPrincipal
  ): Promise<UserPublic> {
    assertLocalUserManagement();
    return this.auth.updateUser(id, body, { id: actor.id, role: actor.role });
  }

  @Delete(':id')
  remove(@Param('id') id: string, @CurrentUser() actor: AuthPrincipal): { ok: true } {
    assertLocalUserManagement();
    if (actor.source === 'api-key' && id === 'service') {
      throw new ForbiddenError('Cannot remove service principal.');
    }
    this.auth.deleteUser(id, actor.id);
    return { ok: true };
  }
}
