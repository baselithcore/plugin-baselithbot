/**
 * MongoDB read-only envelope validation.
 *
 * Supported ops:
 *   - {"op":"collections"}                                          → list collections
 *   - {"op":"count","collection":"<name>","filter":{...}}
 *   - {"op":"find","collection":"<name>","filter":{...},"projection":{...},"sort":{...},"limit":N,"skip":N}
 *   - {"op":"distinct","collection":"<name>","field":"<path>","filter":{...}}
 *   - {"op":"aggregate","collection":"<name>","pipeline":[...]}     → pipeline stages restricted
 *   - {"op":"indexes","collection":"<name>"}                        → list indexes
 *   - {"op":"stats","collection":"<name>"}                          → collection stats
 *
 * The aggregate op rejects write-stages: $out, $merge, $function, $accumulator, $where.
 */

export type MongoOp =
  'collections' | 'count' | 'find' | 'distinct' | 'aggregate' | 'indexes' | 'stats';

const ALLOWED_FIND_KEYS = new Set([
  'filter',
  'projection',
  'sort',
  'limit',
  'skip',
  'collation',
  'hint',
]);

const FORBIDDEN_AGG_STAGES = new Set(['$out', '$merge', '$function', '$accumulator', '$where']);

export interface MongoEnvelope {
  op: MongoOp;
  collection?: string;
  field?: string;
  filter?: Record<string, unknown>;
  projection?: Record<string, unknown>;
  sort?: Record<string, unknown>;
  limit?: number;
  skip?: number;
  pipeline?: Array<Record<string, unknown>>;
}

export function parseMongoEnvelope(raw: string): MongoEnvelope {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new Error(`Invalid JSON: ${(err as Error).message}`);
  }
  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Envelope must be a JSON object.');
  }
  const obj = parsed as Record<string, unknown>;
  const op = obj['op'];
  if (typeof op !== 'string') throw new Error("Missing 'op' field.");
  if (!['collections', 'count', 'find', 'distinct', 'aggregate', 'indexes', 'stats'].includes(op)) {
    throw new Error(
      `Unsupported op '${op}'. Allowed: collections, count, find, distinct, aggregate, indexes, stats.`
    );
  }
  return obj as unknown as MongoEnvelope;
}

export function validateMongoEnvelope(env: MongoEnvelope): void {
  const needsCollection = (
    ['count', 'find', 'distinct', 'aggregate', 'indexes', 'stats'] as MongoOp[]
  ).includes(env.op);
  if (needsCollection && !env.collection) {
    throw new Error(`Op '${env.op}' requires 'collection'.`);
  }
  if (env.op === 'distinct' && !env.field) {
    throw new Error("'distinct' requires 'field'.");
  }
  if (env.op === 'find') {
    const known = ['op', 'collection', ...ALLOWED_FIND_KEYS];
    for (const k of Object.keys(env)) {
      if (!known.includes(k)) {
        throw new Error(`find key '${k}' is not allowed.`);
      }
    }
  }
  if (env.op === 'aggregate') {
    if (!Array.isArray(env.pipeline)) throw new Error("'aggregate' requires 'pipeline' array.");
    for (const stage of env.pipeline) {
      if (!stage || typeof stage !== 'object')
        throw new Error('Each pipeline stage must be an object.');
      for (const key of Object.keys(stage)) {
        if (FORBIDDEN_AGG_STAGES.has(key)) {
          throw new Error(`Pipeline stage '${key}' is not allowed.`);
        }
      }
    }
  }
}
