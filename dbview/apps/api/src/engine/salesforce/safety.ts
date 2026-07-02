import { UnsafeSqlError } from '@dbview/shared';

/**
 * SOQL safety validator. SOQL is SQL-like but distinct enough that
 * node-sql-parser cannot parse it correctly. This validator is regex-based.
 *
 * Rules mirror the SQL safety contract:
 *  1. SELECT only — no INSERT/UPDATE/DELETE/UPSERT/MERGE.
 *  2. Never `SELECT *` — enumerate fields explicitly.
 *  3. Single statement — no `;`.
 *  4. FROM target must reference a known sObject (case-insensitive).
 *  5. Auto-inject LIMIT when missing.
 *  6. Single-identifier field references must exist in the FROM target's
 *     field set when `knownFields` is provided.
 *
 * Errors are thrown as `UnsafeSqlError` (shared with the SQL validator) so the
 * NL2SQL retry loop can treat both engines uniformly.
 */

export interface SoqlSafetyOptions {
  rowLimit: number;
  /** Lowercased known sObject names from introspected schema. */
  knownSObjects: Set<string>;
  /**
   * Map of lowercased sObject name → lowercased field-name set. When provided,
   * the validator rejects single-identifier field references not present in
   * the FROM target's field set. Dotted lookup paths (e.g. `Account.Owner.Name`)
   * are not validated — relationship traversal would require full lookup graph.
   */
  knownFields?: Map<string, Set<string>>;
}

export interface SoqlValidationResult {
  query: string;
}

/** SOQL reserved words + functions that may appear as identifiers in expressions. */
const SOQL_RESERVED = new Set([
  'select',
  'from',
  'where',
  'and',
  'or',
  'not',
  'in',
  'like',
  'null',
  'true',
  'false',
  'group',
  'by',
  'order',
  'having',
  'limit',
  'offset',
  'asc',
  'desc',
  'nulls',
  'first',
  'last',
  'with',
  'all',
  'rows',
  'for',
  'view',
  'reference',
  'update',
  'tracking',
  'viewstat',
  // aggregate / scalar functions
  'count',
  'count_distinct',
  'sum',
  'avg',
  'min',
  'max',
  'distance',
  'geolocation',
  'calendar_month',
  'calendar_quarter',
  'calendar_year',
  'day_in_month',
  'day_in_week',
  'day_in_year',
  'day_only',
  'fiscal_month',
  'fiscal_quarter',
  'fiscal_year',
  'hour_in_day',
  'week_in_month',
  'week_in_year',
  'tolabel',
  'convertcurrency',
  'format',
  // date literals
  'yesterday',
  'today',
  'tomorrow',
  'this_week',
  'last_week',
  'next_week',
  'this_month',
  'last_month',
  'next_month',
  'this_quarter',
  'last_quarter',
  'next_quarter',
  'this_year',
  'last_year',
  'next_year',
  'last_90_days',
  'next_90_days',
]);

/** Date-literal prefixes with parameter form, e.g. `LAST_N_DAYS:30`. */
const SOQL_DATE_LITERAL_PREFIXES =
  /^(?:last|next)_n_(?:days|weeks|months|quarters|years|fiscal_quarters|fiscal_years)$/i;

