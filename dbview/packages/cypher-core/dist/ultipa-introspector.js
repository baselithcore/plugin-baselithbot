import { IntrospectionError, } from '@dbview/shared';
import { createUltipaClient, releaseUltipaClient } from './ultipa-client.js';
export class UltipaIntrospector {
    clientP = null;
    connectionString;
    constructor(connectionString) {
        this.connectionString = connectionString;
    }
    async introspect() {
        try {
            const { client, graph } = await this.connect();
            const nodeTypes = await this.fetchNodeTypes(client, graph);
            const edgeTypes = await this.fetchEdgeTypes(client, graph);
            if (nodeTypes.length === 0 && edgeTypes.length === 0) {
                const available = await client
                    .listGraphs()
                    .then((gs) => gs.map((g) => g.name))
                    .catch(() => []);
                throw new Error(`Ultipa server returned no node/edge types for graph '${graph}'. ` +
                    `Available graphs: [${available.join(', ') || '<none visible>'}]. ` +
                    `Verify the graph name matches one on the server and that the user has read permissions.`);
            }
            // Sample each label's properties via one targeted query. Skip the
            // showNodeProperty + DDL fallbacks (each adds 3 round-trips per
            // label and cloud DBaaS averages ~2s/RPC). When the SDK helper
            // already returned properties we keep them.
            const labels = await mapConcurrent(nodeTypes, 8, async (nt) => {
                let props = nt.properties;
                if (props.length === 0) {
                    props = await sampleNodeProperties(client, graph, nt.name);
                }
                return {
                    id: nt.name,
                    label: nt.name,
                    properties: props.map((p) => ({
                        name: p.name,
                        types: [normalizeType(p.type)],
                        nullable: true,
                    })),
                };
            });
            const edgeProps = new Map();
            for (const et of edgeTypes) {
                edgeProps.set(et.name, et.properties.map((p) => ({
                    name: p.name,
                    types: [normalizeType(p.type)],
                    nullable: true,
                })));
            }
            const relationships = await this.discoverRelationships(client, graph, edgeProps);
            return {
                kind: 'graph',
                dialect: 'ultipa',
                labels,
                relationships,
                generatedAt: new Date().toISOString(),
            };
        }
        catch (err) {
            throw new IntrospectionError(`Ultipa introspection failed: ${err.message}`);
        }
    }
    async fetchNodeTypes(client, graph) {
        for (let attempt = 0; attempt < 4; attempt++) {
            try {
                const helper = await client.showNodeTypes({ graphName: graph, timeout: 30000 });
                if (helper.length > 0) {
                    return helper.map((nt) => ({ name: nt.name, properties: nt.properties }));
                }
            }
            catch {
                // Fall through to retry / DDL.
            }
            try {
                await client.useGraph(graph);
            }
            catch {
                /* ignore */
            }
            const ddl = await runShowTypes(client, graph, 'NODE');
            if (ddl.length > 0)
                return ddl;
            const sampled = await discoverNodeTypesFromData(client, graph);
            if (sampled.length > 0)
                return sampled;
            await new Promise((r) => setTimeout(r, 250));
        }
        return [];
    }
    async fetchEdgeTypes(client, graph) {
        for (let attempt = 0; attempt < 4; attempt++) {
            try {
                const helper = await client.showEdgeTypes({ graphName: graph, timeout: 30000 });
                if (helper.length > 0) {
                    return helper.map((et) => ({ name: et.name, properties: et.properties }));
                }
            }
            catch {
                // Fall through to retry / DDL.
            }
            try {
                await client.useGraph(graph);
            }
            catch {
                /* ignore */
            }
            const ddl = await runShowTypes(client, graph, 'EDGE');
            if (ddl.length > 0)
                return ddl;
            const sampled = await discoverEdgeTypesFromData(client, graph);
            if (sampled.length > 0)
                return sampled;
            // Brief backoff before next outer attempt.
            await new Promise((r) => setTimeout(r, 250));
        }
        return [];
    }
    async close() {
        if (!this.clientP)
            return;
        try {
            await this.clientP;
        }
        catch {
            /* connect failed; nothing to release */
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
                const graph = await resolveGraph(client, target.defaultGraph);
                try {
                    await client.useGraph(graph);
                }
                catch {
                    // Pre-v6 servers route via QueryConfig.graphName; ignore.
                }
                return { client, graph };
            })();
        }
        return this.clientP;
    }
    async discoverRelationships(client, graph, edgeProps) {
        if (edgeProps.size === 0)
            return [];
        // Per-edge-type sampling in parallel. One bounded DISTINCT scan per
        // edge type stays under ~half a second on cloud DBaaS and surfaces
        // all (source, target) label combinations the type actually uses —
        // a single LIMIT 1 sample would lose every combo but the first.
        let idx = 0;
        const entries = [...edgeProps];
        const sampled = await mapConcurrent(entries, 8, async ([type, props]) => {
            const combos = await sampleEdgeCombos(client, graph, type);
            return { type, props, combos };
        });
        const out = [];
        for (const s of sampled) {
            if (s.combos.length === 0) {
                out.push({
                    id: `Unknown-${s.type}-Unknown-${idx++}`,
                    type: s.type,
                    source: 'Unknown',
                    target: 'Unknown',
                    properties: s.props,
                });
                continue;
            }
            for (const c of s.combos) {
                out.push({
                    id: `${c.source}-${s.type}-${c.target}-${idx++}`,
                    type: s.type,
                    source: c.source,
                    target: c.target,
                    properties: s.props,
                });
            }
        }
        return out;
    }
}
async function resolveGraph(client, preferred) {
    if (preferred)
        return preferred;
    const graphs = await client.listGraphs();
    const first = graphs[0];
    if (!first) {
        throw new Error('No graphs found on the Ultipa server.');
    }
    return first.name;
}
function pickFirstLabel(v) {
    if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'string')
        return v[0];
    if (typeof v === 'string' && v.length > 0)
        return v;
    return 'Unknown';
}
function normalizeType(t) {
    return t ? t.toUpperCase() : 'ANY';
}
async function mapConcurrent(items, concurrency, fn) {
    const out = new Array(items.length);
    let next = 0;
    const workers = [];
    const n = Math.min(concurrency, items.length);
    for (let w = 0; w < n; w++) {
        workers.push((async () => {
            while (true) {
                const i = next++;
                if (i >= items.length)
                    return;
                out[i] = await fn(items[i]);
            }
        })());
    }
    await Promise.all(workers);
    return out;
}
/**
 * Fallback to raw GQL DDL when the convenience helper returns nothing
 * (e.g. older v6 builds where `showNodeTypes()` does not honour
 * `graphName` and the session graph differs from the requested one).
 */
