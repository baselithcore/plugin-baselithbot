import type { VectorCollection, VectorPayloadField, VectorStoreSchema } from '@dbview/shared';
import { IntrospectionError } from '@dbview/shared';
import { parseQdrantConnection } from './parse.js';
import { QdrantClient } from './qdrant-client.js';

const SAMPLE_LIMIT = 50;
const VALUE_SAMPLE_THRESHOLD = 8;

export class QdrantIntrospector {
  private readonly client: QdrantClient;
  private readonly collectionFilter?: string;

  constructor(connectionString: string) {
    const target = parseQdrantConnection(connectionString);
    this.client = new QdrantClient(target);
    this.collectionFilter = target.collection;
  }

  async introspect(): Promise<VectorStoreSchema> {
    let collectionNames: string[];
    try {
      if (this.collectionFilter) {
        collectionNames = [this.collectionFilter];
      } else {
        collectionNames = await this.client.listCollections();
      }
    } catch (err) {
      throw new IntrospectionError(`Qdrant introspection failed: ${(err as Error).message}`);
    }

    const collections: VectorCollection[] = [];
    for (const name of collectionNames) {
      try {
        const info = await this.client.getCollection(name);
        const points = await this.client.scroll(name, SAMPLE_LIMIT, true, false).catch(() => []);
        const vectorsCfg = info.config?.params?.vectors;
        let vectorSize = 0;
        let distance = 'cosine';
        let namedVectors: VectorCollection['namedVectors'];
        if (vectorsCfg && typeof vectorsCfg === 'object') {
          const flat = vectorsCfg as { size?: number; distance?: string };
          if (typeof flat.size === 'number') {
            vectorSize = flat.size;
            distance = flat.distance ?? distance;
          } else {
            const named = vectorsCfg as Record<string, { size: number; distance: string }>;
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
        let pointCount: number | undefined = info.points_count;
        if (typeof pointCount !== 'number') {
          try {
            pointCount = await this.client.countPoints(name);
          } catch {
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
      } catch (err) {
        // Surface partial schema even when one collection errors out.
        collections.push({
          id: name,
          name,
          vectorSize: 0,
          distance: 'unknown',
          payloadFields: [
            { name: '_error', types: ['STRING'], sampleValues: [(err as Error).message] },
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

  async close(): Promise<void> {
    // No persistent connection to close — fetch is per-request.
  }
}

function aggregatePayloadFields(payloads: Array<Record<string, unknown>>): VectorPayloadField[] {
  const types = new Map<string, Set<string>>();
  const stringValues = new Map<string, Set<string>>();
  for (const p of payloads) {
    for (const [k, v] of Object.entries(p)) {
      const set = types.get(k) ?? new Set<string>();
      set.add(jsTypeOf(v));
      types.set(k, set);
      if (typeof v === 'string') {
        const vs = stringValues.get(k) ?? new Set<string>();
        if (vs.size <= VALUE_SAMPLE_THRESHOLD) vs.add(v);
        stringValues.set(k, vs);
      }
    }
  }
  return [...types.entries()]
    .map(([name, ts]) => {
      const out: VectorPayloadField = { name, types: [...ts] };
      const vs = stringValues.get(name);
      if (vs && vs.size > 0 && vs.size <= VALUE_SAMPLE_THRESHOLD) {
        out.sampleValues = [...vs].sort();
      }
      return out;
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

function jsTypeOf(v: unknown): string {
  if (v === null || v === undefined) return 'NULL';
  if (Array.isArray(v)) return 'LIST';
  const t = typeof v;
  if (t === 'number') return Number.isInteger(v) ? 'INTEGER' : 'FLOAT';
  if (t === 'boolean') return 'BOOLEAN';
  if (t === 'string') return 'STRING';
  return 'OBJECT';
}
