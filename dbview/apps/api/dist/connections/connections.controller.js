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
import { Body, Controller, Delete, Get, Param, ParseUUIDPipe, Patch, Post } from '@nestjs/common';
import { CreateConnectionSchema, UpdateConnectionSharingSchema, UploadDumpRequestSchema, } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser, Roles } from '../auth/decorators.js';
import { ConnectionsService } from './connections.service.js';
let ConnectionsController = class ConnectionsController {
    svc;
    constructor(svc) {
        this.svc = svc;
    }
    list(principal) {
        return this.svc.list(principal);
    }
    get(id, principal) {
        return this.svc.get(id, principal);
    }
    create(dto, principal) {
        return this.svc.create(dto, principal);
    }
    updateSharing(id, body, principal) {
        return this.svc.updateSharing(id, body, principal);
    }
    test(dto, principal) {
        return this.svc.test(dto, principal);
    }
    uploadDump(dto) {
        return this.svc.uploadDump(dto);
    }
    remove(id, principal) {
        this.svc.remove(id, principal);
        return { ok: true };
    }
};
__decorate([
    Get(),
    __param(0, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Array)
], ConnectionsController.prototype, "list", null);
__decorate([
    Get(':id'),
    __param(0, Param('id', ParseUUIDPipe)),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Object)
], ConnectionsController.prototype, "get", null);
__decorate([
    Post(),
    Roles('admin'),
    __param(0, Body(new ZodPipe(CreateConnectionSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], ConnectionsController.prototype, "create", null);
__decorate([
    Patch(':id/sharing'),
    Roles('admin'),
    __param(0, Param('id', ParseUUIDPipe)),
    __param(1, Body(new ZodPipe(UpdateConnectionSharingSchema))),
    __param(2, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object, Object]),
    __metadata("design:returntype", Object)
], ConnectionsController.prototype, "updateSharing", null);
__decorate([
    Post('test'),
    Roles('admin'),
    __param(0, Body(new ZodPipe(CreateConnectionSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], ConnectionsController.prototype, "test", null);
__decorate([
    Post('upload-dump'),
    Roles('admin'),
    __param(0, Body(new ZodPipe(UploadDumpRequestSchema))),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Object)
], ConnectionsController.prototype, "uploadDump", null);
__decorate([
    Delete(':id'),
    Roles('admin'),
    __param(0, Param('id', ParseUUIDPipe)),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Object)
], ConnectionsController.prototype, "remove", null);
ConnectionsController = __decorate([
    Controller('connections'),
    __metadata("design:paramtypes", [ConnectionsService])
], ConnectionsController);
export { ConnectionsController };
//# sourceMappingURL=connections.controller.js.map