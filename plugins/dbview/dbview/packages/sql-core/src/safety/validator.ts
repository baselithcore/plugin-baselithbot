import sqlParser from 'node-sql-parser';
import { UnsafeSqlError, type SafetyWarning, type SchemaGraph } from '@dbview/shared';

const { Parser } = sqlParser;
import {
  DML_STATEMENT_TYPES,
  FORBIDDEN_STATEMENT_TYPES,
  PARSER_DIALECT,
  type SafetyOptions,
} from './rules.js';

export interface ValidationResult {
  sql: string; // possibly rewritten (limit injected)
  warnings: SafetyWarning[];
  involvedTables: string[];
}

export class SqlSafetyValidator {
  private readonly parser = new Parser();

  validate(rawSql: string, opts: SafetyOptions): ValidationResult {
    const sql = stripComments(rawSql)
      .trim()
      .replace(/;+\s*$/, '');
    if (!sql) throw new UnsafeSqlError('Empty SQL after stripping comments.');
    if (sql.includes(';')) {
      throw new UnsafeSqlError('Multiple statements not allowed.');
    }

    let ast;
    try {
      ast = this.parser.astify(sql, { database: PARSER_DIALECT[opts.dialect] });
    } catch (err) {
      throw new UnsafeSqlError(formatParseError(err as Error, sql));
    }

    const node = Array.isArray(ast) ? ast[0] : ast;
    if (!node || typeof node !== 'object' || !('type' in node)) {
      throw new UnsafeSqlError('Unrecognized SQL AST.');
    }
    const type = String((node as { type: string }).type).toLowerCase();

    if ((FORBIDDEN_STATEMENT_TYPES as readonly string[]).includes(type)) {
      throw new UnsafeSqlError(`DDL/admin statement '${type.toUpperCase()}' is forbidden.`);
    }

    const warnings: SafetyWarning[] = [];
    const isDml = (DML_STATEMENT_TYPES as readonly string[]).includes(type);

    if (isDml && !opts.allowDml) {
      throw new UnsafeSqlError(
        `DML statement '${type.toUpperCase()}' blocked. Set allowDml=true to permit.`,
      );
    }

    if (type !== 'select' && !isDml) {
      throw new UnsafeSqlError(`Statement type '${type}' not allowed.`);
    }

    if (type === 'select' && hasStarColumn(node)) {
      throw new UnsafeSqlError('SELECT * is forbidden. Enumerate explicit columns.');
    }

    const cteNames = collectCteNames(node);
    const involved = collectTables(node).filter((t) => !cteNames.has(t));

    for (const t of involved) {
      if (!opts.knownTables.has(t) && !opts.knownTables.has(stripSchema(t))) {
        warnings.push({
          code: 'unknown_table',
          severity: 'error',
          message: `Table '${t}' not in schema.`,
        });
      }
    }

    // Column-existence check. Catches LLM hallucinations before the query
    // reaches the database. Best-effort: resolves table aliases from FROM/JOIN,
    // skips CTE references and SELECT-list aliases, and ignores fully-qualified
    // bareword references (which the parser already rejects on its own).
    //
    // For wrong-alias hallucinations (`il.InvoiceDate` when `il`=InvoiceLine and
    // InvoiceDate lives on Invoice aliased `i` in the same query), we attempt a
    // deterministic auto-rewrite: if the column exists on exactly one OTHER
    // table referenced by the query, we substitute the right alias. This avoids
    // an extra LLM round-trip when the fix is unambiguous.
    let workingSql = sql;
    if (involved.length > 0 && opts.knownColumns.size > 0) {
      const aliasMap = buildAliasMap(node, opts.knownTables, opts.knownColumns, cteNames);
      const selectAliases = collectSelectAliases(node);
      const involvedColSets = involved
        .map((t) => resolveColumnSet(t, opts.knownColumns))
        .filter((s): s is Set<string> => s !== null);
      // Index in-scope aliases by the bare column names they own. Used by the
      // unique-alternative auto-rewriter below.
      const aliasOwnersForColumn = buildAliasOwnerIndex(aliasMap);
      for (const ref of collectColumnRefs(node)) {
        if (ref.column === '*') continue;
        if (!ref.table && selectAliases.has(ref.column.toLowerCase())) continue;
        if (ref.table && cteNames.has(ref.table)) continue;
        const colSets = ref.table ? aliasMap.get(ref.table.toLowerCase()) : involvedColSets;
        const resolvable = !!colSets && colSets.length > 0;
        const found = resolvable && colSets!.some((s) => setHasCaseInsensitive(s, ref.column));
        if (found) continue;

        // Auto-rewrite when an unambiguous fix is available:
        //   - hallucinated alias (`il.X` where `il` is not in FROM/JOIN), OR
        //   - real alias on a table that doesn't own X,
        // AND the column X is owned by exactly ONE other in-scope alias.
        if (ref.table) {
          const wrongAlias = ref.table;
          const owners = aliasOwnersForColumn.get(ref.column.toLowerCase());
          const candidates = owners?.filter((a) => a !== wrongAlias.toLowerCase()) ?? [];
          if (candidates.length === 1) {
            const correctAlias = candidates[0] as string;
            const rewritten = rewriteAliasInSql(workingSql, wrongAlias, ref.column, correctAlias);
            if (rewritten !== workingSql) {
              workingSql = rewritten;
              warnings.push({
                code: 'unknown_column',
                severity: 'info',
                message: `Rewrote '${wrongAlias}.${ref.column}' → '${correctAlias}.${ref.column}' (column lives on the other in-scope table).`,
              });
              continue;
            }
          }
        }

        // Could not resolve scope and no unique fix → don't false-positive on
        // unrelated identifiers (subquery columns, function args from
        // dialect-specific extensions, etc).
        if (!resolvable) continue;

        const qualified = ref.table ? `${ref.table}.${ref.column}` : ref.column;
        warnings.push({
          code: 'unknown_column',
          severity: 'error',
          message: `Column '${qualified}' not in schema.`,
        });
      }
    }

    if (warnings.some((w) => w.severity === 'error')) {
      throw new UnsafeSqlError(
        warnings
          .filter((w) => w.severity === 'error')
          .map((w) => w.message)
          .join('; '),
      );
    }

    let outSql = workingSql;
    // Belt-and-suspenders: AST traversal handles compound queries, but a
    // textual check on the raw SQL guards against any AST quirk (parser
    // version, future edge cases) emitting a double `LIMIT N LIMIT N`.
    const hasLiteralLimit = /\bLIMIT\s+\d+\b/i.test(workingSql);
    if (type === 'select' && !hasLimit(node) && !hasLiteralLimit) {
      if (opts.dialect === 'mssql') {
        if (!/\bTOP\s+\d+\b/i.test(workingSql) && !/\bFETCH\s+NEXT\b/i.test(workingSql)) {
          outSql = `${workingSql} OFFSET 0 ROWS FETCH NEXT ${opts.rowLimit} ROWS ONLY`;
          warnings.push({
            code: 'missing_limit',
            severity: 'info',
            message: `Auto-injected FETCH NEXT ${opts.rowLimit} ROWS ONLY.`,
          });
        }
      } else if (opts.dialect === 'oracle') {
        if (!/\bFETCH\s+(FIRST|NEXT)\b/i.test(workingSql) && !/\bROWNUM\b/i.test(workingSql)) {
          outSql = `${workingSql} FETCH FIRST ${opts.rowLimit} ROWS ONLY`;
          warnings.push({
            code: 'missing_limit',
            severity: 'info',
            message: `Auto-injected FETCH FIRST ${opts.rowLimit} ROWS ONLY.`,
          });
        }
      } else {
        outSql = `${workingSql} LIMIT ${opts.rowLimit}`;
        warnings.push({
          code: 'missing_limit',
          severity: 'info',
          message: `Auto-injected LIMIT ${opts.rowLimit}.`,
        });
      }
    }

    return { sql: outSql, warnings, involvedTables: involved };
  }
}

