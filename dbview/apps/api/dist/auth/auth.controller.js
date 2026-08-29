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
import { Body, Controller, Get, Post, Req, Res, UseGuards } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ChangePasswordRequestSchema, LoginRequestSchema, RegisterRequestSchema, } from '@dbview/shared';
import { UnauthorizedError } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { Public } from '../common/public.decorator.js';
import { AllowPasswordChange } from '../common/password-change.decorator.js';
import { RateLimit, RateLimitGuard } from '../common/rate-limit.guard.js';
import { AuthService, refreshCookieTtl } from './auth.service.js';
import { CurrentUser } from './decorators.js';
import { isGatewayMode } from './gateway.js';
import { toPublicUser } from './auth.types.js';
const REFRESH_COOKIE = 'dbview_refresh';
function cookieOpts(maxAge) {
    return {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        path: '/api/auth',
        ...(maxAge !== undefined ? { maxAge } : {}),
    };
}
let AuthController = class AuthController {
    auth;
    reflector;
    constructor(auth, reflector) {
        this.auth = auth;
        this.reflector = reflector;
        void this.reflector;
    }
    async login(body, req, reply) {
        const result = await this.auth.login(body.email, body.password, {
            ip: req.ip ?? null,
            userAgent: req.headers['user-agent'] ?? null,
        });
        reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
        return {
            accessToken: result.accessToken,
            expiresIn: result.expiresIn,
            user: result.user,
        };
    }
    config() {
        return {
            registrationEnabled: this.auth.isRegistrationEnabled(),
            gateway: isGatewayMode(),
        };
    }
    async register(body, req, reply) {
        const result = await this.auth.register(body, {
            ip: req.ip ?? null,
            userAgent: req.headers['user-agent'] ?? null,
        });
        reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
        return {
            accessToken: result.accessToken,
            expiresIn: result.expiresIn,
            user: result.user,
        };
    }
    refresh(req, reply) {
        const raw = readRefreshCookie(req);
        if (!raw)
            throw new UnauthorizedError('No refresh token present.');
        const result = this.auth.rotate(raw, {
            ip: req.ip ?? null,
            userAgent: req.headers['user-agent'] ?? null,
        });
        reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
        return {
            accessToken: result.accessToken,
            expiresIn: result.expiresIn,
            user: result.user,
        };
    }
    logout(req, reply) {
        const raw = readRefreshCookie(req);
        this.auth.logout(raw);
        reply.clearCookie(REFRESH_COOKIE, cookieOpts());
        return { ok: true };
    }
    me(principal) {
        if (!principal)
            throw new UnauthorizedError();
        if (principal.source === 'api-key') {
            return {
                user: {
                    id: principal.id,
                    email: principal.email,
                    displayName: 'Service Account',
                    role: principal.role,
                    isActive: true,
                    createdAt: new Date(0).toISOString(),
                    lastLoginAt: null,
                    mustChangePassword: false,
                },
            };
        }
        const user = this.auth.getUser(principal.id);
        if (!user)
            throw new UnauthorizedError('User not found.');
        return { user: toPublicUser(user) };
    }
    async changePassword(body, principal, req, reply) {
        if (!principal || principal.source !== 'jwt') {
            throw new UnauthorizedError('JWT session required.');
        }
        const updated = await this.auth.changePassword(principal.id, body.currentPassword, body.newPassword);
        // Issue a fresh session so the access token reflects mustChangePassword=false
        // immediately. Refresh cookie is rotated to invalidate the prior token chain.
        const result = await this.auth.login(updated.email, body.newPassword, {
            ip: req.ip ?? null,
            userAgent: req.headers['user-agent'] ?? null,
        });
        reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
        return {
            accessToken: result.accessToken,
            expiresIn: result.expiresIn,
            user: result.user,
        };
    }
};
__decorate([
    Public(),
    UseGuards(RateLimitGuard),
    RateLimit({ limit: 5, windowSec: 60 }),
    Post('login'),
    __param(0, Body(new ZodPipe(LoginRequestSchema))),
    __param(1, Req()),
    __param(2, Res({ passthrough: true })),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object, Object]),
    __metadata("design:returntype", Promise)
], AuthController.prototype, "login", null);
__decorate([
    Public(),
    Get('config'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Object)
], AuthController.prototype, "config", null);
__decorate([
    Public(),
    UseGuards(RateLimitGuard),
    RateLimit({ limit: 5, windowSec: 60 }),
    Post('register'),
    __param(0, Body(new ZodPipe(RegisterRequestSchema))),
    __param(1, Req()),
    __param(2, Res({ passthrough: true })),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object, Object]),
    __metadata("design:returntype", Promise)
], AuthController.prototype, "register", null);
__decorate([
    Public(),
    UseGuards(RateLimitGuard),
    RateLimit({ limit: 30, windowSec: 60 }),
    Post('refresh'),
    __param(0, Req()),
    __param(1, Res({ passthrough: true })),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Object)
], AuthController.prototype, "refresh", null);
__decorate([
    Public(),
    Post('logout'),
    __param(0, Req()),
    __param(1, Res({ passthrough: true })),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Object)
], AuthController.prototype, "logout", null);
__decorate([
    AllowPasswordChange(),
    Get('me'),
    __param(0, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Object)
], AuthController.prototype, "me", null);
__decorate([
    AllowPasswordChange(),
    Post('change-password'),
    __param(0, Body(new ZodPipe(ChangePasswordRequestSchema))),
    __param(1, CurrentUser()),
    __param(2, Req()),
    __param(3, Res({ passthrough: true })),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object, Object, Object]),
    __metadata("design:returntype", Promise)
], AuthController.prototype, "changePassword", null);
AuthController = __decorate([
    Controller('auth'),
    __metadata("design:paramtypes", [AuthService,
        Reflector])
], AuthController);
export { AuthController };
function readRefreshCookie(req) {
    const cookies = req
        .cookies;
    return cookies?.[REFRESH_COOKIE] ?? null;
}
//# sourceMappingURL=auth.controller.js.map