var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable } from '@nestjs/common';
import { tap, catchError, throwError } from 'rxjs';
import { httpRequestErrors, httpRequestLatency, statusBucket } from './metrics.registry.js';
let MetricsInterceptor = class MetricsInterceptor {
    intercept(ctx, next) {
        const httpCtx = ctx.switchToHttp();
        const req = httpCtx.getRequest();
        const reply = httpCtx.getResponse();
        const start = process.hrtime.bigint();
        const method = req.method ?? 'GET';
        const route = normalizeRoute(req);
        const record = (status, reason) => {
            const seconds = Number(process.hrtime.bigint() - start) / 1e9;
            const bucket = statusBucket(status);
            httpRequestLatency.labels(method, route, bucket).observe(seconds);
            if (status >= 400) {
                httpRequestErrors.labels(method, route, bucket, reason ?? 'unknown').inc();
            }
        };
        return next.handle().pipe(tap(() => record(reply.statusCode, null)), catchError((err) => {
            const status = extractStatus(err);
            const reason = extractReason(err);
            record(status, reason);
            return throwError(() => err);
        }));
    }
};
MetricsInterceptor = __decorate([
    Injectable()
], MetricsInterceptor);
export { MetricsInterceptor };
// UUIDs, numeric IDs and other dynamic segments in concrete request URLs
// would explode the route label cardinality if used directly. Fastify
// usually exposes a template like `/api/connections/:id` via
// `routeOptions.url` or `routerPath`; only fall back to scrubbing the raw
// URL when neither template is available (e.g. 404 paths that did not match
// any handler).
const UUID_RE = /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g;
const NUMERIC_SEGMENT_RE = /\/\d+(?=\/|$)/g;
function normalizeRoute(req) {
    const fr = req;
    const template = fr.routeOptions?.url ?? fr.routerPath;
    if (template)
        return template;
    const raw = (req.url ?? 'unknown').split('?')[0] ?? 'unknown';
    return raw.replace(UUID_RE, ':id').replace(NUMERIC_SEGMENT_RE, '/:id');
}
function extractStatus(err) {
    if (typeof err !== 'object' || err === null)
        return 500;
    const e = err;
    if (typeof e.getStatus === 'function')
        return e.getStatus();
    return typeof e.status === 'number' ? e.status : 500;
}
function extractReason(err) {
    if (typeof err !== 'object' || err === null)
        return 'unknown';
    const e = err;
    return e.code ?? e.name ?? 'unknown';
}
//# sourceMappingURL=metrics.interceptor.js.map