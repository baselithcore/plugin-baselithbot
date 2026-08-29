import { IntrospectionError } from '@dbview/shared';
import { parseQdrantConnection } from './parse.js';
import { QdrantClient } from './qdrant-client.js';
const SAMPLE_LIMIT = 50;
const VALUE_SAMPLE_THRESHOLD = 8;
export class QdrantIntrospector {
    client;
    collectionFilter;
    constructor(connectionString) {
        const target = parseQdrantConnection(connectionString);
        this.client = new QdrantClient(target);
        this.collectionFilter = target.collection;
    }
    async introspect() {
        let collectionNames;
        try {
            if (this.collectionFilter) {
                collectionNames = [this.collectionFilter];
            }
            else {
                collectionNames = await this.client.listCollections();
            }
        }
        catch (err) {
            throw new IntrospectionError(`Qdrant introspection failed: ${err.message}`);
        }
        const collections = [];
        for (const name of collectionNames) {
            try {
                const info = await this.client.getCollection(name);
                const points = await this.client.scroll(name, SAMPLE_LIMIT, true, false).catch(() => []);
                const vectorsCfg = info.config?.params?.vectors;
                let vectorSize = 0;
                let distance = 'cosine';
                let namedVectors;
                if (vectorsCfg && typeof vectorsCfg === 'object') {
                    const flat = vectorsCfg;
                    if (typeof flat.size === 'number') {
                        vectorSize = flat.size;
                        distance = flat.distance ?? distance;
                    }
                    else {
                        const named = vectorsCfg;
                        namedVectors = Object.entries(named).map(([n, v]) => ({
                            name: n,
                            size: v.size,
                        }));
                        const first = namedVectors[0];
                        if (first) {
                            vectorSize = first.size;
                            distance = named[first.name]?.distance ?? distance;
                        }
                    }
                }
                const payloadFields = aggregatePayloadFields(points.map((p) => p.payload ?? {}));
                let pointCount = info.points_count;
                if (typeof pointCount !== 'number') {
                    try {
                        pointCount = await this.client.countPoints(name);
                    }
                    catch {
                        pointCount = undefined;
                    }
                }
                collections.push({
                    id: name,
                    name,
                    vectorSize,
                    distance,
                    pointCount,
                    namedVectors,
                    payloadFields,
                });
            }
            catch (err) {
                // Surface partial schema even when one collection errors out.
                collections.push({
                    id: name,
                    name,
                    vectorSize: 0,
                    distance: 'unknown',
                    payloadFields: [
                        { name: '_error', types: ['STRING'], sampleValues: [err.message] },
                    ],
                });
            }
        }
        return {
            kind: 'vector',
            dialect: 'qdrant',
            collections,
            generatedAt: new Date().toISOString(),
        };
    }
    async close() {
        // No persistent connection to close — fetch is per-request.
    }
}
function aggregatePayloadFields(payloads) {
    const types = new Map();
    const stringValues = new Map();
    for (const p of payloads) {
        for (const [k, v] of Object.entries(p)) {
            const set = types.get(k) ?? new Set();
            set.add(jsTypeOf(v));
            types.set(k, set);
            if (typeof v === 'string') {
                const vs = stringValues.get(k) ?? new Set();
                if (vs.size <= VALUE_SAMPLE_THRESHOLD)
                    vs.add(v);
                stringValues.set(k, vs);
            }
        }
    }
    return [...types.entries()]
        .map(([name, ts]) => {
        const out = { name, types: [...ts] };
        const vs = stringValues.get(name);
        if (vs && vs.size > 0 && vs.size <= VALUE_SAMPLE_THRESHOLD) {
            out.sampleValues = [...vs].sort();
        }
        return out;
    })
        .sort((a, b) => a.name.localeCompare(b.name));
}
function jsTypeOf(v) {
    if (v === null || v === undefined)
        return 'NULL';
    if (Array.isArray(v))
        return 'LIST';
    const t = typeof v;
    if (t === 'number')
        return Number.isInteger(v) ? 'INTEGER' : 'FLOAT';
    if (t === 'boolean')
        return 'BOOLEAN';
    if (t === 'string')
        return 'STRING';
    return 'OBJECT';
}
//# sourceMappingURL=qdrant-introspector.js.map