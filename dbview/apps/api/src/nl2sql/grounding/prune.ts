import type { SchemaGraph, TableNode } from '@dbview/shared';

export interface PruneOptions {
  /** Skip pruning entirely when the schema has at most this many tables. */
  threshold: number;
  /** Maximum number of tables to keep AFTER 1-hop FK closure. */
  maxTables: number;
}

export interface PruneResult {
  /** Pruned schema (or the original when pruning was skipped). */
  graph: SchemaGraph;
  /** True when the returned graph is a strict subset of the input. */
  pruned: boolean;
  /** Table ids removed from the input. Empty when `pruned` is false. */
  removed: string[];
  /** Tokens extracted from the prompt that drove the scoring. */
  matchedTokens: string[];
}

/**
 * Wide schemas (Salesforce Data Cloud, large datalakes) inflate the system
 * prompt past 30KB and dilute the model's attention so much that the LLM
 * picks the wrong table or invents columns. Reduce the schema to the tables
 * actually relevant to the user's question via keyword overlap, then add the
 * 1-hop FK closure so joins remain expressible.
 *
 * The function is intentionally conservative: when no token matches anything
 * (e.g. fully abstract questions like "list everything"), it returns the input
 * unchanged. Callers must treat this as best-effort and keep the full graph
 * available as a fallback for the retry loop.
 */
export function pruneRelationalSchema(
  graph: SchemaGraph,
  prompt: string,
  opts: PruneOptions,
): PruneResult {
  if (graph.tables.length <= opts.threshold) {
    return { graph, pruned: false, removed: [], matchedTokens: [] };
  }
  const tokens = tokenize(prompt);
  if (tokens.length === 0) {
    return { graph, pruned: false, removed: [], matchedTokens: [] };
  }

  const scores = new Map<string, number>();
  for (const table of graph.tables) {
    const score = scoreTable(table, tokens);
    if (score > 0) scores.set(table.id, score);
  }
  if (scores.size === 0) {
    return { graph, pruned: false, removed: [], matchedTokens: tokens };
  }

  // Pick top-K seed tables by score.
  const seeds = [...scores.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, opts.maxTables)
    .map(([id]) => id);
  const keep = new Set<string>(seeds);

  // 1-hop FK closure: pull in any table directly connected to a seed so the
  // model can still express joins. Closure does NOT recurse — n-hop expansion
  // re-inflates the prompt and defeats the point.
  for (const edge of graph.edges) {
    if (keep.has(edge.source)) keep.add(edge.target);
    if (keep.has(edge.target)) keep.add(edge.source);
  }

  // If FK closure exploded the set past maxTables, drop the lowest-scoring
  // closure additions (never drop seeds — they are the explicit matches).
  if (keep.size > opts.maxTables) {
    const seedSet = new Set(seeds);
    const closureExtras = [...keep]
      .filter((id) => !seedSet.has(id))
      .map((id) => ({ id, score: scores.get(id) ?? 0 }))
      .sort((a, b) => b.score - a.score);
    const allowedExtras = Math.max(0, opts.maxTables - seeds.length);
    const trimmed = new Set(seeds);
    for (const extra of closureExtras.slice(0, allowedExtras)) trimmed.add(extra.id);
    keep.clear();
    for (const id of trimmed) keep.add(id);
  }

  const tables = graph.tables.filter((t) => keep.has(t.id));
  const edges = graph.edges.filter((e) => keep.has(e.source) && keep.has(e.target));
  const removed = graph.tables.filter((t) => !keep.has(t.id)).map((t) => t.id);

  return {
    graph: { ...graph, tables, edges },
    pruned: true,
    removed,
    matchedTokens: tokens,
  };
}

/**
 * Lowercased content tokens (≥3 chars) extracted from the prompt with common
 * English + Italian stopwords removed. Quoted literals and numbers are kept
 * as raw tokens so a question like `WHERE name = "Acme"` still scores tables
 * with an `acme` column or description.
 */
export function tokenize(prompt: string): string[] {
  const lowered = prompt.toLowerCase();
  const raw = lowered.split(/[^a-z0-9_]+/u).filter(Boolean);
  const out: string[] = [];
  const seen = new Set<string>();
  for (const tok of raw) {
    if (tok.length < 3) continue;
    if (STOPWORDS.has(tok)) continue;
    if (seen.has(tok)) continue;
    seen.add(tok);
    out.push(tok);
  }
  return out;
}