/**
 * Trim node-sql-parser's verbose pegjs error to something a UI can show.
 *
 * Raw form: "Expected "!=", "#", ... or end of input but "." found.\nSee Line:1, Column:42 for parse error."
 * The "Expected …" laundry list is hundreds of tokens — useless to a user.
 * We extract the unexpected token + line/column instead.
 */
function formatParseError(err: Error, sql: string): string {
  const raw = err.message ?? String(err);
  const foundMatch = raw.match(/but\s+("(?:\\.|[^"])*"|'(?:[^']|\\')*'|[^\s]+)\s+found/i);
  const lineColMatch = raw.match(/Line[:\s]+(\d+)\s*,\s*[Cc]olumn[:\s]+(\d+)/);
  const found =
    foundMatch && typeof foundMatch[1] === 'string'
      ? foundMatch[1].replace(/^["']|["']$/g, '')
      : 'unexpected token';
  const where = lineColMatch ? ` near line ${lineColMatch[1]}:${lineColMatch[2]}` : '';
  let snippet = '';
  if (lineColMatch) {
    const col = Number(lineColMatch[2]);
    const start = Math.max(0, col - 20);
    const end = Math.min(sql.length, col + 20);
    snippet = ` (…${sql.slice(start, end).replace(/\s+/g, ' ').trim()}…)`;
  }
  return `SQL parse error: unexpected '${found}'${where}${snippet}`;
}

function stripComments(sql: string): string {
  return sql.replace(/--[^\n]*\n/g, '\n').replace(/\/\*[\s\S]*?\*\//g, ' ');
}

function hasStarColumn(node: unknown): boolean {
  let found = false;
  walk(node, (n) => {
    if (
      n &&
      typeof n === 'object' &&
      'columns' in n &&
      (n as { columns: unknown }).columns === '*'
    ) {
      found = true;
    }
    if (
      n &&
      typeof n === 'object' &&
      'expr' in n &&
      typeof (n as { expr: unknown }).expr === 'object'
    ) {
      const expr = (n as { expr: { type?: string; column?: string } }).expr;
      if (expr && expr.type === 'column_ref' && expr.column === '*') found = true;
    }
  });
  return found;
}

function hasLimit(node: unknown): boolean {
  // Walk the entire AST: node-sql-parser attaches `limit` to the outer SELECT
  // for simple queries but to inner branches for compound (UNION/INTERSECT/
  // EXCEPT) queries. A surface-only check would miss the latter and cause a
  // double `LIMIT N LIMIT N` injection in the rewritten SQL.
  let found = false;
  walk(node, (n) => {
    if (!n || typeof n !== 'object') return;
    const lim = (n as { limit?: { value?: unknown[] } | null }).limit;
    if (lim && Array.isArray(lim.value) && lim.value.length > 0) {
      found = true;
    }
  });
  return found;
}

function collectCteNames(node: unknown): Set<string> {
  const out = new Set<string>();
  if (!node || typeof node !== 'object') return out;
  const withClause = (node as { with?: unknown }).with;
  if (!Array.isArray(withClause)) return out;
  for (const cte of withClause) {
    if (cte && typeof cte === 'object') {
      const n = (cte as { name?: { value?: string } | string }).name;
      const name = typeof n === 'string' ? n : n?.value;
      if (name) out.add(name);
    }
  }
  return out;
}

function collectTables(node: unknown): string[] {
  const out = new Set<string>();
  walk(node, (n) => {
    if (!n || typeof n !== 'object') return;
    const obj = n as Record<string, unknown>;
    // Skip column references: they have `table` (alias) AND `column`.
    if ('column' in obj) return;
    // Real FROM/JOIN node: has `table` and typically `as` or `db` siblings.
    if (typeof obj.table === 'string') {
      const id = typeof obj.db === 'string' && obj.db ? `${obj.db}.${obj.table}` : obj.table;
      out.add(id);
    }
  });
  return [...out];
}

function stripSchema(id: string): string {
  const idx = id.indexOf('.');
  return idx >= 0 ? id.slice(idx + 1) : id;
}

function resolveColumnSet(
  tableRef: string,
  knownColumns: Map<string, Set<string>>,
): Set<string> | null {
  if (knownColumns.has(tableRef)) return knownColumns.get(tableRef) ?? null;
  // The known map is keyed by `schema.table` ids; lookup by bare name too.
  for (const [id, cols] of knownColumns) {
    if (id === tableRef || stripSchema(id) === tableRef) return cols;
  }
  return null;
}

/**
 * Map every FROM/JOIN scope identifier (alias or bare table name) to the set
 * of column names of the underlying table. Subquery `(SELECT …) AS x` and CTE
 * references resolve to an empty array (caller treats that as "skip check").
 */
function buildAliasMap(
  node: unknown,
  knownTables: Set<string>,
  knownColumns: Map<string, Set<string>>,
  cteNames: Set<string>,
): Map<string, Set<string>[]> {
  const out = new Map<string, Set<string>[]>();
  walk(node, (n) => {
    if (!n || typeof n !== 'object') return;
    const obj = n as Record<string, unknown>;
    if ('column' in obj) return; // column_ref, not a FROM entry
    const table = typeof obj.table === 'string' ? obj.table : null;
    if (!table) return;
    if (cteNames.has(table)) {
      // Reference to a CTE: allow any column under that scope.
      const alias = pickAlias(obj) ?? table;
      out.set(alias.toLowerCase(), []);
      return;
    }
    const tableId = typeof obj.db === 'string' && obj.db ? `${obj.db}.${table}` : table;
    if (!knownTables.has(tableId) && !knownTables.has(stripSchema(tableId))) return;
    const cols = resolveColumnSet(tableId, knownColumns);
    if (!cols) return;
    const alias = pickAlias(obj);
    const aliasKey = (alias ?? table).toLowerCase();
    const existing = out.get(aliasKey) ?? [];
    existing.push(cols);
    out.set(aliasKey, existing);
    // Also expose the bare table name (handy when SELECT-list uses `tbl.col`
    // without aliasing in the FROM clause).
    if (alias) {
      const bare = table.toLowerCase();
      const arr = out.get(bare) ?? [];
      arr.push(cols);
      out.set(bare, arr);
    }
  });
  return out;
}

function pickAlias(obj: Record<string, unknown>): string | null {
  const as = obj.as;
  if (typeof as === 'string' && as) return as;
  if (as && typeof as === 'object' && 'value' in (as as Record<string, unknown>)) {
    const v = (as as { value?: unknown }).value;
    if (typeof v === 'string' && v) return v;
  }
  return null;
}

function collectSelectAliases(node: unknown): Set<string> {
  const out = new Set<string>();
  walk(node, (n) => {
    if (!n || typeof n !== 'object') return;
    const obj = n as Record<string, unknown>;
    if (!('expr' in obj) || !('as' in obj)) return;
    const alias = obj.as;
    if (typeof alias === 'string' && alias) out.add(alias.toLowerCase());
  });
  return out;
}

interface ColumnRef {
  table: string | null;
  column: string;
}

function collectColumnRefs(node: unknown): ColumnRef[] {
  const out: ColumnRef[] = [];
  walk(node, (n) => {
    if (!n || typeof n !== 'object') return;
    const obj = n as { type?: unknown; table?: unknown; column?: unknown };
    if (obj.type !== 'column_ref') return;
    const column = extractColumnName(obj.column);
    if (!column) return;
    const table = typeof obj.table === 'string' ? obj.table : null;
    out.push({ table, column });
  });
  return out;
}

/**
 * Normalize the many shapes node-sql-parser emits for `column`:
 *   - bare string ("foo")
 *   - `{ expr: { value: "foo" } }` (current shape on postgresql dialect)
 *   - `{ value: "foo" }` (some other dialects)
 */
function extractColumnName(column: unknown): string | null {
  if (typeof column === 'string') return column;
  if (!column || typeof column !== 'object') return null;
  const obj = column as { expr?: { value?: unknown }; value?: unknown };
  if (obj.expr && typeof obj.expr.value === 'string') return obj.expr.value;
  if (typeof obj.value === 'string') return obj.value;
  return null;
}

function setHasCaseInsensitive(set: Set<string>, value: string): boolean {
  if (set.has(value)) return true;
  const lower = value.toLowerCase();
  for (const v of set) {
    if (v.toLowerCase() === lower) return true;
  }
  return false;
}

/**
 * For each bare column name, list the DISTINCT in-scope tables (by cols-set
 * identity) that own it, with one preferred alias per table. The preferred
 * alias is the explicit FROM/JOIN alias when present, otherwise the bare table
 * name. Used to detect when a hallucinated `aliasA.col` can be unambiguously
 * rewritten to a real `aliasB.col` because exactly one in-scope table has `col`.
 */
function buildAliasOwnerIndex(aliasMap: Map<string, Set<string>[]>): Map<string, string[]> {
  // Identify unique tables by cols-set reference, remember preferred alias.
  const tablePreferredAlias = new Map<Set<string>, string>();
  for (const [alias, colSets] of aliasMap) {
    for (const cols of colSets) {
      const existing = tablePreferredAlias.get(cols);
      // Prefer the SHORTEST alias (explicit aliases like `o` win over bare `orders`).
      if (!existing || alias.length < existing.length) {
        tablePreferredAlias.set(cols, alias);
      }
    }
  }
  // Now build column → distinct-table list using preferred aliases.
  const out = new Map<string, string[]>();
  for (const [cols, preferredAlias] of tablePreferredAlias) {
    for (const c of cols) {
      const lower = c.toLowerCase();
      const arr = out.get(lower) ?? [];
      if (!arr.includes(preferredAlias)) arr.push(preferredAlias);
      out.set(lower, arr);
    }
  }
  return out;
}

/**
 * Rewrite every `<wrongAlias>.<column>` occurrence to `<rightAlias>.<column>`
 * in the SQL string. The alias is matched on a word boundary so we don't
 * mangle longer identifiers (e.g. `myil.foo` is left alone). Case-insensitive
 * on the alias (SQL aliases are case-insensitive in every supported dialect).
 */
function rewriteAliasInSql(
  sql: string,
  wrongAlias: string,
  column: string,
  rightAlias: string,
): string {
  const escAlias = escapeRegex(wrongAlias);
  const escCol = escapeRegex(column);
  const re = new RegExp(`\\b${escAlias}\\.(${escCol})\\b`, 'gi');
  return sql.replace(re, `${rightAlias}.$1`);
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function walk(node: unknown, visit: (n: unknown) => void): void {
  if (!node || typeof node !== 'object') return;
  visit(node);
  for (const v of Object.values(node as Record<string, unknown>)) {
    if (Array.isArray(v)) v.forEach((x) => walk(x, visit));
    else if (v && typeof v === 'object') walk(v, visit);
  }
}

export interface KnownSets {
  knownTables: Set<string>;
  knownColumns: Map<string, Set<string>>;
}

export function buildKnownSets(graph: SchemaGraph): KnownSets {
  const knownTables = new Set<string>();
  const knownColumns = new Map<string, Set<string>>();
  for (const t of graph.tables) {
    knownTables.add(t.id);
    knownTables.add(t.name);
    knownColumns.set(t.id, new Set(t.columns.map((c) => c.name)));
  }
  return { knownTables, knownColumns };
}

/**
 * Memoized variant — caches the computed sets per graph identity. Safe because
 * `SchemaService` reuses the same `SchemaGraph` reference for the lifetime of
 * a cache entry. When the schema cache replaces the graph, the old reference
 * becomes unreachable and the WeakMap entry is collected automatically.
 *
 * Use this from hot paths (validator call sites in QueryService / Nl2SqlService)
 * to avoid re-walking O(tables × columns) on every request.
 */
const knownSetsCache = new WeakMap<SchemaGraph, KnownSets>();

export function buildKnownSetsMemoized(graph: SchemaGraph): KnownSets {
  let entry = knownSetsCache.get(graph);
  if (!entry) {
    entry = buildKnownSets(graph);
    knownSetsCache.set(graph, entry);
  }
  return entry;
}
