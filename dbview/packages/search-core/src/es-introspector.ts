import {
  IntrospectionError,
  type SearchIndex,
  type SearchIndexField,
  type SearchStoreSchema,
} from '@dbview/shared';
import type { Client } from '@elastic/elasticsearch';
import { createEsClient } from './es-client.js';

const SYSTEM_INDEX_PREFIXES = ['.', 'security-', 'kibana_'];

export class ElasticsearchIntrospector {
  private client: Client | undefined;

  constructor(private readonly connectionString: string) {}

  private getClient(): Client {
    if (!this.client) {
      this.client = createEsClient(this.connectionString).client;
    }
    return this.client;
  }

  async introspect(): Promise<SearchStoreSchema> {
    try {
      const client = this.getClient();
      const [health, indicesStats, mappingsRes, aliasesRes] = await Promise.all([
        client.cluster.health().catch(() => null),
        client.cat.indices({ format: 'json', bytes: 'b' }).catch(() => []) as Promise<
          Array<Record<string, string>>
        >,
        client.indices.getMapping({}).catch(() => ({})) as Promise<Record<string, unknown>>,
        client.indices.getAlias({}).catch(() => ({})) as Promise<Record<string, unknown>>,
      ]);

      const indices: SearchIndex[] = [];
      for (const stat of indicesStats) {
        const name = stat.index;
        if (!name || SYSTEM_INDEX_PREFIXES.some((p) => name.startsWith(p))) continue;
        const mapping = (mappingsRes as Record<string, { mappings?: { properties?: unknown } }>)[
          name
        ];
        const aliasObj = (aliasesRes as Record<string, { aliases?: Record<string, unknown> }>)[
          name
        ];
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

      const clusterName = (health as { cluster_name?: string } | null)?.cluster_name ?? undefined;

      return {
        kind: 'search',
        dialect: 'elasticsearch',
        cluster: clusterName,
        indices,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(
        `Elasticsearch introspection failed: ${(err as Error).message ?? String(err)}`
      );
    }
  }

  async close(): Promise<void> {
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
function flattenMapping(props: unknown, prefix = ''): SearchIndexField[] {
  if (!props || typeof props !== 'object') return [];
  const out: SearchIndexField[] = [];
  for (const [name, defRaw] of Object.entries(props as Record<string, unknown>)) {
    const def = defRaw as { type?: string; properties?: unknown };
    const fullName = prefix ? `${prefix}.${name}` : name;
    if (def.properties) {
      out.push({ name: fullName, type: def.type ?? 'object' });
      out.push(...flattenMapping(def.properties, fullName));
    } else {
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
