/**
 * Salesforce schema introspector.
 *
 * Strategy:
 *  - List sObjects via `/services/data/<v>/sobjects`. Filter: queryable && !deprecated.
 *    Skip system feed/share/history junk to keep the graph readable.
 *  - Describe each kept sObject in parallel (bounded concurrency) to gather fields + lookups.
 *  - Build relational SchemaGraph: sObject → TableNode, reference field → FKEdge.
 */
export class SalesforceIntrospector {
    client;
    apiVersion;
    constructor(client, apiVersion) {
        this.client = client;
        this.apiVersion = apiVersion;
    }
    async introspect() {
        const list = await this.client.get(`/services/data/${this.apiVersion}/sobjects`);
        const targets = list.sobjects.filter((s) => isInterestingSObject(s));
        const describes = await runWithConcurrency(targets, 8, (s) => this.client.get(`/services/data/${this.apiVersion}/sobjects/${encodeURIComponent(s.name)}/describe`));
        const known = new Set(targets.map((s) => s.name));
        const tables = describes.map((d) => describeToTable(d));
        const edges = [];
        for (const d of describes) {
            for (const f of d.fields) {
                if (!f.referenceTo)
                    continue;
                for (const target of f.referenceTo) {
                    if (!known.has(target))
                        continue;
                    edges.push({
                        id: `${d.name}.${f.name}->${target}.Id`,
                        source: `salesforce.${d.name}`,
                        sourceColumn: f.name,
                        target: `salesforce.${target}`,
                        targetColumn: 'Id',
                        constraintName: f.relationshipName ?? undefined,
                    });
                }
            }
        }
        return {
            kind: 'relational',
            dialect: 'salesforce',
            tables,
            edges,
            generatedAt: new Date().toISOString(),
        };
    }
    async close() {
        await this.client.close();
    }
}
function describeToTable(d) {
    const refSet = new Set(d.fields.filter((f) => f.referenceTo && f.referenceTo.length).map((f) => f.name));
    const columns = d.fields.map((f) => ({
        name: f.name,
        dataType: f.type,
        nullable: f.nillable,
        isPrimaryKey: f.name === 'Id',
        isForeignKey: refSet.has(f.name),
        isUnique: f.unique ?? false,
        defaultValue: f.defaultValue == null ? null : String(f.defaultValue),
    }));
    return {
        id: `salesforce.${d.name}`,
        schema: 'salesforce',
        name: d.name,
        columns,
    };
}
function isInterestingSObject(s) {
    if (!s.queryable)
        return false;
    if (s.deprecatedAndHidden)
        return false;
    // Drop high-volume system/audit sObjects that bloat the graph without value.
    return !/(History|Feed|Share|ChangeEvent|Tag|Vote|Subscription|StreamingChannel)$/.test(s.name);
}
async function runWithConcurrency(items, concurrency, fn) {
    const out = new Array(items.length);
    let next = 0;
    const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
        while (true) {
            const i = next++;
            if (i >= items.length)
                return;
            const item = items[i];
            out[i] = await fn(item);
        }
    });
    await Promise.all(workers);
    return out;
}
//# sourceMappingURL=introspector.js.map