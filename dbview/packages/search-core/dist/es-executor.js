import { createEsClient } from './es-client.js';
import { parseElasticEnvelope, validateElasticEnvelope } from './safety.js';
/**
 * Executes a read-only Elasticsearch envelope.
 * The envelope is a JSON object describing the op (see safety.ts).
 * Output is shaped into the unified columns/rows response.
 */
export class ElasticsearchExecutor {
    connectionString;
    client;
    constructor(connectionString) {
        this.connectionString = connectionString;
    }
    getClient() {
        if (!this.client) {
            this.client = createEsClient(this.connectionString).client;
        }
        return this.client;
    }
    async run(query, rowLimit) {
        const start = performance.now();
        const env = parseElasticEnvelope(query);
        validateElasticEnvelope(env);
        const client = this.getClient();
        if (env.op === 'indices') {
            const stats = (await client.cat.indices({ format: 'json' }));
            const columns = ['index', 'docs.count', 'store.size', 'health', 'status'];
            const rows = stats.map((r) => [
                r.index ?? '',
                r['docs.count'] ?? '0',
                r['store.size'] ?? '',
                r.health ?? '',
                r.status ?? '',
            ]);
            return finalize(columns, rows, rowLimit, start);
        }
        if (env.op === 'count') {
            const res = await client.count({
                index: env.index,
                ...(env.query ? { query: env.query } : {}),
            });
            return finalize(['count'], [[res.count]], rowLimit, start);
        }
        if (env.op === 'mapping') {
            const res = await client.indices.getMapping({ index: env.index });
            const rows = [];
            for (const [idx, mapping] of Object.entries(res)) {
                const props = mapping.mappings
                    ?.properties;
                if (props) {
                    for (const [field, def] of Object.entries(props)) {
                        const t = def.type ?? 'object';
                        rows.push([idx, field, t]);
                    }
                }
            }
            return finalize(['index', 'field', 'type'], rows, rowLimit, start);
        }
        if (env.op === 'get') {
            const res = await client.get({ index: env.index, id: env.id });
            const src = (res._source ?? null);
            return finalize(['_id', '_source'], [[res._id, src ? JSON.stringify(src) : null]], rowLimit, start);
        }
        if (env.op === 'mget') {
            const res = await client.mget({ index: env.index, ids: env.ids });
            const rows = (res.docs ?? []).map((d) => {
                const found = d.found;
                const id = d._id ?? '';
                const src = d._source;
                return [id, found ? 'found' : 'missing', src ? JSON.stringify(src) : null];
            });
            return finalize(['_id', 'status', '_source'], rows, rowLimit, start);
        }
        // search
        const body = (env.body ?? {});
        if (body.size === undefined)
            body.size = rowLimit;
        const searchRes = await client.search({
            index: env.index,
            ...body,
        });
        return shapeSearchResponse(searchRes, rowLimit, start);
    }
    async close() {
        if (this.client) {
            await this.client.close();
            this.client = undefined;
        }
    }
}
function finalize(columns, rows, rowLimit, start) {
    const truncated = rows.length > rowLimit;
    return {
        columns,
        rows: rows.slice(0, rowLimit),
        rowCount: Math.min(rows.length, rowLimit),
        durationMs: Math.round(performance.now() - start),
        truncated,
    };
}
function shapeSearchResponse(res, rowLimit, start) {
    const r = res;
    // Aggregations-only response → render as JSON in one column.
    if ((!r.hits?.hits || r.hits.hits.length === 0) && r.aggregations) {
        return finalize(['aggregations'], [[JSON.stringify(r.aggregations)]], rowLimit, start);
    }
    const hits = r.hits?.hits ?? [];
    if (hits.length === 0) {
        return finalize(['_id', '_score', '_source'], [], rowLimit, start);
    }
    // Collect union of source keys for column projection (up to 12 columns).
    const keys = new Set();
    for (const h of hits) {
        if (h._source)
            for (const k of Object.keys(h._source))
                keys.add(k);
        if (keys.size >= 12)
            break;
    }
    const columns = ['_id', '_score', ...keys];
    const rows = hits.map((h) => {
        const row = [h._id ?? '', h._score ?? null];
        for (const k of keys) {
            const v = h._source?.[k];
            row.push(typeof v === 'object' && v !== null ? JSON.stringify(v) : (v ?? null));
        }
        return row;
    });
    return finalize(columns, rows, rowLimit, start);
}
//# sourceMappingURL=es-executor.js.map