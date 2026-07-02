import type { ExecuteQueryResponse } from '@dbview/shared';
import { UnsafeSqlError } from '@dbview/shared';
import { parseQdrantConnection, type QdrantTarget } from './parse.js';
import { QdrantClient } from './qdrant-client.js';

interface ScrollOp {
  op: 'scroll';
  collection: string;
  limit?: number;
  withPayload?: boolean;
  withVector?: boolean;
  filter?: Record<string, unknown>;
}

interface SearchOp {
  op: 'search';
  collection: string;
  vector: number[];
  limit?: number;
  using?: string;
  withPayload?: boolean;
  filter?: Record<string, unknown>;
}

interface CountOp {
  op: 'count';
  collection: string;
  filter?: Record<string, unknown>;
}

interface CollectionsOp {
  op: 'collections';
}

type QdrantOp = ScrollOp | SearchOp | CountOp | CollectionsOp;

/**
 * Qdrant query executor.
 *
 * Queries are JSON envelopes describing the read operation. Supported ops:
 *
 *   {"op": "collections"}
 *   {"op": "scroll", "collection": "wiki", "limit": 50}
 *   {"op": "search", "collection": "wiki", "vector": [...], "limit": 10}
 *
 * Mutations (upsert, delete, create_collection) are blocked.
 */
export class QdrantExecutor {
  private readonly client: QdrantClient;
  private readonly defaultCollection?: string;

  constructor(connectionString: string) {
    const target: QdrantTarget = parseQdrantConnection(connectionString);
    this.client = new QdrantClient(target);
    this.defaultCollection = target.collection;
  }

  async run(query: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const op = parseOp(query);
    const start = performance.now();
    if (op.op === 'collections') {
      const names = await this.client.listCollections();
      return rowsToResponse(
        ['collection'],
        names.map((n) => [n]),
        start
      );
    }
    const collection = op.collection || this.defaultCollection;
    if (!collection) {
      throw new UnsafeSqlError('Qdrant query missing collection name.');
    }
    if (op.op === 'scroll') {
      const limit = Math.min(rowLimit, op.limit ?? rowLimit);
      const points = await this.client.scroll(
        collection,
        limit,
        op.withPayload ?? true,
        op.withVector ?? false,
        op.filter
      );
      return pointsToResponse(points, false, start);
    }
    if (op.op === 'search') {
      if (!Array.isArray(op.vector)) {
        throw new UnsafeSqlError('Qdrant search requires a numeric `vector` array.');
      }
      const limit = Math.min(rowLimit, op.limit ?? rowLimit);
      const hits = await this.client.search(collection, op.vector, {
        limit,
        usingNamedVector: op.using,
        withPayload: op.withPayload ?? true,
        filter: op.filter,
      });
      return hitsToResponse(hits, start);
    }
    if (op.op === 'count') {
      const count = await this.client.countPoints(collection, op.filter);
      return rowsToResponse(['count'], [[count]], start);
    }
    throw new UnsafeSqlError(`Unknown Qdrant op: ${(op as { op: string }).op}`);
  }

  async close(): Promise<void> {
    // HTTP client is stateless.
  }
}

const WRITE_OPS = new Set(['upsert', 'delete', 'create', 'recreate', 'set', 'update']);

function parseOp(query: string): QdrantOp {
  const trimmed = query.trim();
  if (!trimmed.startsWith('{')) {
    throw new UnsafeSqlError(
      'Qdrant queries must be JSON envelopes (e.g. {"op":"scroll","collection":"...","limit":50}).'
    );
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch (err) {
    throw new UnsafeSqlError(`Invalid JSON: ${(err as Error).message}`);
  }
  if (!parsed || typeof parsed !== 'object') {
    throw new UnsafeSqlError('Qdrant query must be a JSON object.');
  }
  const op = (parsed as { op?: unknown }).op;
  if (typeof op !== 'string') {
    throw new UnsafeSqlError('Qdrant query missing "op" field.');
  }
  if (WRITE_OPS.has(op.toLowerCase())) {
    throw new UnsafeSqlError(`Mutating Qdrant op '${op}' is blocked. dbview is read-only.`);
  }
  if (op === 'collections') return { op: 'collections' };
  if (op === 'count') {
    const o = parsed as Record<string, unknown>;
    const collection = typeof o.collection === 'string' ? o.collection : '';
    return {
      op: 'count',
      collection,
      filter: isPlainObject(o.filter) ? (o.filter as Record<string, unknown>) : undefined,
    };
  }
  if (op === 'scroll' || op === 'search') {
    const o = parsed as Record<string, unknown>;
    const collection = typeof o.collection === 'string' ? o.collection : '';
    const limit = typeof o.limit === 'number' ? o.limit : undefined;
    const filter = isPlainObject(o.filter) ? (o.filter as Record<string, unknown>) : undefined;
    if (op === 'scroll') {
      return {
        op: 'scroll',
        collection,
        limit,
        withPayload: typeof o.withPayload === 'boolean' ? o.withPayload : undefined,
        withVector: typeof o.withVector === 'boolean' ? o.withVector : undefined,
        filter,
      };
    }
    const vector = Array.isArray(o.vector)
      ? (o.vector.filter((x) => typeof x === 'number') as number[])
      : [];
    return {
      op: 'search',
      collection,
      vector,
      limit,
      using: typeof o.using === 'string' ? o.using : undefined,
      withPayload: typeof o.withPayload === 'boolean' ? o.withPayload : undefined,
      filter,
    };
  }
  throw new UnsafeSqlError(`Unsupported Qdrant op '${op}'.`);
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object' && !Array.isArray(v);
}

interface QdrantPointLike {
  id: string | number;
  payload?: Record<string, unknown>;
  vector?: number[] | Record<string, number[]>;
}

function pointsToResponse(
  points: QdrantPointLike[],
  includeVector: boolean,
  start: number
): ExecuteQueryResponse {
  const payloadCols = collectPayloadColumns(points.map((p) => p.payload ?? {}));
  const columns = ['id', ...payloadCols, ...(includeVector ? ['vector'] : [])];
  const rows = points.map((p) => {
    const out: unknown[] = [p.id];
    for (const col of payloadCols) out.push(p.payload?.[col] ?? null);
    if (includeVector) out.push(p.vector ?? null);
    return out;
  });
  return rowsToResponse(columns, rows, start);
}

interface QdrantHit {
  id: string | number;
  score: number;
  payload?: Record<string, unknown>;
}

function hitsToResponse(hits: QdrantHit[], start: number): ExecuteQueryResponse {
  const payloadCols = collectPayloadColumns(hits.map((h) => h.payload ?? {}));
  const columns = ['id', 'score', ...payloadCols];
  const rows = hits.map((h) => {
    const out: unknown[] = [h.id, h.score];
    for (const col of payloadCols) out.push(h.payload?.[col] ?? null);
    return out;
  });
  return rowsToResponse(columns, rows, start);
}

function collectPayloadColumns(payloads: Array<Record<string, unknown>>): string[] {
  const seen = new Set<string>();
  for (const p of payloads) for (const k of Object.keys(p)) seen.add(k);
  return [...seen].sort();
}

function rowsToResponse(columns: string[], rows: unknown[][], start: number): ExecuteQueryResponse {
  return {
    columns,
    rows,
    rowCount: rows.length,
    durationMs: Math.round(performance.now() - start),
    truncated: false,
  };
}