async function runShowTypes(client, graph, kind) {
    const queries = kind === 'NODE'
        ? ['SHOW NODE TYPES', 'SHOW NODE SCHEMAS', 'SHOW SCHEMA NODE']
        : ['SHOW EDGE TYPES', 'SHOW EDGE SCHEMAS', 'SHOW SCHEMA EDGE'];
    for (const q of queries) {
        try {
            const res = await client.gql(q, { graphName: graph, readOnly: true, timeout: 30000 });
            if (res.rows.length === 0)
                continue;
            const out = [];
            const cols = res.columns;
            const nameIdx = findColumnIndex(cols, ['name', 'schema', 'schema_name', 'type']);
            const propsIdx = findColumnIndex(cols, ['properties', 'props']);
            for (const row of res.rows) {
                const name = nameIdx >= 0 ? String(row.get(nameIdx) ?? '') : String(row.get(0) ?? '');
                if (!name)
                    continue;
                const propsVal = propsIdx >= 0 ? row.get(propsIdx) : undefined;
                out.push({ name, properties: parseProperties(propsVal) });
            }
            if (out.length > 0)
                return out;
        }
        catch {
            // Try next dialect of the DDL.
        }
    }
    return [];
}
function findColumnIndex(cols, candidates) {
    for (const c of candidates) {
        const i = cols.findIndex((col) => col.toLowerCase() === c);
        if (i >= 0)
            return i;
    }
    return -1;
}
async function sampleNodeProperties(client, graph, label) {
    try {
        const res = await client.gql(`MATCH (n:\`${label}\`) RETURN n LIMIT 5`, {
            graphName: graph,
            readOnly: true,
        });
        const seen = new Map();
        for (const row of res.rows) {
            const v = row.get(0);
            const props = extractNodeProperties(v);
            for (const [k, val] of Object.entries(props)) {
                if (!seen.has(k))
                    seen.set(k, jsTypeOf(val));
            }
        }
        return [...seen.entries()].map(([name, type]) => ({ name, type }));
    }
    catch {
        return [];
    }
}
/**
 * Unwrap user-defined properties from an Ultipa Node payload. v6 servers
 * surface nodes either as `{id, labels:[...], properties:"<json>"}` or as
 * `{schema, values:{...}}` depending on the codepath, so handle both.
 */
