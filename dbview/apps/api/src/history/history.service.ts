import { Injectable, Logger, NotFoundException, OnModuleInit } from '@nestjs/common';
import type {
  CreateHistoryEntryDto,
  HistoryEntry,
  ListHistoryQuery,
  ListHistoryResponse,
} from '@dbview/shared';
import { AuthService } from '../auth/auth.service.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { HistoryStore } from './history.store.js';

@Injectable()
export class HistoryService implements OnModuleInit {
  private readonly logger = new Logger('HistoryService');
  private readonly store = new HistoryStore();

  constructor(private readonly auth: AuthService) {}

  onModuleInit(): void {
    this.backfillLegacyOwnership();
  }

  list(query: ListHistoryQuery, principal: AuthPrincipal): ListHistoryResponse {
    return this.store.list(query, principal.id);
  }

  /**
   * Non-throwing record. Logs and swallows on failure so a flaky disk
   * never breaks the user-facing NL2Query flow.
   */
  record(dto: CreateHistoryEntryDto, ownerId: string): HistoryEntry | null {
    try {
      return this.store.create(dto, ownerId);
    } catch (err) {
      this.logger.warn(`history record failed: ${(err as Error).message}`);
      return null;
    }
  }

  setFavorite(id: string, favorite: boolean, principal: AuthPrincipal): HistoryEntry {
    const existing = this.requireOwned(id, principal);
    const updated = this.store.setFavorite(existing.id, favorite);
    if (!updated) {
      throw new NotFoundException({ code: 'history_not_found', message: `No history ${id}` });
    }
    return updated;
  }

  remove(id: string, principal: AuthPrincipal): void {
    this.requireOwned(id, principal);
    const ok = this.store.remove(id);
    if (!ok) {
      throw new NotFoundException({ code: 'history_not_found', message: `No history ${id}` });
    }
  }

  clear(principal: AuthPrincipal, connectionId?: string): { removed: number } {
    return { removed: this.store.clear(principal.id, connectionId) };
  }

  clearAll(): { removed: number } {
    return { removed: this.store.clearAll() };
  }

  private requireOwned(id: string, principal: AuthPrincipal): HistoryEntry {
    const entry = this.store.get(id);
    if (!entry) {
      throw new NotFoundException({ code: 'history_not_found', message: `No history ${id}` });
    }
    if (entry.ownerId !== principal.id) {
      // Hide existence from non-owners to prevent enumeration.
      throw new NotFoundException({ code: 'history_not_found', message: `No history ${id}` });
    }
    return entry;
  }

  private backfillLegacyOwnership(): void {
    const pending = this.store.pendingLegacyIds();
    if (pending.length === 0) return;
    const admin = this.auth.listUsers().find((u) => u.role === 'admin' && u.isActive);
    if (!admin) {
      this.logger.warn(
        `legacy_history_pending count=${pending.length} no_admin_yet — entries hidden until backfill`
      );
      return;
    }
    for (const id of pending) {
      this.store.reassignOwner(id, admin.id);
    }
    this.logger.log(`legacy_history_migrated count=${pending.length} owner=${admin.id}`);
  }
}
