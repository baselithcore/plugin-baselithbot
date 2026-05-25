import type { UnifiedSchema } from '@dbview/shared';

const FALLBACK_SUGGESTIONS = [
  'Show first 10 rows from the largest table',
  'Count rows per table',
  'List the columns of each table',
];

/**
 * Build prompt suggestions grounded in the actual schema entities.
 *
 * Generic templates risk asking the LLM about tables that don't exist
 * (e.g. "Top customers" against a Car_Database schema). Anchoring suggestions
 * to real names prevents schema-mismatch dead ends in the empty state.
 */
export function buildSuggestions(schema: UnifiedSchema | undefined): string[] {
  if (!schema) return FALLBACK_SUGGESTIONS;
  if (schema.kind === 'relational') return relationalSuggestions(schema);
  if (schema.kind === 'graph') return graphSuggestions(schema);
  if (schema.kind === 'vector') return vectorSuggestions(schema);
  if (schema.kind === 'keyvalue') return keyValueSuggestions(schema);
  if (schema.kind === 'search') return searchSuggestions(schema);
  return documentSuggestions(schema);
}

function documentSuggestions(schema: Extract<UnifiedSchema, { kind: 'document' }>): string[] {
  const c = schema.collections[0];
  if (!c) return FALLBACK_SUGGESTIONS;
  return [
    `Count documents in ${c.name}`,
    `Show 10 documents from ${c.name}`,
    `List the fields of ${c.name}`,
  ];
}

function keyValueSuggestions(schema: Extract<UnifiedSchema, { kind: 'keyvalue' }>): string[] {
  const ns = schema.namespaces[0];
  if (!ns) return FALLBACK_SUGGESTIONS;
  return [
    `SCAN 0 MATCH ${ns.pattern} COUNT 100`,
    `DBSIZE`,
    `TYPE ${ns.sampleKeys[0] ?? ns.pattern.replace(/\*$/, '1')}`,
  ];
}

function searchSuggestions(schema: Extract<UnifiedSchema, { kind: 'search' }>): string[] {
  const idx = schema.indices[0];
  if (!idx) return FALLBACK_SUGGESTIONS;
  return [
    `Count documents in ${idx.name}`,
    `Show 10 documents from ${idx.name}`,
    `List the fields of ${idx.name}`,
  ];
}

function relationalSuggestions(schema: Extract<UnifiedSchema, { kind: 'relational' }>): string[] {
  const tables = [...schema.tables];
  if (tables.length === 0) return FALLBACK_SUGGESTIONS;

  const out: string[] = [];
  const ranked = tables
    .slice()
    .sort((a, b) => (b.rowCountEstimate ?? 0) - (a.rowCountEstimate ?? 0));

  const main = ranked[0];
  if (main) out.push(`Show 10 rows from ${humanize(main.name)}`);

  const dateColumn = findDateColumn(ranked);
  if (dateColumn) {
    out.push(
      `Recent ${humanize(dateColumn.table)} ordered by ${humanize(dateColumn.column)} (last 30 days)`
    );
  }

  const fk = schema.edges[0];
  if (fk) {
    const src = tables.find((t) => t.id === fk.source);
    const tgt = tables.find((t) => t.id === fk.target);
    if (src && tgt) {
      out.push(`Count of ${humanize(src.name)} per ${humanize(tgt.name)}`);
    }
  }

  const numeric = findNumericColumn(ranked);
  if (numeric) {
    out.push(`Top 5 ${humanize(numeric.table)} by ${humanize(numeric.column)}`);
  }

  if (tables.length >= 2 && out.length < 4) {
    const second = ranked[1];
    if (second) out.push(`How many distinct values per column in ${humanize(second.name)}`);
  }

  return dedupe(out).slice(0, 4);
}

function graphSuggestions(schema: Extract<UnifiedSchema, { kind: 'graph' }>): string[] {
  const labels = schema.labels;
  if (labels.length === 0) return FALLBACK_SUGGESTIONS;
  const out = [`Show 10 ${humanize(labels[0]!.label)} nodes`];
  const rel = schema.relationships[0];
  if (rel) {
    out.push(`Find ${humanize(rel.source)} connected via ${humanize(rel.type)}`);
  }
  if (labels[1]) {
    out.push(`Count nodes per label`);
  }
  return out.slice(0, 4);
}

function vectorSuggestions(schema: Extract<UnifiedSchema, { kind: 'vector' }>): string[] {
  const c = schema.collections[0];
  if (!c) return FALLBACK_SUGGESTIONS;
  return [
    `List 10 points from ${c.name}`,
    `Total points in ${c.name}`,
    `Distinct values for the first payload field of ${c.name}`,
  ];
}

interface ColumnRef {
  table: string;
  column: string;
}

function findDateColumn(
  tables: Array<{ name: string; columns: Array<{ name: string; dataType: string }> }>
): ColumnRef | null {
  const dateRe = /(date|timestamp|datetime|time)/i;
  const namedRe = /(_at|_date|_time|created|updated|modified)/i;
  for (const t of tables) {
    const c =
      t.columns.find((c) => namedRe.test(c.name) && dateRe.test(c.dataType)) ??
      t.columns.find((c) => dateRe.test(c.dataType));
    if (c) return { table: t.name, column: c.name };
  }
  return null;
}

function findNumericColumn(
  tables: Array<{ name: string; columns: Array<{ name: string; dataType: string }> }>
): ColumnRef | null {
  const numericRe = /(int|numeric|decimal|float|double|money|real|number)/i;
  const interestingRe = /(price|amount|total|revenue|qty|quantity|score|count|stock|salary)/i;
  for (const t of tables) {
    const interesting = t.columns.find(
      (c) => interestingRe.test(c.name) && numericRe.test(c.dataType)
    );
    if (interesting) return { table: t.name, column: interesting.name };
  }
  for (const t of tables) {
    const c = t.columns.find((c) => numericRe.test(c.dataType) && !/^id$/i.test(c.name));
    if (c) return { table: t.name, column: c.name };
  }
  return null;
}

function humanize(s: string): string {
  return s.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function dedupe(arr: string[]): string[] {
  return [...new Set(arr)];
}
