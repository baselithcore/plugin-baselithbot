var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { ForbiddenException, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { UnauthorizedError } from '@dbview/shared';
import { IS_PUBLIC_KEY } from '../common/public.decorator.js';
import { ALLOW_PASSWORD_CHANGE_KEY } from '../common/password-change.decorator.js';
import { verifyAccessToken } from './tokens.js';
let JwtAuthGuard = class JwtAuthGuard {
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
        const req = ctx.switchToHttp().getRequest();
        if (!req.user) {
            const header = req.headers.authorization;
            if (!header || !header.toLowerCase().startsWith('bearer ')) {
                throw new UnauthorizedError('Bearer access token required.');
            }
            const token = header.slice(7).trim();
            try {
                const claims = verifyAccessToken(token);
                req.user = {
                    id: claims.sub,
                    email: claims.email,
                    role: claims.role,
                    source: 'jwt',
                    mustChangePassword: claims.mustChangePassword,
                };
            }
            catch {
                throw new UnauthorizedError('Invalid or expired access token.');
            }
        }
        if (req.user.mustChangePassword) {
            const allowed = this.reflector.getAllAndOverride(ALLOW_PASSWORD_CHANGE_KEY, [
                ctx.getHandler(),
                ctx.getClass(),
            ]);
            if (!allowed) {
                throw new ForbiddenException({
                    code: 'password_change_required',
                    message: 'Password change required before accessing this resource.',
                });
            }
        }
        return true;
    }
};
JwtAuthGuard = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [Reflector])
], JwtAuthGuard);
export { JwtAuthGuard };
//# sourceMappingURL=jwt-auth.guard.js.map