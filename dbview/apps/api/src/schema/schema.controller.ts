import { Controller, Get, Param, ParseUUIDPipe, Query } from '@nestjs/common';
import type { UnifiedSchema } from '@dbview/shared';
import { CurrentUser } from '../auth/decorators.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { SchemaService } from './schema.service.js';

@Controller('schema')
export class SchemaController {
  constructor(private readonly svc: SchemaService) {}

  @Get(':connectionId')
  async get(
    @Param('connectionId', ParseUUIDPipe) connectionId: string,
    @CurrentUser() principal: AuthPrincipal,
    @Query('refresh') refresh?: string
  ): Promise<UnifiedSchema> {
    return this.svc.getGraph(connectionId, principal, refresh === '1');
  }
}
