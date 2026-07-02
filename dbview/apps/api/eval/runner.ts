import { isSqlDialect, type SchemaGraph, type UnifiedSchema } from '@dbview/shared';
import { SqlSafetyValidator, buildKnownSetsMemoized } from '@dbview/sql-core';
import { buildSystemPrompt, buildUserPromptBase, withRetryFeedback } from '../src/nl2sql/prompt.js';
import { sanitize } from '../src/nl2sql/grounding/sanitize.js';
import { pruneRelationalSchema } from '../src/nl2sql/grounding/prune.js';
import type { EvalCase, EvalResult, RunnerAdapter } from './types.js';

export interface RunnerOptions {
  /** Apply schema pruning before building the prompt. Default true (matches prod). */
  prune?: boolean;
  /** Max retries on validator rejection — same semantic as DBVIEW_NL2SQL_MAX_RETRIES. */
  maxRetries?: number;
  /** Default row limit; cases can override. */
  rowLimit?: number;
}

interface LlmJson {
  query: string;
  language: string;
  involvedEntities: string[];
}

const validator = new SqlSafetyValidator();

/**
 * Execute a single eval case against the prompt builder + sanitize + validator
 * pipeline using a pluggable adapter for the LLM step. Returns a structured
 * result with pass/fail + diagnostic reasons; never throws on test failure.
 *
 * Throws ONLY on programmer errors (e.g. non-relational schema for a SQL
 * dialect) so the caller knows the case file itself is wrong.
 */
export async function runEvalCase(
  evalCase: EvalCase,
  schema: SchemaGraph,
  adapter: RunnerAdapter,
  opts: RunnerOptions = {}
): Promise<EvalResult> {
  const t0 = Date.now();
  const prune = opts.prune ?? true;
  const maxRetries = opts.maxRetries ?? 2;
  const rowLimit = evalCase.rowLimit ?? opts.rowLimit ?? 100;

  let activeGraph: UnifiedSchema = schema;
  let usingPruned = false;
  if (prune) {
    const pr = pruneRelationalSchema(schema, evalCase.prompt, { threshold: 5, maxTables: 12 });
    if (pr.pruned) {
      activeGraph = pr.graph;
      usingPruned = true;
    }
  }

  let system = buildSystemPrompt(activeGraph, schema.dialect, false);
  let userBase = buildUserPromptBase({
    graph: activeGraph,
    dialect: schema.dialect,
    userPrompt: evalCase.prompt,
    rowLimit,
    allowDml: false,
  });

  let feedback: string | undefined;
  let lastQuery: string | undefined;
  let lastInvolved: string[] | undefined;
  let lastReason: string | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    let raw: string;
    try {
      raw = await adapter.complete(system, withRetryFeedback(userBase, feedback));
    } catch (err) {
      lastReason = `adapter threw: ${(err as Error).message}`;
      break;
    }

    let parsed: LlmJson;
    try {
      parsed = parseEnvelope(raw);
    } catch (err) {
      feedback = `Output was not valid JSON: ${(err as Error).message}`;
      lastReason = `parse: ${(err as Error).message}`;
      continue;
    }

    const sanitized = sanitize(parsed.query, {
      rowLimit,
      language: parsed.language === 'cypher' ? 'cypher' : 'sql',
      knownTables: new Set(
        activeGraph.kind === 'relational' ? activeGraph.tables.map((t) => t.id) : []
      ),
    });
    const sql = sanitized.query;

    if (activeGraph.kind !== 'relational') {
      lastReason = 'eval harness only supports relational schemas';
      break;
    }

    if (!isSqlDialect(schema.dialect)) {
      throw new Error(`eval harness currently only supports SQL dialects, got '${schema.dialect}'`);
    }
    const { knownTables, knownColumns } = buildKnownSetsMemoized(activeGraph);
    try {
      const result = validator.validate(sql, {
        dialect: schema.dialect,
        allowDml: false,
        rowLimit,
        knownTables,
        knownColumns,
      });
      lastQuery = result.sql;
      lastInvolved = result.involvedTables;
      return finalize(evalCase, lastQuery, lastInvolved, t0);
    } catch (err) {
      const msg = (err as Error).message;
      feedback = `Generated query rejected: ${msg}. Regenerate using ONLY entities listed.`;
      lastReason = `validator: ${msg}`;
      if (usingPruned && schema.kind === 'relational') {
        // Mirror the prod fallback: revert to full schema on unknown-entity.
        activeGraph = schema;
        usingPruned = false;
        system = buildSystemPrompt(activeGraph, schema.dialect, false);
        userBase = buildUserPromptBase({
          graph: activeGraph,
          dialect: schema.dialect,
          userPrompt: evalCase.prompt,
          rowLimit,
          allowDml: false,
        });
      }
    }
  }

  return {
    caseId: evalCase.id,
    passed: false,
    reasons: [lastReason ?? 'unknown failure', ...(lastQuery ? [`last query: ${lastQuery}`] : [])],
    validatedQuery: lastQuery,
    involvedTables: lastInvolved,
    durationMs: Date.now() - t0,
  };
}

