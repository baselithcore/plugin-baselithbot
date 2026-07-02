import { Body, Controller, Delete, Get, Param, ParseUUIDPipe, Patch, Post } from '@nestjs/common';
import {
  CreateConnectionSchema,
  UpdateConnectionSharingSchema,
  UploadDumpRequestSchema,
  type ConnectionSummary,
  type UploadDumpResponse,
} from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser, Roles } from '../auth/decorators.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { ConnectionsService } from './connections.service.js';

@Controller('connections')
export class ConnectionsController {
  constructor(private readonly svc: ConnectionsService) {}

  @Get()
  list(@CurrentUser() principal: AuthPrincipal): ConnectionSummary[] {
    return this.svc.list(principal);
  }

  @Get(':id')
  get(
    @Param('id', ParseUUIDPipe) id: string,
    @CurrentUser() principal: AuthPrincipal,
  ): ConnectionSummary {
    return this.svc.get(id, principal);
  }

  @Post()
  @Roles('admin')
  create(
    @Body(new ZodPipe(CreateConnectionSchema)) dto: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): Promise<ConnectionSummary> {
    return this.svc.create(dto as never, principal);
  }

  @Patch(':id/sharing')
  @Roles('admin')
  updateSharing(
    @Param('id', ParseUUIDPipe) id: string,
    @Body(new ZodPipe(UpdateConnectionSharingSchema)) body: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): ConnectionSummary {
    return this.svc.updateSharing(id, body as never, principal);
  }

  @Post('test')
  @Roles('admin')
  test(
    @Body(new ZodPipe(CreateConnectionSchema)) dto: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): Promise<{ ok: true }> {
    return this.svc.test(dto as never, principal);
  }

  @Post('upload-dump')
  @Roles('admin')
  uploadDump(@Body(new ZodPipe(UploadDumpRequestSchema)) dto: unknown): UploadDumpResponse {
    return this.svc.uploadDump(dto as never);
  }

  @Delete(':id')
  @Roles('admin')
  remove(
    @Param('id', ParseUUIDPipe) id: string,
    @CurrentUser() principal: AuthPrincipal,
  ): { ok: true } {
    this.svc.remove(id, principal);
    return { ok: true };
  }
}
