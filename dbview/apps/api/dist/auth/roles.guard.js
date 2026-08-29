var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ForbiddenError } from '@dbview/shared';
import { IS_PUBLIC_KEY } from '../common/public.decorator.js';
import { ROLES_KEY } from './decorators.js';
let RolesGuard = class RolesGuard {
    reflector;
    constructor(reflector) {
        this.reflector = reflector;
    }
    canActivate(ctx) {
        const isPublic = this.reflector.getAllAndOverride(IS_PUBLIC_KEY, [
            ctx.getHandler(),
            ctx.getClass(),
        ]);
        if (isPublic)
            return true;
        const required = this.reflector.getAllAndOverride(ROLES_KEY, [
            ctx.getHandler(),
            ctx.getClass(),
        ]);
        if (!required || required.length === 0)
            return true;
        const req = ctx.switchToHttp().getRequest();
        const user = req.user;
        if (!user)
            throw new ForbiddenError('Authentication required.');
        if (!required.includes(user.role)) {
            throw new ForbiddenError(`Requires role: ${required.join(' or ')}.`);
        }
        return true;
    }
};
RolesGuard = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [Reflector])
], RolesGuard);
export { RolesGuard };
//# sourceMappingURL=roles.guard.js.map