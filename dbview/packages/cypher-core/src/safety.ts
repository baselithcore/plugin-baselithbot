import { UnsafeSqlError, type PropertyGraphSchema, type SafetyWarning } from '@dbview/shared';

export interface CypherSafetyOptions {
  schema: PropertyGraphSchema;
  rowLimit: number;
  allowWrites: boolean;
}

export interface CypherValidationResult {
  query: string;
  warnings: SafetyWarning[];
  involvedLabels: string[];
}

const FORBIDDEN_KEYWORDS = [
  'CREATE',
  'DELETE',
  'DETACH',
  'MERGE',
  'SET',
  'REMOVE',
  'DROP',
  'LOAD',
  'USING',
  'FOREACH',
] as const;

const FORBIDDEN_CALL_PREFIXES = [
  'apoc.create',
  'apoc.merge',
  'apoc.refactor',
  'apoc.load',
  'apoc.export',
  'apoc.periodic',
  'db.create',
  'db.drop',
  'dbms.',
  'tx.',
] as const;

const ALLOWED_FIRST_KEYWORDS = ['MATCH', 'OPTIONAL', 'WITH', 'CALL', 'UNWIND', 'RETURN'] as const;

export class CypherSafetyValidator {
  validate(rawQuery: string, opts: CypherSafetyOptions): CypherValidationResult {
    const stripped = stripComments(rawQuery)
      .trim()
      .replace(/;+\s*$/, '');
    if (!stripped) throw new UnsafeSqlError('Empty Cypher after stripping comments.');
    if (stripped.includes(';')) throw new UnsafeSqlError('Multiple statements not allowed.');

    const upper = stripped.toUpperCase();
    const tokens = tokenize(upper);
    const firstWord = tokens[0];
    if (!firstWord || !(ALLOWED_FIRST_KEYWORDS as readonly string[]).includes(firstWord)) {
      throw new UnsafeSqlError(
        `Cypher must start with ${ALLOWED_FIRST_KEYWORDS.join('/')}; got '${firstWord ?? '<empty>'}'.`,
      );
    }

    if (!opts.allowWrites) {
      for (const kw of FORBIDDEN_KEYWORDS) {
        if (tokens.includes(kw)) {
          throw new UnsafeSqlError(`Cypher keyword '${kw}' blocked (write operation).`);
        }
      }
      const callMatches = stripped.matchAll(/\bCALL\s+([A-Za-z][A-Za-z0-9_.]+)/gi);
      for (const m of callMatches) {
        const proc = (m[1] ?? '').toLowerCase();
        for (const prefix of FORBIDDEN_CALL_PREFIXES) {
          if (proc.startsWith(prefix)) {
            throw new UnsafeSqlError(`Procedure '${proc}' blocked (write/admin).`);
          }
        }
      }
    }

    assertProperTermination(stripped);
    assertNoSchemaTypeLeak(stripped);
    assertNoUnknownProperties(stripped, opts.schema);

    const involvedLabels = collectLabels(stripped);
    const knownLabels = new Set(opts.schema.labels.map((l) => l.label));
    const warnings: SafetyWarning[] = [];
    for (const lbl of involvedLabels) {
      if (!knownLabels.has(lbl)) {
        warnings.push({
          code: 'unknown_label',
          severity: 'error',
          message: `Label '${lbl}' not in schema.`,
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

    let query = stripped;
    if (!/\bLIMIT\s+\d+/i.test(query)) {
      query = `${query} LIMIT ${opts.rowLimit}`;
      warnings.push({
        code: 'missing_limit',
        severity: 'info',
        message: `Auto-injected LIMIT ${opts.rowLimit}.`,
      });
    }
    return { query, warnings, involvedLabels };
  }
}

function stripComments(s: string): string {
  return s.replace(/\/\/[^\n]*\n/g, '\n').replace(/\/\*[\s\S]*?\*\//g, ' ');
}

function tokenize(upper: string): string[] {
  return upper.split(/[^A-Z_]+/).filter(Boolean);
}

/**
 * Read-only Cypher must terminate with RETURN, UNION (whose final branch returns), or a
 * read-only CALL ... YIELD that exposes columns. A trailing WITH/ORDER BY/LIMIT alone is
 * a parse error in Neo4j and FalkorDB. Catching it here gives a clear 400 instead of a
 * generic engine 500.
 */
function assertProperTermination(query: string): void {
  const cleaned = query.replace(/\s+/g, ' ').trim();
  const upper = cleaned.toUpperCase();
  if (/\bRETURN\b/.test(upper)) return;
  if (/\bUNION\b/.test(upper)) return;
  if (/\bYIELD\b/.test(upper)) return;
  throw new UnsafeSqlError(
    'Read query must end with RETURN (or UNION/YIELD). Trailing WITH/ORDER BY/LIMIT alone is invalid.',
  );
}

/**
 * Detect schema-notation leaks like `[:CONTAINS { qty: INTEGER }]` where the LLM copied a
 * descriptive type from the prompt schema into a property-map filter, which Cypher rejects.
 */
/**
 * Reject queries referencing `var.prop` where `prop` is not declared on any label or
 * relationship in the schema. Catches LLM-invented properties (e.g. `o.createdAt` when
 * Order has only id/status/total) before they silently match nothing at runtime.
 */
function assertNoUnknownProperties(query: string, schema: PropertyGraphSchema): void {
  const known = new Set<string>();
  for (const l of schema.labels) for (const p of l.properties) known.add(p.name);
  for (const r of schema.relationships) for (const p of r.properties) known.add(p.name);
  // Strip string literals so `'a.b.c'` does not trigger.
  const cleaned = query.replace(/'(?:\\.|[^'\\])*'/g, "''").replace(/"(?:\\.|[^"\\])*"/g, '""');
  const refs = cleaned.matchAll(/\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b/g);
  const unknown = new Set<string>();
  for (const m of refs) {
    const prop = m[2];
    if (prop && !known.has(prop)) unknown.add(`${m[1]}.${prop}`);
  }
  if (unknown.size > 0) {
    throw new UnsafeSqlError(
      `Property reference(s) not in schema: ${[...unknown].join(', ')}. Use only properties listed in the schema; do not invent (e.g. createdAt, updatedAt) when none exists.`,
    );
  }
}

function assertNoSchemaTypeLeak(query: string): void {
  // Match `key: TYPE` inside `{...}` where TYPE is an unquoted ALL-CAPS schema type token.
  // Strip string literals first so `{type: "STRING"}` does not false-positive.
  const noStrings = query.replace(/'(?:\\.|[^'\\])*'/g, "''").replace(/"(?:\\.|[^"\\])*"/g, '""');
  const propMaps = noStrings.matchAll(/\{([^{}]*)\}/g);
  const TYPE_TOKEN =
    /:\s*(INTEGER|STRING|FLOAT|BOOLEAN|DATE|DATETIME|TIME|POINT|LIST|MAP|NUMBER)\b/;
  for (const m of propMaps) {
    const body = m[1] ?? '';
    if (TYPE_TOKEN.test(body)) {
      throw new UnsafeSqlError(
        'Property map contains a schema type name (e.g. `{qty: INTEGER}`). Schema types are descriptive — use literal values or omit the filter.',
      );
    }
  }
}

function collectLabels(query: string): string[] {
  const out = new Set<string>();
  // Node patterns: `(varname?:Label1[:Label2]...)`. Skip relationship patterns `[...]`.
  const nodePatterns = query.matchAll(/\(([^()]*)\)/g);
  for (const np of nodePatterns) {
    const inside = np[1] ?? '';
    const labelMatches = inside.matchAll(/:`?([A-Za-z_][A-Za-z0-9_]*)`?/g);
    for (const lm of labelMatches) {
      const label = lm[1];
      if (label) out.add(label);
    }
  }
  return [...out];
}
