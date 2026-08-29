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
import { Body, Controller, Delete, Get, Param, Patch, Post } from '@nestjs/common';
import { ForbiddenError, InviteRequestSchema, UpdateUserRequestSchema, } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { AuthService } from './auth.service.js';
import { CurrentUser, Roles } from './decorators.js';
import { isGatewayMode } from './gateway.js';
/** In gateway (SSO) mode the user directory is owned by the central IdP. */
function assertLocalUserManagement() {
    if (isGatewayMode()) {
        throw new ForbiddenError('Users are managed by the central identity provider.');
    }
}
let UsersController = class UsersController {
    auth;
    constructor(auth) {
        this.auth = auth;
    }
    list(actor) {
        return this.auth.listUsersVisibleTo(actor);
    }
    invite(body, actor) {
        assertLocalUserManagement();
        return this.auth.invite(body, actor.id);
    }
    update(id, body, actor) {
        assertLocalUserManagement();
        return this.auth.updateUser(id, body, { id: actor.id, role: actor.role });
    }
    remove(id, actor) {
        assertLocalUserManagement();
        if (actor.source === 'api-key' && id === 'service') {
            throw new ForbiddenError('Cannot remove service principal.');
        }
        this.auth.deleteUser(id, actor.id);
        return { ok: true };
    }
};
__decorate([
    Get(),
    __param(0, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Array)
], UsersController.prototype, "list", null);
__decorate([
    Post(),
    __param(0, Body(new ZodPipe(InviteRequestSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], UsersController.prototype, "invite", null);
__decorate([
    Patch(':id'),
    __param(0, Param('id')),
    __param(1, Body(new ZodPipe(UpdateUserRequestSchema))),
    __param(2, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object, Object]),
    __metadata("design:returntype", Promise)
], UsersController.prototype, "update", null);
__decorate([
    Delete(':id'),
    __param(0, Param('id')),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Object)
], UsersController.prototype, "remove", null);
UsersController = __decorate([
    Controller('auth/users'),
    Roles('admin'),
    __metadata("design:paramtypes", [AuthService])
], UsersController);
export { UsersController };
//# sourceMappingURL=users.controller.js.map