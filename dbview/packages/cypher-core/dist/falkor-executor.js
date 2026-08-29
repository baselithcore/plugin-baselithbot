import { FalkorDB } from 'falkordb';
/**
 * Connection string: `falkor://[user]:[pass]@host:port/graphName`
 * Falls back to `redis://` scheme. graphName from URL path.
 */
export function parseFalkorConnection(connectionString) {
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
export class FalkorExecutor {
    clientPromise = null;
    target;
    constructor(connectionString) {
        this.target = parseFalkorConnection(connectionString);
    }
    client() {
        if (!this.clientPromise) {
            this.clientPromise = FalkorDB.connect(this.target.options);
        }
        return this.clientPromise;
    }
    async run(query, rowLimit) {
        const db = await this.client();
        const graph = db.selectGraph(this.target.graphName);
        const start = performance.now();
        const res = await graph.roQuery(query);
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
    async close() {
        if (!this.clientPromise)
            return;
        const db = await this.clientPromise;
        await db.close();
        this.clientPromise = null;
    }
}
function normalizeFalkorValue(v) {
    if (v === null || v === undefined)
        return v;
    if (typeof v !== 'object')
        return v;
    const obj = v;
    if ('labels' in obj && 'properties' in obj) {
        return {
            _kind: 'node',
            _labels: obj.labels ?? [],
            ...(obj.properties ?? {}),
        };
    }
    if ('relationshipType' in obj && 'properties' in obj) {
        return {
            _kind: 'relationship',
            _type: obj.relationshipType,
            ...(obj.properties ?? {}),
        };
    }
    return v;
}
//# sourceMappingURL=falkor-executor.js.map