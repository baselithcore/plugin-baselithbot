import { Body, Controller, Delete, Get, Param, Patch, Query } from '@nestjs/common';
import {
  ListHistoryQuerySchema,
  ToggleFavoriteDtoSchema,
  type HistoryEntry,
  type ListHistoryResponse,
} from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser, Roles } from '../auth/decorators.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { HistoryService } from './history.service.js';

@Controller('history')
export class HistoryController {
  constructor(private readonly svc: HistoryService) {}

  @Get()
  list(
    @Query(new ZodPipe(ListHistoryQuerySchema)) q: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): ListHistoryResponse {
    return this.svc.list(q as never, principal);
  }

  @Patch(':id/favorite')
  toggleFavorite(
    @Param('id') id: string,
    @Body(new ZodPipe(ToggleFavoriteDtoSchema)) body: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): HistoryEntry {
    const { favorite } = body as { favorite: boolean };
    return this.svc.setFavorite(id, favorite, principal);
  }

  // IMPORTANT: declare `:all` admin-nuke BEFORE the wildcard `:id` route, otherwise
  // `DELETE /api/history/all` matches `remove(':id')` first and never reaches clearAll.
  @Delete('all')
  @Roles('admin')
  clearAll(): { removed: number } {
    return this.svc.clearAll();
  }

  @Delete(':id')
  remove(@Param('id') id: string, @CurrentUser() principal: AuthPrincipal): { ok: true } {
    this.svc.remove(id, principal);
    return { ok: true };
  }

  @Delete()
  clear(
    @CurrentUser() principal: AuthPrincipal,
    @Query('connectionId') connectionId?: string,
  ): { removed: number } {
    return this.svc.clear(principal, connectionId);
  }
}
