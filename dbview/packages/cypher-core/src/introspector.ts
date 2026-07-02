import neo4j from 'neo4j-driver';
import type { Driver } from 'neo4j-driver';
import {
  IntrospectionError,
  type NodeLabel,
  type PropertyGraphSchema,
  type PropertyKey,
  type RelationshipType,
} from '@dbview/shared';

export class Neo4jIntrospector {
  private readonly driver: Driver;

  constructor(connectionString: string) {
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

  async introspect(): Promise<PropertyGraphSchema> {
    const session = this.driver.session({ defaultAccessMode: neo4j.session.READ });
    try {
      const labels = await this.collectLabels(session);
      const relationships = await this.collectRelationships(session);

      for (const lbl of labels) {
        await this.attachLabelSamples(session, lbl);
      }
      const sampledRelTypes = new Set<string>();
      for (const rel of relationships) {
        if (sampledRelTypes.has(rel.type)) continue;
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
    } catch (err) {
      throw new IntrospectionError(`Neo4j introspection failed: ${(err as Error).message}`);
    } finally {
      await session.close();
    }
  }

  private async attachLabelSamples(
    session: ReturnType<Driver['session']>,
    label: NodeLabel
  ): Promise<void> {
    const stringProps = label.properties.filter((p) => p.types.some((t) => /string/i.test(t)));
    if (stringProps.length === 0) return;
    const res = await session.run(
      `MATCH (n:\`${label.label}\`) WITH n LIMIT 500
       UNWIND $props AS k
       WITH k, n[k] AS v
       WHERE v IS NOT NULL AND toString(v) = v
       WITH k, collect(DISTINCT v) AS vals
       RETURN k, vals`,
      { props: stringProps.map((p) => p.name) }
    );
    applySamples(res.records, label.properties);
  }

  private async attachRelSamples(
    session: ReturnType<Driver['session']>,
    relType: string,
    rels: RelationshipType[]
  ): Promise<void> {
    const sampleProps = rels.find((r) => r.type === relType)?.properties ?? [];
    const stringProps = sampleProps.filter((p) => p.types.some((t) => /string/i.test(t)));
    if (stringProps.length === 0) return;
    const res = await session.run(
      `MATCH ()-[r:\`${relType}\`]->() WITH r LIMIT 500
       UNWIND $props AS k
       WITH k, r[k] AS v
       WHERE v IS NOT NULL AND toString(v) = v
       WITH k, collect(DISTINCT v) AS vals
       RETURN k, vals`,
      { props: stringProps.map((p) => p.name) }
    );
    for (const rel of rels.filter((r) => r.type === relType)) {
      applySamples(res.records, rel.properties);
    }
  }

  private async collectLabels(session: ReturnType<Driver['session']>): Promise<NodeLabel[]> {
    const propsRes = await session.run(`
      CALL db.schema.nodeTypeProperties()
      YIELD nodeType, propertyName, propertyTypes, mandatory
      RETURN nodeType, collect({
        name: propertyName,
        types: propertyTypes,
        mandatory: mandatory
      }) AS properties
    `);

    const labelMap = new Map<string, NodeLabel>();
    for (const rec of propsRes.records) {
      const nodeType = rec.get('nodeType') as string; // ":`Label`" or ":`L1`:`L2`"
      const props = rec.get('properties') as Array<{
        name: string | null;
        types: string[] | null;
        mandatory: boolean | null;
      }>;
      const labels = parseNodeType(nodeType);
      for (const label of labels) {
        const properties: PropertyKey[] = props
          .filter((p) => p.name)
          .map((p) => ({
            name: p.name as string,
            types: p.types ?? ['ANY'],
            nullable: p.mandatory !== true,
          }));
        const existing = labelMap.get(label);
        if (existing) {
          mergeProperties(existing.properties, properties);
        } else {
          labelMap.set(label, { id: label, label, properties });
        }
      }
    }

    return [...labelMap.values()];
  }

  private async collectRelationships(
    session: ReturnType<Driver['session']>
  ): Promise<RelationshipType[]> {
    const propsRes = await session.run(`
      CALL db.schema.relTypeProperties()
      YIELD relType, propertyName, propertyTypes, mandatory
      RETURN relType, collect({
        name: propertyName,
        types: propertyTypes,
        mandatory: mandatory
      }) AS properties
    `);
    const propsByType = new Map<string, PropertyKey[]>();
    for (const rec of propsRes.records) {
      const relType = stripBackticks(rec.get('relType') as string);
      const props = rec.get('properties') as Array<{
        name: string | null;
        types: string[] | null;
        mandatory: boolean | null;
      }>;
      propsByType.set(
        relType,
        props
          .filter((p) => p.name)
          .map((p) => ({
            name: p.name as string,
            types: p.types ?? ['ANY'],
            nullable: p.mandatory !== true,
          }))
      );
    }

    const combinationsRes = await session.run(`
      MATCH (a)-[r]->(b)
      RETURN DISTINCT labels(a) AS srcLabels, type(r) AS relType, labels(b) AS tgtLabels
    `);

    const out: RelationshipType[] = [];
    let idx = 0;
    for (const rec of combinationsRes.records) {
      const srcLabels = (rec.get('srcLabels') as string[]) ?? [];
      const tgtLabels = (rec.get('tgtLabels') as string[]) ?? [];
      const relType = rec.get('relType') as string;
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

  async close(): Promise<void> {
    await this.driver.close();
  }
}

function parseNodeType(s: string): string[] {
  // Format: ":`Label1`:`Label2`"
  const matches = s.match(/`([^`]+)`/g) ?? [];
  return matches.map((m) => m.slice(1, -1));
}

function stripBackticks(s: string): string {
  const m = s.match(/`([^`]+)`/);
  return m?.[1] ?? s;
}

function mergeProperties(existing: PropertyKey[], incoming: PropertyKey[]): void {
  const seen = new Set(existing.map((p) => p.name));
  for (const p of incoming) {
    if (!seen.has(p.name)) {
      existing.push(p);
      seen.add(p.name);
    }
  }
}

const VALUE_SAMPLE_THRESHOLD = 10;

function applySamples(records: Array<{ get(key: string): unknown }>, props: PropertyKey[]): void {
  const byKey = new Map<string, PropertyKey>();
  for (const p of props) byKey.set(p.name, p);
  for (const rec of records) {
    const k = rec.get('k') as string;
    const vals = rec.get('vals') as unknown[];
    if (!Array.isArray(vals)) continue;
    const distinct = vals.filter((v): v is string => typeof v === 'string');
    if (distinct.length === 0 || distinct.length > VALUE_SAMPLE_THRESHOLD) continue;
    const target = byKey.get(k);
    if (target) target.sampleValues = [...new Set(distinct)].sort();
  }
}
