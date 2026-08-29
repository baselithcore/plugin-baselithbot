import { type OnModuleDestroy } from '@nestjs/common';
import { type Dialect } from '@dbview/shared';
import { type QueryEngine } from './factory.js';
/**
 * Reuses `QueryEngine` instances across requests for SQL dialects only.
 *
 * Postgres/CockroachDB executors wrap an internal `pg.Pool` (4 connections);
 * better-sqlite3 holds a single read-only file handle. Both are safe to share
 * across concurrent requests and cost a non-trivial amount to construct
 * (TCP+TLS handshake, file open + read-only PRAGMA). Pooling avoids paying
 * that cost on every preview / sample / execute call.
 *
 * Non-SQL dialects (graph, vector, document, search, SaaS) are not pooled —
 * their vendor SDKs each have different lifecycle semantics, and keeping the
 * scope tight avoids surprises. Callers fall back to fresh-create/close.
 */
export declare class EnginePool implements OnModuleDestroy {
    private readonly logger;
    private readonly cache;
    private readonly sweepTimer;
    constructor();
    /**
     * Returns a pooled engine or `null` for unsupported dialects. Caller must
     * NOT close engines returned by this method — the pool owns their lifecycle.
     */
    acquire(dialect: Dialect, connectionString: string): QueryEngine | null;
    /**
     * Evicts and closes the engine matching this connection string. Use after
     * a connection is deleted or its credentials change so stale credentials
     * do not linger in memory.
     */
    invalidate(dialect: Dialect, connectionString: string): void;
    onModuleDestroy(): Promise<void>;
    private sweep;
    private key;
}
//# sourceMappingURL=engine-pool.d.ts.map