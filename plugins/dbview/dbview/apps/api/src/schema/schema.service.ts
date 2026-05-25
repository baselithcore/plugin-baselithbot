import { Injectable, Logger } from '@nestjs/common';
import { ConnectionUnreachableError, IntrospectionError, type UnifiedSchema } from '@dbview/shared';
import { ConnectionsService } from '../connections/connections.service.js';
import { createQueryEngine } from '../engine/factory.js';
import { EnginePool } from '../engine/engine-pool.js';
import type { AuthPrincipal } from '../auth/auth.types.js';

interface CacheEntry {
  graph: UnifiedSchema;
  freshUntil: number;
  staleUntil: number;
}

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

@Injectable()
export class SchemaService {
  private readonly logger = new Logger('SchemaService');
  private readonly cache = new Map<string, CacheEntry>();

  constructor(
    private readonly connections: ConnectionsService,
    private readonly enginePool: EnginePool,
  ) {}

  async getGraph(
    connectionId: string,
    principal: AuthPrincipal,
    force = false,
  ): Promise<UnifiedSchema> {
    const now = Date.now();
    const cached = this.cache.get(connectionId);
    // Visibility check before cache hit: ensures a user without access cannot
    // peek at a cached schema for a connection they cannot see.
    this.connections.get(connectionId, principal);
    if (!force && cached && cached.freshUntil > now) return cached.graph;

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
    } catch (err) {
      // If we have a recently seen schema, serve it. Keeps the UI functional
      // when a database is briefly down or the network blips. Logs at WARN so
      // the degradation is visible in observability.
      if (cached && cached.staleUntil > now) {
        this.logger.warn(
          `serving stale schema connection=${connectionId} dialect=${dialect}: ${(err as Error).message}`,
        );
        return cached.graph;
      }
      throw classifyError(err, connectionString);
    } finally {
      if (!pooled) {
        await engine.close().catch(() => {
          /* ignore close errors during failure path */
        });
      }
    }
  }

  invalidate(connectionId: string): void {
    this.cache.delete(connectionId);
  }
}

function classifyError(err: unknown, connectionString: string): Error {
  const e = err as { code?: string; message?: string };
  const message = e.message ?? String(err);
  const code = typeof e.code === 'string' ? e.code : '';
  if (err instanceof IntrospectionError) {
    // Already classified upstream; check if its inner cause looks like a network issue.
    const networkCause =
      NETWORK_CODES.has(code) || /ECONNREFUSED|ENOTFOUND|ETIMEDOUT|EHOSTUNREACH/i.test(message);
    if (networkCause) return toUnreachable(message, code, connectionString);
    return err;
  }
  if (NETWORK_CODES.has(code) || /ECONNREFUSED|ENOTFOUND|ETIMEDOUT|EHOSTUNREACH/i.test(message)) {
    return toUnreachable(message, code, connectionString);
  }
  return new IntrospectionError(`Introspection failed: ${message}`);
}

function toUnreachable(
  message: string,
  code: string,
  connectionString: string,
): ConnectionUnreachableError {
  const cause = causeFromCode(code, message);
  const { host, port } = extractHostPort(connectionString);
  const target = host ? `${host}${port ? `:${port}` : ''}` : 'database';
  return new ConnectionUnreachableError(
    `Database at ${target} is unreachable (${cause}). Verify it is running and the host/port are correct.`,
    { cause, host, port },
  );
}

function causeFromCode(
  code: string,
  message: string,
): 'refused' | 'timeout' | 'dns' | 'tls' | 'auth' | 'unknown' {
  if (code === 'ECONNREFUSED') return 'refused';
  if (code === 'ETIMEDOUT' || /timeout/i.test(message)) return 'timeout';
  if (code === 'ENOTFOUND' || code === 'EAI_AGAIN' || /getaddrinfo/i.test(message)) return 'dns';
  if (/tls|ssl|certificate/i.test(message)) return 'tls';
  if (/password|authentication|auth/i.test(message)) return 'auth';
  return 'unknown';
}

function extractHostPort(cs: string): { host?: string; port?: number } {
  // Handle SQLite (file path) — no host.
  if (!cs.includes('://')) return {};
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
  } catch {
    return {};
  }
}
