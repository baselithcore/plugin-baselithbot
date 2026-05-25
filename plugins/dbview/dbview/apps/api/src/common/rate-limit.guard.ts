import {
  CanActivate,
  ExecutionContext,
  HttpException,
  HttpStatus,
  Injectable,
  Logger,
  SetMetadata,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { FastifyRequest } from 'fastify';

interface BucketState {
  tokens: number;
  updatedAt: number;
}

export interface RateLimitConfig {
  /** Max requests per window. */
  limit: number;
  /** Window in seconds. */
  windowSec: number;
}

const RL_META = 'dbview:rate-limit';

export const RateLimit = (cfg: RateLimitConfig) => SetMetadata(RL_META, cfg);

@Injectable()
export class RateLimitGuard implements CanActivate {
  private readonly logger = new Logger('RateLimitGuard');
  private readonly buckets = new Map<string, BucketState>();

  constructor(private readonly reflector: Reflector) {}

  canActivate(ctx: ExecutionContext): boolean {
    const cfg = this.reflector.get<RateLimitConfig | undefined>(RL_META, ctx.getHandler());
    if (!cfg) return true;

    const req = ctx.switchToHttp().getRequest<FastifyRequest>();
    const key = `${ctx.getHandler().name}:${req.ip ?? 'unknown'}`;
    const now = Date.now();
    const refillPerMs = cfg.limit / (cfg.windowSec * 1000);
    const bucket = this.buckets.get(key) ?? { tokens: cfg.limit, updatedAt: now };
    const elapsed = now - bucket.updatedAt;
    bucket.tokens = Math.min(cfg.limit, bucket.tokens + elapsed * refillPerMs);
    bucket.updatedAt = now;

    if (bucket.tokens < 1) {
      this.buckets.set(key, bucket);
      throw new HttpException(
        {
          code: 'rate_limited',
          message: `Too many requests. Limit ${cfg.limit}/${cfg.windowSec}s.`,
        },
        HttpStatus.TOO_MANY_REQUESTS,
      );
    }
    bucket.tokens -= 1;
    this.buckets.set(key, bucket);
    return true;
  }
}
