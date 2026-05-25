import { FalkorDB } from 'falkordb';
import {
  IntrospectionError,
  type NodeLabel,
  type PropertyGraphSchema,
  type PropertyKey,
  type RelationshipType,
} from '@dbview/shared';
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

type Record = { [k: string]: unknown };
interface QueryClient {
  roQuery<T>(query: string): Promise<{ data?: Array<T> }>;
}

export class FalkorIntrospector {
  private clientPromise: Promise<FalkorDB> | null = null;
  private readonly target: ReturnType<typeof parseFalkorConnection>;

  constructor(connectionString: string) {
    this.target = parseFalkorConnection(connectionString);
  }

  private client(): Promise<FalkorDB> {
    if (!this.clientPromise) {
      this.clientPromise = FalkorDB.connect(this.target.options);
    }
    return this.clientPromise;
  }

  async introspect(): Promise<PropertyGraphSchema> {
    try {
      const db = await this.client();
      const graph = db.selectGraph(this.target.graphName) as unknown as QueryClient;

      const labelsRes = await graph.roQuery<Record>('CALL db.labels() YIELD label RETURN label');
      const labelNames = (labelsRes.data ?? [])
        .map((r) => r.label)
        .filter((v): v is string => typeof v === 'string');

      const relsRes = await graph.roQuery<Record>(
        'CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType'
      );
      const relTypes = (relsRes.data ?? [])
        .map((r) => r.relationshipType)
        .filter((v): v is string => typeof v === 'string');

      const labels: NodeLabel[] = [];
      for (const lbl of labelNames) {
        const props = await samplePropertiesForLabel(graph, lbl);
        labels.push({ id: lbl, label: lbl, properties: props });
      }

      const relationships: RelationshipType[] = [];
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
        } else {
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
    } catch (err) {
      throw new IntrospectionError(`FalkorDB introspection failed: ${(err as Error).message}`);
    }
  }

  async close(): Promise<void> {
    if (!this.clientPromise) return;
    const db = await this.clientPromise;
    await db.close();
    this.clientPromise = null;
  }
}

async function samplePropertiesForLabel(graph: QueryClient, label: string): Promise<PropertyKey[]> {
  const res = await graph.roQuery<Record>(
    `MATCH (n:\`${label}\`) WITH n LIMIT ${SAMPLE_LIMIT} RETURN keys(n) AS ks, n AS node`
  );
  return aggregateProps(res.data ?? [], 'node');
}

async function samplePropertiesForRel(graph: QueryClient, rel: string): Promise<PropertyKey[]> {
  const res = await graph.roQuery<Record>(
    `MATCH ()-[r:\`${rel}\`]->() WITH r LIMIT ${SAMPLE_LIMIT} RETURN keys(r) AS ks, r AS edge`
  );
  return aggregateProps(res.data ?? [], 'edge');
}

function aggregateProps(rows: Record[], entityKey: 'node' | 'edge'): PropertyKey[] {
  const seen = new Map<string, Set<string>>();
  const stringValues = new Map<string, Set<string>>();
  // Insertion-ordered string values per property — used to surface
  // first-N snippets for high-cardinality text fields.
  const stringFirstSeen = new Map<string, string[]>();
  for (const row of rows) {
    const keys = row.ks;
    const entity = row[entityKey];
    const keyList = Array.isArray(keys)
      ? keys.filter((k): k is string => typeof k === 'string')
      : [];
    const propsObj =
      entity && typeof entity === 'object' && 'properties' in (entity as object)
        ? ((entity as { properties: unknown }).properties as Record)
        : {};
    for (const k of keyList) {
      const v = propsObj[k];
      const t = jsTypeOf(v);
      const set = seen.get(k) ?? new Set<string>();
      set.add(t);
      seen.set(k, set);
      if (typeof v === 'string') {
        const vs = stringValues.get(k) ?? new Set<string>();
        if (vs.size <= VALUE_SAMPLE_THRESHOLD) vs.add(v);
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
    const out: PropertyKey = { name, types: [...types], nullable: true };
    const vs = stringValues.get(name);
    if (vs && vs.size > 0 && vs.size <= VALUE_SAMPLE_THRESHOLD) {
      out.sampleValues = [...vs].sort();
    } else if (types.has('STRING')) {
      // High-cardinality string field: emit a couple of *truncated* snippets so
      // the LLM understands the field carries free-form text. Without this it
      // cannot ground questions about page bodies / descriptions.
      const snippets = (stringFirstSeen.get(name) ?? [])
        .slice(0, TEXT_SNIPPET_COUNT)
        .map((s) => (s.length > TEXT_SNIPPET_MAX ? s.slice(0, TEXT_SNIPPET_MAX - 1) + '…' : s));
      if (snippets.length > 0) out.sampleValues = snippets;
    }
    return out;
  });
}

async function sampleRelationshipCombos(
  graph: QueryClient,
  rel: string
): Promise<Array<{ src: string; tgt: string }>> {
  const res = await graph.roQuery<Record>(
    `MATCH (a)-[:\`${rel}\`]->(b) RETURN DISTINCT labels(a) AS srcLabels, labels(b) AS tgtLabels LIMIT 25`
  );
  const out: Array<{ src: string; tgt: string }> = [];
  for (const row of res.data ?? []) {
    const srcLabels = row.srcLabels;
    const tgtLabels = row.tgtLabels;
    const src =
      Array.isArray(srcLabels) && typeof srcLabels[0] === 'string' ? srcLabels[0] : 'Unknown';
    const tgt =
      Array.isArray(tgtLabels) && typeof tgtLabels[0] === 'string' ? tgtLabels[0] : 'Unknown';
    out.push({ src, tgt });
  }
  return out;
}

function jsTypeOf(v: unknown): string {
  if (v === null || v === undefined) return 'NULL';
  if (Array.isArray(v)) return 'LIST';
  const t = typeof v;
  if (t === 'number') return Number.isInteger(v) ? 'INTEGER' : 'FLOAT';
  if (t === 'boolean') return 'BOOLEAN';
  if (t === 'string') return 'STRING';
  return 'ANY';
}
