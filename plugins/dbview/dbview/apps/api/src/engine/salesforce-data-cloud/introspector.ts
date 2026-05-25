import type { Column, FKEdge, SchemaGraph, TableNode } from '@dbview/shared';
import { SalesforceDataCloudClient, type SdcMetadataEntity } from './client.js';

const SCHEMA_LABEL = 'data_cloud';

/**
 * Salesforce Data Cloud schema introspector.
 *
 * Strategy:
 *  - GET `/api/v2/metadata` to list every entity (DMOs, DLOs, CIOs) with fields.
 *  - When the list response omits fields for some entities, fall back to
 *    per-entity describes with bounded concurrency.
 *  - Compute FK edges from declared relationships, derive each column's
 *    `isForeignKey` flag from the union of edge source columns, then build the
 *    relational SchemaGraph.
 */
export class SalesforceDataCloudIntrospector {
  constructor(
    private readonly client: SalesforceDataCloudClient,
    private readonly options: { excludePattern?: RegExp; concurrency?: number } = {}
  ) {}

  async introspect(): Promise<SchemaGraph> {
    const list = await this.client.listEntities();
    const exclude = this.options.excludePattern;
    const entities = (list.metadata ?? []).filter((e) => !exclude || !exclude.test(e.name));

    const missing = entities.filter((e) => !e.fields || e.fields.length === 0);
    if (missing.length > 0) {
      const concurrency = Math.max(1, this.options.concurrency ?? 8);
      const described = await runWithConcurrency(missing, concurrency, (e) =>
        this.client.describeEntity(e.name)
      );
      const byName = new Map(described.map((d) => [d.name, d]));
      for (let i = 0; i < entities.length; i++) {
        const refresh = byName.get(entities[i]!.name);
        if (refresh) entities[i] = refresh;
      }
    }

    const known = new Set(entities.map((e) => e.name));
    const edges = collectEdges(entities, known);
    const fkColumnsByEntity = collectFkColumns(edges);
    const tables: TableNode[] = entities.map((e) =>
      entityToTable(e, fkColumnsByEntity.get(e.name) ?? new Set())
    );

    return {
      kind: 'relational',
      dialect: 'salesforce-data-cloud',
      tables,
      edges,
      generatedAt: new Date().toISOString(),
    };
  }

  async close(): Promise<void> {
    await this.client.close();
  }
}

function entityToTable(e: SdcMetadataEntity, fkColumns: Set<string>): TableNode {
  const pkSet = new Set<string>();
  for (const pk of e.primaryKeys ?? []) {
    if (pk.name) pkSet.add(pk.name);
  }
  for (const f of e.fields ?? []) {
    if (f.isPrimaryKey && f.name) pkSet.add(f.name);
  }

  const columns: Column[] = (e.fields ?? [])
    .filter((f) => !isNoisySystemField(f.name))
    .map((f) => {
      const displayName = cleanDisplayName(f.displayName, f.name);
      return {
        name: f.name,
        dataType: humanType(f.type ?? 'UNKNOWN'),
        nullable: !pkSet.has(f.name),
        isPrimaryKey: pkSet.has(f.name),
        isForeignKey: fkColumns.has(f.name),
        isUnique: pkSet.has(f.name),
        defaultValue: null,
        ...(displayName ? { displayName } : {}),
        ...(f.description ? { description: f.description } : {}),
      } satisfies Column;
    });

  const tableDisplayName = cleanDisplayName(e.displayName, e.name);
  return {
    id: `${SCHEMA_LABEL}.${e.name}`,
    schema: SCHEMA_LABEL,
    name: e.name,
    columns,
    ...(tableDisplayName ? { displayName: tableDisplayName } : {}),
    ...(e.description ? { description: e.description } : {}),
  } satisfies TableNode;
}

/**
 * Drop noisy provenance/system fields that pollute the prompt without adding
 * semantic value (Data Source linkage IDs, internal organization tags, etc.).
 * Real foreign keys to user-visible DMOs are preserved by the relationships
 * branch even when their bearing column matches one of these patterns.
 */
function isNoisySystemField(name: string): boolean {
  return (
    /^KQ_/i.test(name) ||
    /^ssot__DataSource(Object)?Id__c$/i.test(name) ||
    /^ssot__InternalOrganization(Id)?__c$/i.test(name) ||
    /^cdp_sys_/i.test(name)
  );
}

/**
 * Salesforce display names sometimes echo the technical name verbatim (or
 * differ only by separator/case). Treat those as absent so the prompt
 * serializer doesn't emit redundant `Foo — "Foo"` noise.
 */
function cleanDisplayName(display: string | undefined, technical: string): string | undefined {
  if (!display) return undefined;
  const trimmed = display.trim();
  if (!trimmed) return undefined;
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '');
  if (norm(trimmed) === norm(technical)) return undefined;
  return trimmed;
}

function collectEdges(entities: SdcMetadataEntity[], known: Set<string>): FKEdge[] {
  const edges: FKEdge[] = [];
  for (const e of entities) {
    for (const rel of e.relationships ?? []) {
      const from = rel.fromEntity ?? e.name;
      const to = rel.toEntity;
      const fromCol = rel.fromEntityAttribute;
      const toCol = rel.toEntityAttribute;
      if (!from || !to || !fromCol || !toCol) continue;
      if (!known.has(from) || !known.has(to)) continue;
      edges.push({
        id: `${from}.${fromCol}->${to}.${toCol}`,
        source: `${SCHEMA_LABEL}.${from}`,
        sourceColumn: fromCol,
        target: `${SCHEMA_LABEL}.${to}`,
        targetColumn: toCol,
        constraintName: rel.relationshipName ?? undefined,
      });
    }
  }
  return edges;
}

function collectFkColumns(edges: FKEdge[]): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  for (const e of edges) {
    const entityName = e.source.startsWith(`${SCHEMA_LABEL}.`)
      ? e.source.slice(SCHEMA_LABEL.length + 1)
      : e.source;
    let set = out.get(entityName);
    if (!set) {
      set = new Set();
      out.set(entityName, set);
    }
    set.add(e.sourceColumn);
  }
  return out;
}

/**
 * Map SDC API type tokens to short human-readable strings used by the UI and
 * the NL2SQL prompt schema serializer.
 */
function humanType(t: string): string {
  switch (t) {
    case 'STRING_TYPE':
      return 'string';
    case 'NUMBER_TYPE':
      return 'number';
    case 'DATE_TIME_TYPE':
      return 'timestamp';
    case 'DATE_TYPE':
      return 'date';
    case 'BOOLEAN_TYPE':
      return 'boolean';
    case 'PERCENT_TYPE':
      return 'number';
    default:
      return t.toLowerCase().replace(/_type$/, '');
  }
}

async function runWithConcurrency<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T) => Promise<R>
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      const item = items[i] as T;
      out[i] = await fn(item);
    }
  });
  await Promise.all(workers);
  return out;
}
