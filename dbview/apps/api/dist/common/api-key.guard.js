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
import { timingSafeEqual } from 'node:crypto';
import { IS_PUBLIC_KEY } from './public.decorator.js';
/**
 * Optional service-to-service API key gate. Active when DBVIEW_API_KEY is set.
 * On match, attaches a synthetic admin principal so JWT guard can short-circuit.
 * Never throws — absence is handled by the JWT guard.
 */
let ApiKeyGuard = class ApiKeyGuard {
    reflector;
    expected = process.env.DBVIEW_API_KEY ?? '';
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
        if (!this.expected)
            return true; // no key configured, defer to JWT guard
        const req = ctx.switchToHttp().getRequest();
        const provided = req.headers['x-api-key'] ?? '';
        if (provided && safeEqual(provided, this.expected)) {
            req.user = {
                id: 'service',
                email: 'service@dbview.local',
                role: 'admin',
                source: 'api-key',
            };
        }
        return true;
    }
};
ApiKeyGuard = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [Reflector])
], ApiKeyGuard);
export { ApiKeyGuard };
function safeEqual(a, b) {
    const ab = Buffer.from(a);
    const bb = Buffer.from(b);
    if (ab.length !== bb.length)
        return false;
    return timingSafeEqual(ab, bb);
}
//# sourceMappingURL=api-key.guard.js.map