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
export interface ElasticEnvelope {
    op: ElasticOp;
    index?: string;
    id?: string;
    ids?: string[];
    query?: unknown;
    body?: Record<string, unknown>;
}
export declare function parseElasticEnvelope(raw: string): ElasticEnvelope;
export declare function validateElasticEnvelope(env: ElasticEnvelope): void;
//# sourceMappingURL=safety.d.ts.map