function scoreTable(table: TableNode, tokens: string[]): number {
  const tableName = table.name.toLowerCase();
  const tableNameParts = splitIdentifier(tableName);
  const displayParts = table.displayName ? splitIdentifier(table.displayName.toLowerCase()) : [];
  const descParts = table.description ? splitIdentifier(table.description.toLowerCase()) : [];

  let score = 0;
  for (const tok of tokens) {
    // Exact matches against the entity name and its display label dominate.
    if (tableName === tok) score += 8;
    if (tableNameParts.includes(tok)) score += 5;
    if (displayParts.includes(tok)) score += 4;
    if (descParts.includes(tok)) score += 2;
    // Substring fallback so plurals / partial morphemes still count.
    if (tableName.includes(tok) || tok.includes(tableName)) score += 2;

    for (const col of table.columns) {
      const colName = col.name.toLowerCase();
      const colParts = splitIdentifier(colName);
      if (colName === tok) score += 3;
      else if (colParts.includes(tok)) score += 2;
      if (col.displayName) {
        const dn = col.displayName.toLowerCase();
        if (splitIdentifier(dn).includes(tok)) score += 2;
      }
      if (col.description && col.description.toLowerCase().includes(tok)) score += 1;
    }
  }
  return score;
}

function splitIdentifier(s: string): string[] {
  return s.split(/[^a-z0-9]+/u).filter((p) => p.length >= 2);
}

const STOPWORDS = new Set<string>([
  // English
  'the',
  'and',
  'for',
  'with',
  'from',
  'into',
  'over',
  'under',
  'about',
  'show',
  'list',
  'find',
  'give',
  'tell',
  'what',
  'which',
  'when',
  'where',
  'who',
  'how',
  'top',
  'bottom',
  'first',
  'last',
  'all',
  'any',
  'some',
  'each',
  'every',
  'none',
  'most',
  'least',
  'best',
  'worst',
  'sum',
  'avg',
  'min',
  'max',
  'count',
  'total',
  'average',
  'median',
  'group',
  'order',
  'sort',
  'rank',
  'select',
  'where',
  'between',
  'than',
  'less',
  'more',
  'much',
  'many',
  'few',
  'data',
  'value',
  'values',
  'record',
  'records',
  'row',
  'rows',
  'item',
  'items',
  'thing',
  'things',
  'have',
  'has',
  'had',
  'are',
  'was',
  'were',
  'been',
  'being',
  'this',
  'that',
  'these',
  'those',
  'will',
  'would',
  'could',
  'should',
  'can',
  'may',
  'might',
  // Italian
  'che',
  'con',
  'per',
  'sul',
  'sui',
  'sui',
  'tra',
  'fra',
  'una',
  'uno',
  'gli',
  'come',
  'cosa',
  'quale',
  'quali',
  'quando',
  'dove',
  'chi',
  'tutti',
  'tutte',
  'tutto',
  'tutta',
  'sono',
  'sono',
  'era',
  'erano',
  'essere',
  'avere',
  'fare',
  'mostra',
  'mostrami',
  'elenca',
  'lista',
  'trova',
  'dammi',
  'voglio',
  'vorrei',
  'primi',
  'prime',
  'ultimo',
  'ultima',
  'ultimi',
  'ultime',
  'maggior',
  'minor',
  'media',
  'somma',
  'totale',
  'massimo',
  'minimo',
  'numero',
  'valore',
  'valori',
  'dato',
  'dati',
  'riga',
  'righe',
  'questo',
  'questa',
  'questi',
  'queste',
  'quello',
  'quella',
  'quelli',
  'quelle',
  'più',
  'meno',
  'nel',
  'nei',
  'nella',
  'nelle',
  'del',
  'dei',
  'degli',
  'della',
  'delle',
  'alla',
  'allo',
  'agli',
  'alle',
  'ogni',
  'qualche',
  'nessun',
  'nessuna',
  'molto',
  'molti',
  'poco',
  'pochi',
  'tanti',
  'tante',
  'principali',
  'principale',
  'tipo',
  'tipi',
]);
