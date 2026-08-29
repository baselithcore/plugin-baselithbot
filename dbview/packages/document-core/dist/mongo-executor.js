import { createMongoClient } from './mongo-client.js';
import { parseMongoEnvelope, validateMongoEnvelope } from './safety.js';
/**
 * Read-only MongoDB executor. Accepts a JSON envelope (see safety.ts) and
 * dispatches against the connection's default DB. Results are shaped into
 * the unified columns/rows envelope.
 */
export class MongoExecutor {
    connectionString;
    client;
    database = '';
    constructor(connectionString) {
        this.connectionString = connectionString;
    }
    async getClient() {
        if (!this.client) {
            const { client, database } = createMongoClient(this.connectionString);
            this.client = client;
            this.database = database;
            await client.connect();
        }
        return this.client;
    }
    async run(query, rowLimit) {
        const start = performance.now();
        const env = parseMongoEnvelope(query);
        validateMongoEnvelope(env);
        const client = await this.getClient();
        const db = client.db(this.database);
        if (env.op === 'collections') {
            const list = await db.listCollections({}, { nameOnly: false }).toArray();
            const rows = list.map((c) => [c.name, (c.type ?? 'collection')]);
            return finalize(['name', 'type'], rows, rowLimit, start);
        }
        if (env.op === 'count') {
            const n = await db.collection(env.collection).countDocuments(env.filter ?? {});
            return finalize(['count'], [[n]], rowLimit, start);
        }
        if (env.op === 'find') {
            const cursor = db
                .collection(env.collection)
                .find(env.filter ?? {}, { projection: env.projection })
                .limit(env.limit ?? rowLimit);
            if (env.sort)
                cursor.sort(env.sort);
            if (env.skip)
                cursor.skip(env.skip);
            const docs = await cursor.toArray();
            return shapeDocs(docs, rowLimit, start);
        }
        if (env.op === 'distinct') {
            const values = await db.collection(env.collection).distinct(env.field, env.filter ?? {});
            const rows = values.map((v) => [
                typeof v === 'object' && v !== null ? JSON.stringify(v) : (v ?? null),
            ]);
            return finalize([env.field], rows, rowLimit, start);
        }
        if (env.op === 'aggregate') {
            const docs = await db
                .collection(env.collection)
                .aggregate(env.pipeline ?? [], { allowDiskUse: false })
                .limit(rowLimit + 1)
                .toArray();
            return shapeDocs(docs, rowLimit, start);
        }
        if (env.op === 'indexes') {
            const idxs = await db.collection(env.collection).indexes();
            const rows = idxs.map((i) => [
                i.name ?? '',
                JSON.stringify(i.key ?? {}),
            ]);
            return finalize(['name', 'key'], rows, rowLimit, start);
        }
        // stats
        const stats = (await db.command({ collStats: env.collection }));
        return finalize(['metric', 'value'], Object.entries(stats)
            .filter(([k]) => !k.startsWith('$') && !k.startsWith('wiredTiger'))
            .map(([k, v]) => [k, typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)]), rowLimit, start);
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
function shapeDocs(docs, rowLimit, start) {
    if (docs.length === 0)
        return finalize(['_id'], [], rowLimit, start);
    const keys = new Set();
    for (const d of docs) {
        for (const k of Object.keys(d))
            keys.add(k);
        if (keys.size >= 12)
            break;
    }
    const columns = [...keys];
    const rows = docs.map((d) => columns.map((k) => {
        const v = d[k];
        if (v === null || v === undefined)
            return null;
        if (typeof v === 'object')
            return JSON.stringify(v);
        return v;
    }));
    return finalize(columns, rows, rowLimit, start);
}
//# sourceMappingURL=mongo-executor.js.map