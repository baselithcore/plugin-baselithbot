import neo4j from 'neo4j-driver';
import type { Driver } from 'neo4j-driver';
import type { ExecuteQueryResponse } from '@dbview/shared';

/**
 * Per-query timeout (ms) sent to Neo4j as `timeout`. Default 30s.
 * Override with `DBVIEW_GRAPH_QUERY_TIMEOUT_MS` (clamped to 1000..600000).
 */
const QUERY_TIMEOUT_MS = clampTimeout(process.env.DBVIEW_GRAPH_QUERY_TIMEOUT_MS, 30_000);

function clampTimeout(raw: string | undefined, fallback: number): number {
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(1_000, Math.min(600_000, n));
}

export class Neo4jExecutor {
  private readonly driver: Driver;

  constructor(connectionString: string) {
    const url = new URL(connectionString);
    const username = decodeURIComponent(url.username || 'neo4j');
    const password = decodeURIComponent(url.password || 'neo4j');
    url.username = '';
    url.password = '';
    this.driver = neo4j.driver(url.toString(), neo4j.auth.basic(username, password), {
      connectionAcquisitionTimeout: 5_000,
      maxConnectionPoolSize: 4,
    });
  }

  async run(query: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
    const start = performance.now();
    try {
      const res = await session.run(query, {}, { timeout: QUERY_TIMEOUT_MS });
      const columns = res.records.length > 0 ? ((res.records[0]?.keys as string[]) ?? []) : [];
      const rows = res.records
        .slice(0, rowLimit)
        .map((rec) => columns.map((c) => normalizeValue(rec.get(c))));
      return {
        columns,
        rows,
        rowCount: res.records.length,
        durationMs: Math.round(performance.now() - start),
        truncated: res.records.length >= rowLimit,
      };
    } finally {
      await session.close();
    }
  }

  async close(): Promise<void> {
    await this.driver.close();
  }
}

function normalizeValue(v: unknown): unknown {
  if (v === null || v === undefined) return v;
  if (typeof v === 'object') {
    const obj = v as Record<string, unknown>;
    // neo4j Integer
    if ('low' in obj && 'high' in obj && Object.keys(obj).length === 2) {
      return neo4j.integer.toNumber(v as never);
    }
    // neo4j Node / Relationship → unwrap to properties + meta
    if ('properties' in obj && ('labels' in obj || 'type' in obj)) {
      const labels = (obj.labels as string[] | undefined) ?? [];
      const type = obj.type as string | undefined;
      return {
        _kind: 'labels' in obj ? 'node' : 'relationship',
        _labels: labels,
        _type: type,
        ...((obj.properties as Record<string, unknown>) ?? {}),
      };
    }
  }
  return v;
}
