import { FalkorDB, type FalkorDBOptions } from 'falkordb';
import type { ExecuteQueryResponse } from '@dbview/shared';

interface FalkorTarget {
  options: FalkorDBOptions;
  graphName: string;
}

/**
 * Connection string: `falkor://[user]:[pass]@host:port/graphName`
 * Falls back to `redis://` scheme. graphName from URL path.
 */
export function parseFalkorConnection(connectionString: string): FalkorTarget {
  const url = new URL(connectionString.replace(/^falkor:/, 'redis:'));
  const host = url.hostname || 'localhost';
  const port = url.port ? Number(url.port) : 6379;
  const username = decodeURIComponent(url.username || '') || undefined;
  const password = decodeURIComponent(url.password || '') || undefined;
  const graphName = url.pathname.replace(/^\//, '') || 'default';
  return {
    options: { username, password, socket: { host, port } },
    graphName,
  };
}

type GraphRecord = Record<string, unknown>;

export class FalkorExecutor {
  private clientPromise: Promise<FalkorDB> | null = null;
  private readonly target: FalkorTarget;

  constructor(connectionString: string) {
    this.target = parseFalkorConnection(connectionString);
  }

  private client(): Promise<FalkorDB> {
    if (!this.clientPromise) {
      this.clientPromise = FalkorDB.connect(this.target.options);
    }
    return this.clientPromise;
  }

  async run(query: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const db = await this.client();
    const graph = db.selectGraph(this.target.graphName);
    const start = performance.now();
    const res = await graph.roQuery<GraphRecord>(query);
    const allRows = res.data ?? [];
    const columns = allRows[0] ? Object.keys(allRows[0]) : [];
    const rows = allRows
      .slice(0, rowLimit)
      .map((row) => columns.map((c) => normalizeFalkorValue(row[c])));
    return {
      columns,
      rows,
      rowCount: allRows.length,
      durationMs: Math.round(performance.now() - start),
      truncated: allRows.length >= rowLimit,
    };
  }

  async close(): Promise<void> {
    if (!this.clientPromise) return;
    const db = await this.clientPromise;
    await db.close();
    this.clientPromise = null;
  }
}

function normalizeFalkorValue(v: unknown): unknown {
  if (v === null || v === undefined) return v;
  if (typeof v !== 'object') return v;
  const obj = v as Record<string, unknown>;
  if ('labels' in obj && 'properties' in obj) {
    return {
      _kind: 'node',
      _labels: (obj.labels as string[] | undefined) ?? [],
      ...((obj.properties as Record<string, unknown>) ?? {}),
    };
  }
  if ('relationshipType' in obj && 'properties' in obj) {
    return {
      _kind: 'relationship',
      _type: obj.relationshipType,
      ...((obj.properties as Record<string, unknown>) ?? {}),
    };
  }
  return v;
}
