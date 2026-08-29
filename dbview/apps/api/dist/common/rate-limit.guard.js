var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { HttpException, HttpStatus, Injectable, Logger, SetMetadata, } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
const RL_META = 'dbview:rate-limit';
export const RateLimit = (cfg) => SetMetadata(RL_META, cfg);
let RateLimitGuard = class RateLimitGuard {
    reflector;
    logger = new Logger('RateLimitGuard');
    buckets = new Map();
    constructor(reflector) {
        this.reflector = reflector;
    }
    canActivate(ctx) {
        const cfg = this.reflector.get(RL_META, ctx.getHandler());
        if (!cfg)
            return true;
        const req = ctx.switchToHttp().getRequest();
        const key = `${ctx.getHandler().name}:${req.ip ?? 'unknown'}`;
        const now = Date.now();
        const refillPerMs = cfg.limit / (cfg.windowSec * 1000);
        const bucket = this.buckets.get(key) ?? { tokens: cfg.limit, updatedAt: now };
        const elapsed = now - bucket.updatedAt;
        bucket.tokens = Math.min(cfg.limit, bucket.tokens + elapsed * refillPerMs);
        bucket.updatedAt = now;
        if (bucket.tokens < 1) {
            this.buckets.set(key, bucket);
            throw new HttpException({
                code: 'rate_limited',
                message: `Too many requests. Limit ${cfg.limit}/${cfg.windowSec}s.`,
            }, HttpStatus.TOO_MANY_REQUESTS);
        }
        bucket.tokens -= 1;
        this.buckets.set(key, bucket);
        return true;
    }
};
RateLimitGuard = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [Reflector])
], RateLimitGuard);
export { RateLimitGuard };
//# sourceMappingURL=rate-limit.guard.js.map