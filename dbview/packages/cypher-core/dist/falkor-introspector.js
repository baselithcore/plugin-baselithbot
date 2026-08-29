import { FalkorDB } from 'falkordb';
import { IntrospectionError, } from '@dbview/shared';
import { parseFalkorConnection } from './falkor-executor.js';
const SAMPLE_LIMIT = 50;
const VALUE_SAMPLE_THRESHOLD = 10;
/**
 * For high-cardinality string properties (e.g. wiki page bodies) we still want
 * the LLM to see *what kind* of content exists, otherwise it has no grounding
 * for open-ended questions like "di cosa parlano i documenti?". We expose a
 * small number of truncated snippets in that case under `textSnippets`.
 */
const TEXT_SNIPPET_COUNT = 3;
const TEXT_SNIPPET_MAX = 120;
export class FalkorIntrospector {
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
    async introspect() {
        try {
            const db = await this.client();
            const graph = db.selectGraph(this.target.graphName);
            const labelsRes = await graph.roQuery('CALL db.labels() YIELD label RETURN label');
            const labelNames = (labelsRes.data ?? [])
                .map((r) => r.label)
                .filter((v) => typeof v === 'string');
            const relsRes = await graph.roQuery('CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType');
            const relTypes = (relsRes.data ?? [])
                .map((r) => r.relationshipType)
                .filter((v) => typeof v === 'string');
            const labels = [];
            for (const lbl of labelNames) {
                const props = await samplePropertiesForLabel(graph, lbl);
                labels.push({ id: lbl, label: lbl, properties: props });
            }
            const relationships = [];
            let idx = 0;
            for (const rel of relTypes) {
                const combos = await sampleRelationshipCombos(graph, rel);
                const props = await samplePropertiesForRel(graph, rel);
                if (combos.length === 0) {
                    relationships.push({
                        id: `Unknown-${rel}-Unknown-${idx++}`,
                        type: rel,
                        source: 'Unknown',
                        target: 'Unknown',
                        properties: props,
                    });
                }
                else {
                    for (const c of combos) {
                        relationships.push({
                            id: `${c.src}-${rel}-${c.tgt}-${idx++}`,
                            type: rel,
                            source: c.src,
                            target: c.tgt,
                            properties: props,
                        });
                    }
                }
            }
            return {
                kind: 'graph',
                dialect: 'falkordb',
                labels,
                relationships,
                generatedAt: new Date().toISOString(),
            };
        }
        catch (err) {
            throw new IntrospectionError(`FalkorDB introspection failed: ${err.message}`);
        }
    }
    async close() {
        if (!this.clientPromise)
            return;
        const db = await this.clientPromise;
        await db.close();
        this.clientPromise = null;
    }
}
async function samplePropertiesForLabel(graph, label) {
    const res = await graph.roQuery(`MATCH (n:\`${label}\`) WITH n LIMIT ${SAMPLE_LIMIT} RETURN keys(n) AS ks, n AS node`);
    return aggregateProps(res.data ?? [], 'node');
}
async function samplePropertiesForRel(graph, rel) {
    const res = await graph.roQuery(`MATCH ()-[r:\`${rel}\`]->() WITH r LIMIT ${SAMPLE_LIMIT} RETURN keys(r) AS ks, r AS edge`);
    return aggregateProps(res.data ?? [], 'edge');
}
function aggregateProps(rows, entityKey) {
    const seen = new Map();
    const stringValues = new Map();
    // Insertion-ordered string values per property — used to surface
    // first-N snippets for high-cardinality text fields.
    const stringFirstSeen = new Map();
    for (const row of rows) {
        const keys = row.ks;
        const entity = row[entityKey];
        const keyList = Array.isArray(keys)
            ? keys.filter((k) => typeof k === 'string')
            : [];
        const propsObj = entity && typeof entity === 'object' && 'properties' in entity
            ? entity.properties
            : {};
        for (const k of keyList) {
            const v = propsObj[k];
            const t = jsTypeOf(v);
            const set = seen.get(k) ?? new Set();
            set.add(t);
            seen.set(k, set);
            if (typeof v === 'string') {
                const vs = stringValues.get(k) ?? new Set();
                if (vs.size <= VALUE_SAMPLE_THRESHOLD)
                    vs.add(v);
                stringValues.set(k, vs);
                const firsts = stringFirstSeen.get(k) ?? [];
                if (firsts.length < TEXT_SNIPPET_COUNT && !firsts.includes(v)) {
                    firsts.push(v);
                }
                stringFirstSeen.set(k, firsts);
            }
        }
    }
    return [...seen.entries()].map(([name, types]) => {
        const out = { name, types: [...types], nullable: true };
        const vs = stringValues.get(name);
        if (vs && vs.size > 0 && vs.size <= VALUE_SAMPLE_THRESHOLD) {
            out.sampleValues = [...vs].sort();
        }
        else if (types.has('STRING')) {
            // High-cardinality string field: emit a couple of *truncated* snippets so
            // the LLM understands the field carries free-form text. Without this it
            // cannot ground questions about page bodies / descriptions.
            const snippets = (stringFirstSeen.get(name) ?? [])
                .slice(0, TEXT_SNIPPET_COUNT)
                .map((s) => (s.length > TEXT_SNIPPET_MAX ? s.slice(0, TEXT_SNIPPET_MAX - 1) + '…' : s));
            if (snippets.length > 0)
                out.sampleValues = snippets;
        }
        return out;
    });
}
async function sampleRelationshipCombos(graph, rel) {
    const res = await graph.roQuery(`MATCH (a)-[:\`${rel}\`]->(b) RETURN DISTINCT labels(a) AS srcLabels, labels(b) AS tgtLabels LIMIT 25`);
    const out = [];
    for (const row of res.data ?? []) {
        const srcLabels = row.srcLabels;
        const tgtLabels = row.tgtLabels;
        const src = Array.isArray(srcLabels) && typeof srcLabels[0] === 'string' ? srcLabels[0] : 'Unknown';
        const tgt = Array.isArray(tgtLabels) && typeof tgtLabels[0] === 'string' ? tgtLabels[0] : 'Unknown';
        out.push({ src, tgt });
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
        return Number.isInteger(v) ? 'INTEGER' : 'FLOAT';
    if (t === 'boolean')
        return 'BOOLEAN';
    if (t === 'string')
        return 'STRING';
    return 'ANY';
}
//# sourceMappingURL=falkor-introspector.js.map