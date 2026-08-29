var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
import { Body, Controller, Delete, Get, Param, Patch, Query } from '@nestjs/common';
import { ListHistoryQuerySchema, ToggleFavoriteDtoSchema, } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser, Roles } from '../auth/decorators.js';
import { HistoryService } from './history.service.js';
let HistoryController = class HistoryController {
    svc;
    constructor(svc) {
        this.svc = svc;
    }
    list(q, principal) {
        return this.svc.list(q, principal);
    }
    toggleFavorite(id, body, principal) {
        const { favorite } = body;
        return this.svc.setFavorite(id, favorite, principal);
    }
    // IMPORTANT: declare `:all` admin-nuke BEFORE the wildcard `:id` route, otherwise
    // `DELETE /api/history/all` matches `remove(':id')` first and never reaches clearAll.
    clearAll() {
        return this.svc.clearAll();
    }
    remove(id, principal) {
        this.svc.remove(id, principal);
        return { ok: true };
    }
    clear(principal, connectionId) {
        return this.svc.clear(principal, connectionId);
    }
};
__decorate([
    Get(),
    __param(0, Query(new ZodPipe(ListHistoryQuerySchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Object)
], HistoryController.prototype, "list", null);
__decorate([
    Patch(':id/favorite'),
    __param(0, Param('id')),
    __param(1, Body(new ZodPipe(ToggleFavoriteDtoSchema))),
    __param(2, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object, Object]),
    __metadata("design:returntype", Object)
], HistoryController.prototype, "toggleFavorite", null);
__decorate([
    Delete('all'),
    Roles('admin'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Object)
], HistoryController.prototype, "clearAll", null);
__decorate([
    Delete(':id'),
    __param(0, Param('id')),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Object)
], HistoryController.prototype, "remove", null);
__decorate([
    Delete(),
    __param(0, CurrentUser()),
    __param(1, Query('connectionId')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, String]),
    __metadata("design:returntype", Object)
], HistoryController.prototype, "clear", null);
HistoryController = __decorate([
    Controller('history'),
    __metadata("design:paramtypes", [HistoryService])
], HistoryController);
export { HistoryController };
//# sourceMappingURL=history.controller.js.map