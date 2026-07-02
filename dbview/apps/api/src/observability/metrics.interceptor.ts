import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { Observable, tap, catchError, throwError } from 'rxjs';
import type { FastifyReply, FastifyRequest } from 'fastify';
import { httpRequestErrors, httpRequestLatency, statusBucket } from './metrics.registry.js';

@Injectable()
export class MetricsInterceptor implements NestInterceptor {
  intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown> {
    const httpCtx = ctx.switchToHttp();
    const req = httpCtx.getRequest<FastifyRequest>();
    const reply = httpCtx.getResponse<FastifyReply>();
    const start = process.hrtime.bigint();
    const method = req.method ?? 'GET';
    const route = normalizeRoute(req);

    const record = (status: number, reason: string | null): void => {
      const seconds = Number(process.hrtime.bigint() - start) / 1e9;
      const bucket = statusBucket(status);
      httpRequestLatency.labels(method, route, bucket).observe(seconds);
      if (status >= 400) {
        httpRequestErrors.labels(method, route, bucket, reason ?? 'unknown').inc();
      }
    };

    return next.handle().pipe(
      tap(() => record(reply.statusCode, null)),
      catchError((err: unknown) => {
        const status = extractStatus(err);
        const reason = extractReason(err);
        record(status, reason);
        return throwError(() => err);
      }),
    );
  }
}

// UUIDs, numeric IDs and other dynamic segments in concrete request URLs
// would explode the route label cardinality if used directly. Fastify
// usually exposes a template like `/api/connections/:id` via
// `routeOptions.url` or `routerPath`; only fall back to scrubbing the raw
// URL when neither template is available (e.g. 404 paths that did not match
// any handler).
const UUID_RE = /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g;
const NUMERIC_SEGMENT_RE = /\/\d+(?=\/|$)/g;

function normalizeRoute(req: FastifyRequest): string {
  const fr = req as FastifyRequest & {
    routeOptions?: { url?: string };
    routerPath?: string;
  };
  const template = fr.routeOptions?.url ?? fr.routerPath;
  if (template) return template;
  const raw = (req.url ?? 'unknown').split('?')[0] ?? 'unknown';
  return raw.replace(UUID_RE, ':id').replace(NUMERIC_SEGMENT_RE, '/:id');
}

function extractStatus(err: unknown): number {
  if (typeof err !== 'object' || err === null) return 500;
  const e = err as { status?: number; getStatus?: () => number };
  if (typeof e.getStatus === 'function') return e.getStatus();
  return typeof e.status === 'number' ? e.status : 500;
}

function extractReason(err: unknown): string {
  if (typeof err !== 'object' || err === null) return 'unknown';
  const e = err as { code?: string; name?: string };
  return e.code ?? e.name ?? 'unknown';
}
