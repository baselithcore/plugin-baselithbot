var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable, Logger, NotFoundException } from '@nestjs/common';
import { AuthService } from '../auth/auth.service.js';
import { HistoryStore } from './history.store.js';
let HistoryService = class HistoryService {
    auth;
    logger = new Logger('HistoryService');
    store = new HistoryStore();
    constructor(auth) {
        this.auth = auth;
    }
    onModuleInit() {
        this.backfillLegacyOwnership();
    }
    list(query, principal) {
        return this.store.list(query, principal.id);
    }
    /**
     * Non-throwing record. Logs and swallows on failure so a flaky disk
     * never breaks the user-facing NL2Query flow.
     */
    record(dto, ownerId) {
        try {
            return this.store.create(dto, ownerId);
        }
        catch (err) {
            this.logger.warn(`history record failed: ${err.message}`);
            return null;
        }
    }
    setFavorite(id, favorite, principal) {
        const existing = this.requireOwned(id, principal);
        const updated = this.store.setFavorite(existing.id, favorite);
        if (!updated) {
            throw new NotFoundException({ code: 'history_not_found', message: `No history ${id}` });
        }
        return updated;
    }
    remove(id, principal) {
        this.requireOwned(id, principal);
        const ok = this.store.remove(id);
        if (!ok) {
            throw new NotFoundException({ code: 'history_not_found', message: `No history ${id}` });
        }
    }
    clear(principal, connectionId) {
        return { removed: this.store.clear(principal.id, connectionId) };
    }
    clearAll() {
        return { removed: this.store.clearAll() };
    }
    requireOwned(id, principal) {
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
    backfillLegacyOwnership() {
        const pending = this.store.pendingLegacyIds();
        if (pending.length === 0)
            return;
        const admin = this.auth.listUsers().find((u) => u.role === 'admin' && u.isActive);
        if (!admin) {
            this.logger.warn(`legacy_history_pending count=${pending.length} no_admin_yet — entries hidden until backfill`);
            return;
        }
        for (const id of pending) {
            this.store.reassignOwner(id, admin.id);
        }
        this.logger.log(`legacy_history_migrated count=${pending.length} owner=${admin.id}`);
    }
};
HistoryService = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [AuthService])
], HistoryService);
export { HistoryService };
//# sourceMappingURL=history.service.js.map