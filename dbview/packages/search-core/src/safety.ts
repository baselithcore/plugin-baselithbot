/**
 * Elasticsearch query envelope — JSON payload validated against a strict
 * read-only whitelist before being dispatched.
 *
 * Supported ops:
 *   - {"op":"indices"}               → list indices + basic stats
 *   - {"op":"count","index":"...","query":{...}}
 *   - {"op":"search","index":"...","body":{"query":{...},"size":N,...}}
 *   - {"op":"get","index":"...","id":"..."}
 *   - {"op":"mget","index":"...","ids":["..."]}
 *   - {"op":"mapping","index":"..."}
 *
 * All payload bodies are restricted to a read-only allowlist: `query`, `size`,
 * `from`, `sort`, `aggs`, `_source`, `track_total_hits`, `highlight`.
 * Anything else (update_by_query, delete_by_query, scripts, etc.) is rejected.
 */

export type ElasticOp = 'indices' | 'count' | 'search' | 'get' | 'mget' | 'mapping';

const ALLOWED_BODY_KEYS = new Set([
  'query',
  'size',
  'from',
  'sort',
  'aggs',
  'aggregations',
  '_source',
  'track_total_hits',
  'highlight',
  'fields',
  'min_score',
]);

export interface ElasticEnvelope {
  op: ElasticOp;
  index?: string;
  id?: string;
  ids?: string[];
  query?: unknown;
  body?: Record<string, unknown>;
}

export function parseElasticEnvelope(raw: string): ElasticEnvelope {
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
  if (!['indices', 'count', 'search', 'get', 'mget', 'mapping'].includes(op)) {
    throw new Error(`Unsupported op '${op}'. Allowed: indices, count, search, get, mget, mapping.`);
  }
  return obj as unknown as ElasticEnvelope;
}

export function validateElasticEnvelope(env: ElasticEnvelope): void {
  if (env.op === 'count' && !env.index) throw new Error("'count' requires 'index'.");
  if (env.op === 'search' && !env.index) throw new Error("'search' requires 'index'.");
  if (env.op === 'mapping' && !env.index) throw new Error("'mapping' requires 'index'.");
  if (env.op === 'get' && (!env.index || !env.id)) {
    throw new Error("'get' requires 'index' and 'id'.");
  }
  if (env.op === 'mget' && (!env.index || !Array.isArray(env.ids))) {
    throw new Error("'mget' requires 'index' and 'ids' array.");
  }
  if (env.body) {
    for (const key of Object.keys(env.body)) {
      if (!ALLOWED_BODY_KEYS.has(key)) {
        throw new Error(
          `Body key '${key}' is not allowed. Permitted: ${[...ALLOWED_BODY_KEYS].join(', ')}.`
        );
      }
    }
    if ('script' in env.body || 'scripts' in env.body) {
      throw new Error('Inline scripts are not allowed.');
    }
  }
}