function finalize(evalCase: EvalCase, query: string, involved: string[], t0: number): EvalResult {
  const reasons: string[] = [];
  const lower = query.toLowerCase();
  const exp = evalCase.expectations;
  if (exp.mustInvolveTables) {
    for (const t of exp.mustInvolveTables) {
      if (!involved.includes(t)) reasons.push(`missing involved table: ${t}`);
    }
  }
  if (exp.onlyInvolveTables) {
    const allowed = new Set(exp.onlyInvolveTables);
    for (const t of involved) {
      if (!allowed.has(t)) reasons.push(`unexpected involved table: ${t}`);
    }
  }
  if (exp.mustContain) {
    for (const needle of exp.mustContain) {
      if (!lower.includes(needle.toLowerCase())) reasons.push(`missing substring: "${needle}"`);
    }
  }
  if (exp.mustNotContain) {
    for (const needle of exp.mustNotContain) {
      if (lower.includes(needle.toLowerCase()))
        reasons.push(`forbidden substring present: "${needle}"`);
    }
  }
  return {
    caseId: evalCase.id,
    passed: reasons.length === 0,
    reasons,
    validatedQuery: query,
    involvedTables: involved,
    durationMs: Date.now() - t0,
  };
}

function parseEnvelope(raw: string): LlmJson {
  const stripped = raw
    .trim()
    .replace(/^```json\s*/i, '')
    .replace(/^```\s*/i, '')
    .replace(/```\s*$/i, '');
  const start = stripped.indexOf('{');
  const end = stripped.lastIndexOf('}');
  if (start < 0 || end < start) throw new Error('No JSON object found.');
  const obj = JSON.parse(stripped.slice(start, end + 1)) as Partial<LlmJson> & { sql?: string };
  const query = obj.query ?? obj.sql;
  if (typeof query !== 'string' || !query.trim()) throw new Error('Missing query field.');
  return {
    query,
    language: typeof obj.language === 'string' ? obj.language : 'sql',
    involvedEntities: Array.isArray(obj.involvedEntities)
      ? obj.involvedEntities.filter((x): x is string => typeof x === 'string')
      : [],
  };
}

export interface ReportSummary {
  total: number;
  passed: number;
  failed: number;
  durationMs: number;
}

export function summarize(results: EvalResult[]): ReportSummary {
  return {
    total: results.length,
    passed: results.filter((r) => r.passed).length,
    failed: results.filter((r) => !r.passed).length,
    durationMs: results.reduce((acc, r) => acc + r.durationMs, 0),
  };
}

/**
 * Render a compact, copy-pasteable text report. Used by the CLI runner so
 * humans can scan failures quickly; tests use the structured `EvalResult[]`
 * directly without going through this formatter.
 */
export function renderReport(results: EvalResult[]): string {
  const lines: string[] = [];
  for (const r of results) {
    const status = r.passed ? 'PASS' : 'FAIL';
    lines.push(`[${status}] ${r.caseId} (${r.durationMs}ms)`);
    if (!r.passed) {
      for (const reason of r.reasons) lines.push(`       - ${reason}`);
    }
  }
  const s = summarize(results);
  lines.push(`\n${s.passed}/${s.total} passed (${s.failed} failed) in ${s.durationMs}ms`);
  return lines.join('\n');
}
