var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable, Logger } from '@nestjs/common';
import { ConnectionUnreachableError, IntrospectionError } from '@dbview/shared';
import { ConnectionsService } from '../connections/connections.service.js';
import { createQueryEngine } from '../engine/factory.js';
import { EnginePool } from '../engine/engine-pool.js';
const FRESH_TTL_MS = 5 * 60_000;
const STALE_TTL_MS = 60 * 60_000; // 1 hour
const NETWORK_CODES = new Set([
    'ECONNREFUSED',
    'ETIMEDOUT',
    'ENOTFOUND',
    'EHOSTUNREACH',
    'ENETUNREACH',
    'EAI_AGAIN',
    'ECONNRESET',
    'EPIPE',
]);
let SchemaService = class SchemaService {
    connections;
    enginePool;
    logger = new Logger('SchemaService');
    cache = new Map();
    constructor(connections, enginePool) {
        this.connections = connections;
        this.enginePool = enginePool;
    }
    async getGraph(connectionId, principal, force = false) {
        const now = Date.now();
        const cached = this.cache.get(connectionId);
        // Visibility check before cache hit: ensures a user without access cannot
        // peek at a cached schema for a connection they cannot see.
        this.connections.get(connectionId, principal);
        if (!force && cached && cached.freshUntil > now)
            return cached.graph;
        const { dialect, connectionString } = this.connections.resolvePlain(connectionId, principal);
        const pooled = this.enginePool.acquire(dialect, connectionString);
        const engine = pooled ?? createQueryEngine(dialect, connectionString);
        try {
            const graph = await engine.introspect();
            this.cache.set(connectionId, {
                graph,
                freshUntil: now + FRESH_TTL_MS,
                staleUntil: now + STALE_TTL_MS,
            });
            return graph;
        }
        catch (err) {
            // If we have a recently seen schema, serve it. Keeps the UI functional
            // when a database is briefly down or the network blips. Logs at WARN so
            // the degradation is visible in observability.
            if (cached && cached.staleUntil > now) {
                this.logger.warn(`serving stale schema connection=${connectionId} dialect=${dialect}: ${err.message}`);
                return cached.graph;
            }
            throw classifyError(err, connectionString);
        }
        finally {
            if (!pooled) {
                await engine.close().catch(() => {
                    /* ignore close errors during failure path */
                });
            }
        }
    }
    invalidate(connectionId) {
        this.cache.delete(connectionId);
    }
};
SchemaService = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [ConnectionsService,
        EnginePool])
], SchemaService);
export { SchemaService };
function classifyError(err, connectionString) {
    const e = err;
    const message = e.message ?? String(err);
    const code = typeof e.code === 'string' ? e.code : '';
    if (err instanceof IntrospectionError) {
        // Already classified upstream; check if its inner cause looks like a network issue.
        const networkCause = NETWORK_CODES.has(code) || /ECONNREFUSED|ENOTFOUND|ETIMEDOUT|EHOSTUNREACH/i.test(message);
        if (networkCause)
            return toUnreachable(message, code, connectionString);
        return err;
    }
    if (NETWORK_CODES.has(code) || /ECONNREFUSED|ENOTFOUND|ETIMEDOUT|EHOSTUNREACH/i.test(message)) {
        return toUnreachable(message, code, connectionString);
    }
    return new IntrospectionError(`Introspection failed: ${message}`);
}
function toUnreachable(message, code, connectionString) {
    const cause = causeFromCode(code, message);
    const { host, port } = extractHostPort(connectionString);
    const target = host ? `${host}${port ? `:${port}` : ''}` : 'database';
    return new ConnectionUnreachableError(`Database at ${target} is unreachable (${cause}). Verify it is running and the host/port are correct.`, { cause, host, port });
}
function causeFromCode(code, message) {
    if (code === 'ECONNREFUSED')
        return 'refused';
    if (code === 'ETIMEDOUT' || /timeout/i.test(message))
        return 'timeout';
    if (code === 'ENOTFOUND' || code === 'EAI_AGAIN' || /getaddrinfo/i.test(message))
        return 'dns';
    if (/tls|ssl|certificate/i.test(message))
        return 'tls';
    if (/password|authentication|auth/i.test(message))
        return 'auth';
    return 'unknown';
}
function extractHostPort(cs) {
    // Handle SQLite (file path) — no host.
    if (!cs.includes('://'))
        return {};
    try {
        // Normalize non-URL-compliant schemes.
        const normalized = cs
            .replace(/^falkor:/i, 'redis:')
            .replace(/^mssql:/i, 'http:')
            .replace(/^qdrants?:/i, 'http:');
        const u = new URL(normalized);
        const host = u.hostname || undefined;
        const port = u.port ? Number(u.port) : undefined;
        return { host, port };
    }
    catch {
        return {};
    }
}
//# sourceMappingURL=schema.service.js.map