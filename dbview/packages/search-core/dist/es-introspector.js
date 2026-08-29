import { IntrospectionError, } from '@dbview/shared';
import { createEsClient } from './es-client.js';
const SYSTEM_INDEX_PREFIXES = ['.', 'security-', 'kibana_'];
export class ElasticsearchIntrospector {
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
    async introspect() {
        try {
            const client = this.getClient();
            const [health, indicesStats, mappingsRes, aliasesRes] = await Promise.all([
                client.cluster.health().catch(() => null),
                client.cat.indices({ format: 'json', bytes: 'b' }).catch(() => []),
                client.indices.getMapping({}).catch(() => ({})),
                client.indices.getAlias({}).catch(() => ({})),
            ]);
            const indices = [];
            for (const stat of indicesStats) {
                const name = stat.index;
                if (!name || SYSTEM_INDEX_PREFIXES.some((p) => name.startsWith(p)))
                    continue;
                const mapping = mappingsRes[name];
                const aliasObj = aliasesRes[name];
                const aliases = aliasObj?.aliases ? Object.keys(aliasObj.aliases) : [];
                const fields = flattenMapping(mapping?.mappings?.properties);
                indices.push({
                    id: name,
                    name,
                    docCount: stat['docs.count'] ? Number(stat['docs.count']) : undefined,
                    sizeBytes: stat['store.size'] ? Number(stat['store.size']) : undefined,
                    aliases,
                    fields,
                });
            }
            const clusterName = health?.cluster_name ?? undefined;
            return {
                kind: 'search',
                dialect: 'elasticsearch',
                cluster: clusterName,
                indices,
                generatedAt: new Date().toISOString(),
            };
        }
        catch (err) {
            throw new IntrospectionError(`Elasticsearch introspection failed: ${err.message ?? String(err)}`);
        }
    }
    async close() {
        if (this.client) {
            await this.client.close();
            this.client = undefined;
        }
    }
}
/**
 * Flatten ES mapping `properties` recursively into dotted-path SearchIndexField list.
 * Stops at primitive/object/nested leaves.
 */
function flattenMapping(props, prefix = '') {
    if (!props || typeof props !== 'object')
        return [];
    const out = [];
    for (const [name, defRaw] of Object.entries(props)) {
        const def = defRaw;
        const fullName = prefix ? `${prefix}.${name}` : name;
        if (def.properties) {
            out.push({ name: fullName, type: def.type ?? 'object' });
            out.push(...flattenMapping(def.properties, fullName));
        }
        else {
            const type = def.type ?? 'unknown';
            out.push({
                name: fullName,
                type,
                analyzed: type === 'text',
            });
        }
    }
    return out;
}
//# sourceMappingURL=es-introspector.js.map