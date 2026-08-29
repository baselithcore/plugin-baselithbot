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
export type MongoOp = 'collections' | 'count' | 'find' | 'distinct' | 'aggregate' | 'indexes' | 'stats';
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
export declare function parseMongoEnvelope(raw: string): MongoEnvelope;
export declare function validateMongoEnvelope(env: MongoEnvelope): void;
//# sourceMappingURL=safety.d.ts.map