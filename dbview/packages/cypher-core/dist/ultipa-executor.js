import { QueryTimeoutError } from '@dbview/shared';
import { createUltipaClient, releaseUltipaClient } from './ultipa-client.js';
/**
 * Per-query timeout (ms) forwarded to the Ultipa gRPC client. Default 60s.
 * Override with `DBVIEW_GRAPH_QUERY_TIMEOUT_MS` (clamped to 1000..600000).
 * Earlier defaults (5s, then 30s) were too tight for medium traversals.
 */
const QUERY_TIMEOUT_MS = clampTimeout(process.env.DBVIEW_GRAPH_QUERY_TIMEOUT_MS, 60_000);
/**
 * Detect gRPC DEADLINE_EXCEEDED surfaced by the Ultipa driver.
 * The driver re-throws the underlying `@grpc/grpc-js` error verbatim
 * (status code 4, name `QueryFailedError`). We match on either signal
 * so a driver upgrade renaming the wrapper does not silently regress.
 */
function isDeadlineExceeded(err) {
    if (!err || typeof err !== 'object')
        return false;
    const e = err;
    if (e.code === 4)
        return true;
    const msg = typeof e.message === 'string' ? e.message : '';
    return /DEADLINE_EXCEEDED|Deadline exceeded/i.test(msg);
}
function clampTimeout(raw, fallback) {
    if (!raw)
        return fallback;
    const n = Number.parseInt(raw, 10);
    if (!Number.isFinite(n))
        return fallback;
    return Math.max(1_000, Math.min(600_000, n));
}
/**
 * Ultipa GQL executor.
 *
 * Reuses a long-lived authenticated `GqldbClient`. The Cypher safety
 * validator runs upstream — this executor only forwards the validated GQL
 * statement with `readOnly: true` so any write attempt the validator
 * misses is still rejected server-side.
 */
export class UltipaExecutor {
    clientP = null;
    connectionString;
    constructor(connectionString) {
        this.connectionString = connectionString;
    }
    async run(query, rowLimit) {
        const { client, defaultGraph } = await this.connect();
        const start = performance.now();
        let res;
        try {
            res = await client.gql(query, {
                graphName: defaultGraph,
                readOnly: true,
                timeout: QUERY_TIMEOUT_MS,
            });
        }
        catch (err) {
            if (isDeadlineExceeded(err)) {
                throw new QueryTimeoutError(`Ultipa query exceeded ${QUERY_TIMEOUT_MS}ms deadline. Narrow the filter or raise DBVIEW_GRAPH_QUERY_TIMEOUT_MS.`, { dialect: 'gqldb', timeoutMs: QUERY_TIMEOUT_MS });
            }
            throw err;
        }
        const columns = res.columns;
        const totalRows = res.rows.length;
        const rows = res.rows
            .slice(0, rowLimit)
            .map((row) => columns.map((_c, i) => normalizeValue(row.get(i))));
        return {
            columns,
            rows,
            rowCount: totalRows,
            durationMs: Math.round(performance.now() - start),
            truncated: totalRows > rowLimit || res.hasMore,
        };
    }
    async close() {
        if (!this.clientP)
            return;
        try {
            await this.clientP;
        }
        catch {
            /* connect failed */
        }
        finally {
            releaseUltipaClient(this.connectionString);
            this.clientP = null;
        }
    }
    async connect() {
        if (!this.clientP) {
            this.clientP = (async () => {
                const { client, target } = await createUltipaClient(this.connectionString);
                return { client, defaultGraph: target.defaultGraph };
            })();
        }
        return this.clientP;
    }
}
/**
 * Map an Ultipa v6 `Node` / `Edge` (shape declared in
 * `@ultipa-graph/ultipa-driver` `response.d.ts`) into the common
 * graph-row format the dbview UI expects.
 *
 * v6 Node: `{id, labels: string[], properties: Record}`
 * v6 Edge: `{id, label: string, fromNodeId, toNodeId, properties: Record}`
 */
function normalizeValue(v) {
    if (v === null || v === undefined)
        return v;
    if (typeof v === 'bigint')
        return Number(v);
    if (Array.isArray(v))
        return v.map(normalizeValue);
    if (typeof v !== 'object')
        return v;
    const obj = v;
    const props = readProperties(obj);
    const hasFromNode = typeof obj.fromNodeId === 'string' ||
        typeof obj.toNodeId === 'string' ||
        'fromUuid' in obj ||
        'fromId' in obj;
    const isEdge = hasFromNode || (typeof obj.label === 'string' && !Array.isArray(obj.labels));
    const isNode = !isEdge && (Array.isArray(obj.labels) || typeof obj.schema === 'string');
    if (!isEdge && !isNode)
        return v;
    if (isEdge) {
        const type = obj.label ??
            obj.schema ??
            obj.schemaName;
        const sourceId = obj.fromNodeId ??
            obj.fromUuid ??
            obj.fromId ??
            obj.from;
        const targetId = obj.toNodeId ??
            obj.toUuid ??
            obj.toId ??
            obj.to;
        const id = pickId(obj, props);
        return {
            _kind: 'relationship',
            ...(type ? { _type: type, _schema: type } : {}),
            ...(id !== undefined ? { _id: id, id } : {}),
            ...(sourceId !== undefined ? { sourceId, _fromId: sourceId } : {}),
            ...(targetId !== undefined ? { targetId, _toId: targetId } : {}),
            ...props,
        };
    }
    const schema = obj.schema ?? obj.schemaName;
    const labels = Array.isArray(obj.labels) && obj.labels.length > 0
        ? obj.labels
        : schema
            ? [schema]
            : [];
    const id = pickId(obj, props);
    return {
        _kind: 'node',
        ...(schema ? { _schema: schema } : {}),
        _labels: labels,
        ...(id !== undefined ? { _id: id, id } : {}),
        ...props,
    };
}
function readProperties(obj) {
    if (obj.properties && typeof obj.properties === 'object' && !Array.isArray(obj.properties)) {
        return obj.properties;
    }
    if (typeof obj.properties === 'string') {
        try {
            const parsed = JSON.parse(obj.properties);
            if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                return parsed;
            }
        }
        catch {
            // Ignore parse errors.
        }
    }
    if (obj.values && typeof obj.values === 'object' && !Array.isArray(obj.values)) {
        return obj.values;
    }
    return {};
}
function pickId(obj, props) {
    const candidates = [obj.id, obj.uuid, props._uuid, props._id, props.id];
    for (const c of candidates) {
        if (c !== undefined && c !== null && c !== '')
            return c;
    }
    return undefined;
}
//# sourceMappingURL=ultipa-executor.js.map