function extractNodeProperties(v) {
    if (!v || typeof v !== 'object')
        return {};
    const obj = v;
    if (obj.values && typeof obj.values === 'object') {
        return obj.values;
    }
    if (typeof obj.properties === 'string') {
        try {
            const parsed = JSON.parse(obj.properties);
            if (parsed && typeof parsed === 'object')
                return parsed;
        }
        catch {
            return {};
        }
    }
    if (obj.properties && typeof obj.properties === 'object' && !Array.isArray(obj.properties)) {
        return obj.properties;
    }
    const out = {};
    for (const [k, val] of Object.entries(obj)) {
        if (k === 'id' || k === 'uuid' || k === 'schema' || k === 'labels' || k === 'values')
            continue;
        if (k.startsWith('_'))
            continue;
        out[k] = val;
    }
    return out;
}
function jsTypeOf(v) {
    if (v === null || v === undefined)
        return 'NULL';
    if (Array.isArray(v))
        return 'LIST';
    const t = typeof v;
    if (t === 'number')
        return Number.isInteger(v) ? 'INT64' : 'DOUBLE';
    if (t === 'boolean')
        return 'BOOL';
    if (t === 'string')
        return 'STRING';
    return 'STRING';
}
async function sampleEdgeCombos(client, graph, edgeType) {
    try {
        const res = await client.gql(`MATCH (a)-[r:\`${edgeType}\`]->(b) RETURN DISTINCT labels(a) AS src, labels(b) AS tgt LIMIT 25`, { graphName: graph, readOnly: true, timeout: 30000 });
        const seen = new Set();
        const out = [];
        for (const row of res.rows) {
            const source = pickFirstLabel(row.get(0));
            const target = pickFirstLabel(row.get(1));
            const key = `${source} ${target}`;
            if (seen.has(key))
                continue;
            seen.add(key);
            out.push({ source, target });
        }
        return out;
    }
    catch {
        return [];
    }
}
async function discoverNodeTypesFromData(client, graph) {
    try {
        const res = await client.gql('MATCH (n) RETURN DISTINCT labels(n) AS labels LIMIT 200', {
            graphName: graph,
            readOnly: true,
            timeout: 30000,
        });
        const seen = new Set();
        for (const row of res.rows) {
            const v = row.get(0);
            if (Array.isArray(v)) {
                for (const l of v)
                    if (typeof l === 'string' && l)
                        seen.add(l);
            }
            else if (typeof v === 'string' && v) {
                seen.add(v);
            }
        }
        return [...seen].map((name) => ({ name, properties: [] }));
    }
    catch {
        return [];
    }
}
async function discoverEdgeTypesFromData(client, graph) {
    try {
        const res = await client.gql('MATCH ()-[r]->() RETURN DISTINCT type(r) AS t LIMIT 200', {
            graphName: graph,
            readOnly: true,
            timeout: 30000,
        });
        const seen = new Set();
        for (const row of res.rows) {
            const v = row.get(0);
            if (typeof v === 'string' && v)
                seen.add(v);
        }
        return [...seen].map((name) => ({ name, properties: [] }));
    }
    catch {
        return [];
    }
}
function parseProperties(v) {
    if (!v)
        return [];
    if (Array.isArray(v)) {
        return v
            .map((p) => {
            if (p && typeof p === 'object') {
                const o = p;
                const name = String(o.name ?? o.propertyName ?? '');
                const type = String(o.type ?? o.propertyType ?? 'ANY');
                return name ? { name, type } : null;
            }
            return null;
        })
            .filter((p) => p !== null);
    }
    if (typeof v === 'string') {
        try {
            return parseProperties(JSON.parse(v));
        }
        catch {
            return [];
        }
    }
    return [];
}
//# sourceMappingURL=ultipa-introspector.js.map