export class SalesforceSafetyValidator {
  validate(soql: string, opts: SoqlSafetyOptions): SoqlValidationResult {
    const trimmed = soql.trim().replace(/;+\s*$/, '');
    if (!trimmed) throw soqlError('Empty SOQL.', 'empty_query');

    if (trimmed.includes(';')) {
      throw soqlError('Multiple statements are not allowed.', 'multi_statement');
    }

    const stripped = stripStringsAndComments(trimmed);

    if (!/^\s*SELECT\b/i.test(stripped)) {
      throw soqlError('Only SELECT queries are allowed.', 'unsafe_sql');
    }

    if (/\bSELECT\s+\*/i.test(stripped)) {
      throw soqlError('SELECT * is not allowed — enumerate fields.', 'unsafe_sql');
    }

    const banned = ['INSERT', 'UPDATE', 'DELETE', 'UPSERT', 'MERGE', 'CREATE', 'DROP', 'ALTER'];
    for (const kw of banned) {
      if (new RegExp(`\\b${kw}\\b`, 'i').test(stripped)) {
        throw soqlError(`Keyword '${kw}' is not allowed.`, 'unsafe_sql');
      }
    }

    // Strip parenthesized sub-selects: their FROM target is a relationship name
    // (not always equal to a sObject), and their fields belong to a different
    // sObject than the outer query — validating them here would require the
    // child-relationship metadata graph.
    const outerQuery = stripParenGroups(stripped);

    // Find the OUTER FROM target. SOQL grammar: `FROM <sObject>` — no schema
    // prefix, no JOIN. Sub-selects are now stripped, so the first match is the
    // outer target.
    const fromMatch = outerQuery.match(/\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b/i);
    const sobjectName = fromMatch?.[1];
    if (!sobjectName) {
      throw soqlError('SOQL must reference a single FROM <sObject>.', 'unsafe_sql');
    }
    if (!opts.knownSObjects.has(sobjectName.toLowerCase())) {
      throw soqlError(
        `Unknown sObject '${sobjectName}'. Use one of the introspected objects.`,
        'unknown_table'
      );
    }

    if (opts.knownFields) {
      const fieldsSet = opts.knownFields.get(sobjectName.toLowerCase());
      if (fieldsSet) {
        const unknown = findUnknownFields(outerQuery, fieldsSet, sobjectName);
        if (unknown.length > 0) {
          throw soqlError(
            `Field '${unknown[0]}' not in schema for sObject '${sobjectName}'.`,
            'unknown_column'
          );
        }
      }
    }

    if (/\bLIMIT\b/i.test(stripped)) {
      return { query: trimmed };
    }
    return { query: `${trimmed} LIMIT ${opts.rowLimit}` };
  }
}

function findUnknownFields(
  outerQuery: string,
  knownFields: Set<string>,
  sobjectName: string
): string[] {
  let cleaned = outerQuery.replace(/:[A-Za-z_][A-Za-z0-9_.]*/g, ' ');
  cleaned = cleaned.replace(/[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+/g, ' ');
  cleaned = cleaned.replace(/\b\d[\d._:T+\-Zz]*\b/g, ' ');

  const sobjectLower = sobjectName.toLowerCase();
  const tokenRe = /[A-Za-z_][A-Za-z0-9_]*/g;
  const unknown: string[] = [];
  const seen = new Set<string>();
  for (const m of cleaned.matchAll(tokenRe)) {
    const tok = m[0];
    const lower = tok.toLowerCase();
    if (SOQL_RESERVED.has(lower)) continue;
    if (SOQL_DATE_LITERAL_PREFIXES.test(tok)) continue;
    if (lower === sobjectLower) continue; // FROM target name itself
    if (seen.has(lower)) continue;
    seen.add(lower);
    if (!knownFields.has(lower)) {
      unknown.push(tok);
    }
  }
  return unknown;
}

/**
 * Drop SOQL sub-selects: any parenthesized group containing a nested SELECT.
 * Leaves function call argument lists (e.g. `COUNT(Id)`) intact so their field
 * references still get validated against the outer sObject's field set.
 */
function stripParenGroups(s: string): string {
  let prev: string;
  let out = s;
  do {
    prev = out;
    // Innermost parens containing a SELECT (case-insensitive). Repeat until
    // stable so nested sub-selects collapse too.
    out = out.replace(/\([^()]*\bSELECT\b[^()]*\)/gi, ' ');
  } while (out !== prev);
  return out;
}

function stripStringsAndComments(s: string): string {
  // Remove single-quoted strings, /* */ block comments, and -- line comments.
  return s
    .replace(/'(?:\\.|[^'\\])*'/g, "''")
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/--[^\n]*/g, ' ');
}

function soqlError(message: string, _code: string): UnsafeSqlError {
  return new UnsafeSqlError(message);
}
