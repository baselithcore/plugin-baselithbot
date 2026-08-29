import neo4j from 'neo4j-driver';
import { IntrospectionError, } from '@dbview/shared';
export class Neo4jIntrospector {
    driver;
    constructor(connectionString) {
        const url = new URL(connectionString);
        const username = decodeURIComponent(url.username || 'neo4j');
        const password = decodeURIComponent(url.password || 'neo4j');
        url.username = '';
        url.password = '';
        this.driver = neo4j.driver(url.toString(), neo4j.auth.basic(username, password), {
            connectionAcquisitionTimeout: 5_000,
            maxConnectionPoolSize: 4,
        });
    }
    async introspect() {
        const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
        try {
            const labels = await this.collectLabels(session);
            const relationships = await this.collectRelationships(session);
            for (const lbl of labels) {
                await this.attachLabelSamples(session, lbl);
            }
            const sampledRelTypes = new Set();
            for (const rel of relationships) {
                if (sampledRelTypes.has(rel.type))
                    continue;
                sampledRelTypes.add(rel.type);
                await this.attachRelSamples(session, rel.type, relationships);
            }
            return {
                kind: 'graph',
                dialect: 'neo4j',
                labels,
                relationships,
                generatedAt: new Date().toISOString(),
            };
        }
        catch (err) {
            throw new IntrospectionError(`Neo4j introspection failed: ${err.message}`);
        }
        finally {
            await session.close();
        }
    }
    async attachLabelSamples(session, label) {
        const stringProps = label.properties.filter((p) => p.types.some((t) => /string/i.test(t)));
        if (stringProps.length === 0)
            return;
        const res = await session.run(`MATCH (n:\`${label.label}\`) WITH n LIMIT 500
       UNWIND $props AS k
       WITH k, n[k] AS v
       WHERE v IS NOT NULL AND toString(v) = v
       WITH k, collect(DISTINCT v) AS vals
       RETURN k, vals`, { props: stringProps.map((p) => p.name) });
        applySamples(res.records, label.properties);
    }
    async attachRelSamples(session, relType, rels) {
        const sampleProps = rels.find((r) => r.type === relType)?.properties ?? [];
        const stringProps = sampleProps.filter((p) => p.types.some((t) => /string/i.test(t)));
        if (stringProps.length === 0)
            return;
        const res = await session.run(`MATCH ()-[r:\`${relType}\`]->() WITH r LIMIT 500
       UNWIND $props AS k
       WITH k, r[k] AS v
       WHERE v IS NOT NULL AND toString(v) = v
       WITH k, collect(DISTINCT v) AS vals
       RETURN k, vals`, { props: stringProps.map((p) => p.name) });
        for (const rel of rels.filter((r) => r.type === relType)) {
            applySamples(res.records, rel.properties);
        }
    }
    async collectLabels(session) {
        const propsRes = await session.run(`
      CALL db.schema.nodeTypeProperties()
      YIELD nodeType, propertyName, propertyTypes, mandatory
      RETURN nodeType, collect({
        name: propertyName,
        types: propertyTypes,
        mandatory: mandatory
      }) AS properties
    `);
        const labelMap = new Map();
        for (const rec of propsRes.records) {
            const nodeType = rec.get('nodeType'); // ":`Label`" or ":`L1`:`L2`"
            const props = rec.get('properties');
            const labels = parseNodeType(nodeType);
            for (const label of labels) {
                const properties = props
                    .filter((p) => p.name)
                    .map((p) => ({
                    name: p.name,
                    types: p.types ?? ['ANY'],
                    nullable: p.mandatory !== true,
                }));
                const existing = labelMap.get(label);
                if (existing) {
                    mergeProperties(existing.properties, properties);
                }
                else {
                    labelMap.set(label, { id: label, label, properties });
                }
            }
        }
        return [...labelMap.values()];
    }
    async collectRelationships(session) {
        const propsRes = await session.run(`
      CALL db.schema.relTypeProperties()
      YIELD relType, propertyName, propertyTypes, mandatory
      RETURN relType, collect({
        name: propertyName,
        types: propertyTypes,
        mandatory: mandatory
      }) AS properties
    `);
        const propsByType = new Map();
        for (const rec of propsRes.records) {
            const relType = stripBackticks(rec.get('relType'));
            const props = rec.get('properties');
            propsByType.set(relType, props
                .filter((p) => p.name)
                .map((p) => ({
                name: p.name,
                types: p.types ?? ['ANY'],
                nullable: p.mandatory !== true,
            })));
        }
        const combinationsRes = await session.run(`
      MATCH (a)-[r]->(b)
      RETURN DISTINCT labels(a) AS srcLabels, type(r) AS relType, labels(b) AS tgtLabels
    `);
        const out = [];
        let idx = 0;
        for (const rec of combinationsRes.records) {
            const srcLabels = rec.get('srcLabels') ?? [];
            const tgtLabels = rec.get('tgtLabels') ?? [];
            const relType = rec.get('relType');
            const src = srcLabels[0] ?? 'Unknown';
            const tgt = tgtLabels[0] ?? 'Unknown';
            out.push({
                id: `${src}-${relType}-${tgt}-${idx++}`,
                type: relType,
                source: src,
                target: tgt,
                properties: propsByType.get(relType) ?? [],
            });
        }
        return out;
    }
    async close() {
        await this.driver.close();
    }
}
function parseNodeType(s) {
    // Format: ":`Label1`:`Label2`"
    const matches = s.match(/`([^`]+)`/g) ?? [];
    return matches.map((m) => m.slice(1, -1));
}
function stripBackticks(s) {
    const m = s.match(/`([^`]+)`/);
    return m?.[1] ?? s;
}
function mergeProperties(existing, incoming) {
    const seen = new Set(existing.map((p) => p.name));
    for (const p of incoming) {
        if (!seen.has(p.name)) {
            existing.push(p);
            seen.add(p.name);
        }
    }
}
const VALUE_SAMPLE_THRESHOLD = 10;
function applySamples(records, props) {
    const byKey = new Map();
    for (const p of props)
        byKey.set(p.name, p);
    for (const rec of records) {
        const k = rec.get('k');
        const vals = rec.get('vals');
        if (!Array.isArray(vals))
            continue;
        const distinct = vals.filter((v) => typeof v === 'string');
        if (distinct.length === 0 || distinct.length > VALUE_SAMPLE_THRESHOLD)
            continue;
        const target = byKey.get(k);
        if (target)
            target.sampleValues = [...new Set(distinct)].sort();
    }
}
//# sourceMappingURL=introspector.js.map