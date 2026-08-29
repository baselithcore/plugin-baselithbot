import { UnsafeSqlError } from '@dbview/shared';
import { parseQdrantConnection } from './parse.js';
import { QdrantClient } from './qdrant-client.js';
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
    client;
    defaultCollection;
    constructor(connectionString) {
        const target = parseQdrantConnection(connectionString);
        this.client = new QdrantClient(target);
        this.defaultCollection = target.collection;
    }
    async run(query, rowLimit) {
        const op = parseOp(query);
        const start = performance.now();
        if (op.op === 'collections') {
            const names = await this.client.listCollections();
            return rowsToResponse(['collection'], names.map((n) => [n]), start);
        }
        const collection = op.collection || this.defaultCollection;
        if (!collection) {
            throw new UnsafeSqlError('Qdrant query missing collection name.');
        }
        if (op.op === 'scroll') {
            const limit = Math.min(rowLimit, op.limit ?? rowLimit);
            const points = await this.client.scroll(collection, limit, op.withPayload ?? true, op.withVector ?? false, op.filter);
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
        throw new UnsafeSqlError(`Unknown Qdrant op: ${op.op}`);
    }
    async close() {
        // HTTP client is stateless.
    }
}
const WRITE_OPS = new Set(['upsert', 'delete', 'create', 'recreate', 'set', 'update']);
function parseOp(query) {
    const trimmed = query.trim();
    if (!trimmed.startsWith('{')) {
        throw new UnsafeSqlError('Qdrant queries must be JSON envelopes (e.g. {"op":"scroll","collection":"...","limit":50}).');
    }
    let parsed;
    try {
        parsed = JSON.parse(trimmed);
    }
    catch (err) {
        throw new UnsafeSqlError(`Invalid JSON: ${err.message}`);
    }
    if (!parsed || typeof parsed !== 'object') {
        throw new UnsafeSqlError('Qdrant query must be a JSON object.');
    }
    const op = parsed.op;
    if (typeof op !== 'string') {
        throw new UnsafeSqlError('Qdrant query missing "op" field.');
    }
    if (WRITE_OPS.has(op.toLowerCase())) {
        throw new UnsafeSqlError(`Mutating Qdrant op '${op}' is blocked. dbview is read-only.`);
    }
    if (op === 'collections')
        return { op: 'collections' };
    if (op === 'count') {
        const o = parsed;
        const collection = typeof o.collection === 'string' ? o.collection : '';
        return {
            op: 'count',
            collection,
            filter: isPlainObject(o.filter) ? o.filter : undefined,
        };
    }
    if (op === 'scroll' || op === 'search') {
        const o = parsed;
        const collection = typeof o.collection === 'string' ? o.collection : '';
        const limit = typeof o.limit === 'number' ? o.limit : undefined;
        const filter = isPlainObject(o.filter) ? o.filter : undefined;
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
            ? o.vector.filter((x) => typeof x === 'number')
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
function isPlainObject(v) {
    return !!v && typeof v === 'object' && !Array.isArray(v);
}
function pointsToResponse(points, includeVector, start) {
    const payloadCols = collectPayloadColumns(points.map((p) => p.payload ?? {}));
    const columns = ['id', ...payloadCols, ...(includeVector ? ['vector'] : [])];
    const rows = points.map((p) => {
        const out = [p.id];
        for (const col of payloadCols)
            out.push(p.payload?.[col] ?? null);
        if (includeVector)
            out.push(p.vector ?? null);
        return out;
    });
    return rowsToResponse(columns, rows, start);
}
function hitsToResponse(hits, start) {
    const payloadCols = collectPayloadColumns(hits.map((h) => h.payload ?? {}));
    const columns = ['id', 'score', ...payloadCols];
    const rows = hits.map((h) => {
        const out = [h.id, h.score];
        for (const col of payloadCols)
            out.push(h.payload?.[col] ?? null);
        return out;
    });
    return rowsToResponse(columns, rows, start);
}
function collectPayloadColumns(payloads) {
    const seen = new Set();
    for (const p of payloads)
        for (const k of Object.keys(p))
            seen.add(k);
    return [...seen].sort();
}
function rowsToResponse(columns, rows, start) {
    return {
        columns,
        rows,
        rowCount: rows.length,
        durationMs: Math.round(performance.now() - start),
        truncated: false,
    };
}
//# sourceMappingURL=qdrant-executor.js.map