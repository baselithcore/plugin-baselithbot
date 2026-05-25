import { Injectable, Logger, type OnModuleDestroy } from '@nestjs/common';
import { isSqlDialect, type Dialect } from '@dbview/shared';
import { createQueryEngine, type QueryEngine } from './factory.js';

interface PoolEntry {
  engine: QueryEngine;
  lastUsed: number;
  dialect: Dialect;
}

const IDLE_TTL_MS = 5 * 60_000;
const SWEEP_INTERVAL_MS = 60_000;

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
@Injectable()
export class EnginePool implements OnModuleDestroy {
  private readonly logger = new Logger('EnginePool');
  private readonly cache = new Map<string, PoolEntry>();
  private readonly sweepTimer: NodeJS.Timeout;

  constructor() {
    this.sweepTimer = setInterval(() => this.sweep(), SWEEP_INTERVAL_MS);
    this.sweepTimer.unref?.();
  }

  /**
   * Returns a pooled engine or `null` for unsupported dialects. Caller must
   * NOT close engines returned by this method — the pool owns their lifecycle.
   */
  acquire(dialect: Dialect, connectionString: string): QueryEngine | null {
    if (!isSqlDialect(dialect)) return null;
    const key = this.key(dialect, connectionString);
    let entry = this.cache.get(key);
    if (!entry) {
      const engine = createQueryEngine(dialect, connectionString);
      entry = { engine, lastUsed: Date.now(), dialect };
      this.cache.set(key, entry);
    } else {
      entry.lastUsed = Date.now();
    }
    return entry.engine;
  }

  /**
   * Evicts and closes the engine matching this connection string. Use after
   * a connection is deleted or its credentials change so stale credentials
   * do not linger in memory.
   */
  invalidate(dialect: Dialect, connectionString: string): void {
    if (!isSqlDialect(dialect)) return;
    const key = this.key(dialect, connectionString);
    const entry = this.cache.get(key);
    if (!entry) return;
    this.cache.delete(key);
    void entry.engine.close().catch((err) => {
      this.logger.warn(`engine_close_failed dialect=${entry.dialect}: ${(err as Error).message}`);
    });
  }

  async onModuleDestroy(): Promise<void> {
    clearInterval(this.sweepTimer);
    const entries = [...this.cache.values()];
    this.cache.clear();
    await Promise.all(
      entries.map((e) =>
        e.engine.close().catch((err) => {
          this.logger.warn(`engine_close_failed dialect=${e.dialect}: ${(err as Error).message}`);
        })
      )
    );
  }

  private sweep(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache) {
      if (now - entry.lastUsed > IDLE_TTL_MS) {
        this.cache.delete(key);
        void entry.engine.close().catch((err) => {
          this.logger.warn(
            `engine_close_failed dialect=${entry.dialect}: ${(err as Error).message}`
          );
        });
      }
    }
  }

  private key(dialect: Dialect, connectionString: string): string {
    return `${dialect}|${connectionString}`;
  }
}
