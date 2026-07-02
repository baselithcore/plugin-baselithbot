import {
  LlmProviderError,
  ModelOutputError,
  type Nl2ConversationTurn,
  type SchemaGraph,
} from '@dbview/shared';
import type {
  LlmAdapter,
  LlmCompletionInput,
  LlmCompletionResult,
  StructuredContext,
} from './provider.js';

/**
 * Adapter for the sqlcoder model family (raw SQL completion model).
 *
 * sqlcoder is NOT chat-tuned: it expects a single prompt ending with `[SQL]`
 * and returns raw SQL (no JSON, no narrative). We:
 *   1) call Ollama's `/api/generate` (completion endpoint)
 *   2) render a sqlcoder-style prompt from the structured context
 *   3) parse raw SQL from the response
 *   4) wrap it in synthetic LlmJson so the rest of the pipeline is uniform
 *
 * Per defog/sqlcoder model card: https://huggingface.co/defog/sqlcoder-7b-2
 */
export class SqlcoderAdapter implements LlmAdapter {
  readonly provider = 'ollama' as const;
  readonly name = 'ollama-sqlcoder';

  constructor(private readonly baseUrl: string) {}

  async complete(input: LlmCompletionInput, model: string): Promise<LlmCompletionResult> {
    if (!input.structured) {
      throw new LlmProviderError(
        `sqlcoder adapter requires structured context (schema, dialect, userPrompt).`
      );
    }
    if (input.structured.schema.kind !== 'relational') {
      throw new LlmProviderError(
        `sqlcoder only supports relational schemas; got '${input.structured.schema.kind}'.`
      );
    }

    const prompt = renderSqlcoderPrompt(input.structured);
    const url = `${normalizeBase(this.baseUrl)}/generate`;
    const body = {
      model,
      prompt,
      stream: false,
      raw: true,
      options: {
        temperature: input.temperature ?? 0,
        // Stop on a fresh section header or another fenced block (defog format).
        // We do NOT include `[SQL]` here: it appears in the prompt itself as a cue,
        // so listing it as a stop token caused immediate truncation on echoed output.
        stop: [';', '\n```', '\n### '],
        num_predict: 1024,
      },
    };

    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 120_000);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new LlmProviderError(
          `sqlcoder (${model}) returned ${res.status}: ${text.slice(0, 200) || res.statusText}`
        );
      }
      const json = (await res.json()) as { response?: string; error?: string };
      if (json.error) throw new LlmProviderError(`sqlcoder (${model}) error: ${json.error}`);
      const raw = json.response ?? '';
      if (!raw.trim()) throw new LlmProviderError(`sqlcoder (${model}) returned empty content.`);

      const sql = extractSql(raw);
      if (!sql) {
        throw new ModelOutputError(
          `sqlcoder (${model}) output did not contain a SELECT/WITH statement; got: ${raw.slice(0, 200).replace(/\n/g, ' ')}`
        );
      }
      const wrapped = JSON.stringify({
        query: sql,
        language: 'sql',
        explanation: '',
        joinNotes: [],
        involvedEntities: [],
      });
      return { text: wrapped, model };
    } catch (err) {
      if (err instanceof LlmProviderError || err instanceof ModelOutputError) throw err;
      if ((err as { name?: string }).name === 'AbortError') {
        throw new LlmProviderError(`sqlcoder (${model}) timed out after 120s.`);
      }
      throw new LlmProviderError(`sqlcoder (${model}) failed: ${(err as Error).message}`);
    } finally {
      clearTimeout(timeout);
    }
  }
}

/**
 * Render a defog/sqlcoder-2 prompt. Mirrors the official training template:
 *   ### Task → ### Database Schema → ### Answer → ```sql cue.
 * The model continues from the opening fence with raw SQL.
 *
 * Reference: https://huggingface.co/defog/sqlcoder-7b-2
 */
export function renderSqlcoderPrompt(ctx: StructuredContext): string {
  const schema = ctx.schema as SchemaGraph;
  const ddl = renderDdl(schema);
  const question = ctx.userPrompt.trim();
  const feedback = ctx.retryFeedback
    ? `\nThe previous attempt was rejected: ${ctx.retryFeedback.replace(/\n/g, ' ')}. Fix the issue.\n`
    : '';
  const priorTurns = renderPriorTurns(ctx.history);
  // SQLite has no user schemas; tables are unqualified (`Brands`, not `main.Brands`).
  // Other dialects use the schema prefix exactly as shown in the DDL.
  const tableExample = pickTableExample(schema);
  const namingRule =
    ctx.dialect === 'sqlite'
      ? `- Use the bare table names exactly as shown in the DDL (e.g. ${tableExample}). NEVER add a schema prefix like "main." or any other dot prefix — SQLite has no user schemas.`
      : `- Use schema-qualified table names exactly as shown in the DDL (e.g. ${tableExample}).`;
  const limitRule = `- LIMIT must be a literal positive integer. NEVER write "LIMIT N", "LIMIT <n>", "LIMIT ?" or any placeholder. If the question states a number ("3 customers" => LIMIT 3, "first 5 orders" => LIMIT 5), use it. Otherwise use LIMIT ${ctx.rowLimit}. Never exceed ${ctx.rowLimit}.`;
  return [
    priorTurns,
    `### Task`,
    `Generate a SQL query (dialect: ${ctx.dialect}) that answers the question: \`${question}\``,
    ``,
    `### Instructions`,
    namingRule,
    `- Single SELECT statement only. No DDL/DML, no semicolons except the terminator.`,
    `- Use ONLY columns and tables defined in the schema below. Never invent columns.`,
    `- Do NOT add WHERE filters, joins, or ORDER BY clauses unless implied by the question.`,
    `- Vague phrasing like "top N", "main", "principali" => no WHERE clause; just SELECT + LIMIT (and ORDER BY only when a metric is named).`,
    limitRule,
    `- Output the final SQL only. No explanations, no preamble like "Here is" or "Sure", no trailing notes.`,
    feedback,
    `### Database Schema`,
    `The query will run on a database whose schema is described by these CREATE TABLE statements:`,
    ddl,
    ``,
    `### Answer`,
    `Given the question \`${question}\`, the SQL query is:`,
    '```sql',
  ].join('\n');
}

function pickTableExample(schema: SchemaGraph): string {
  return schema.tables[0]?.id ?? 'my_table';
}

/**
 * Render prior conversation turns in a sqlcoder-compatible section. Output
 * is empty when there is no history, so existing single-turn prompts stay
 * byte-identical. Each prior assistant SQL is truncated to keep the model's
 * attention focused on the current question.
 */
function renderPriorTurns(history: readonly Nl2ConversationTurn[] | undefined): string {
  if (!history || history.length === 0) return '';
  const lines: string[] = ['### Prior conversation (most recent last)'];
  history.forEach((turn, idx) => {
    const n = idx + 1;
    const prompt = turn.prompt.replace(/\s+/g, ' ').trim().slice(0, 280);
    lines.push(`-- Turn ${n} user: ${prompt}`);
    if (turn.query) {
      const q = turn.query.replace(/\s+/g, ' ').trim().slice(0, 400);
      const rows =
        turn.rowCount === undefined || turn.rowCount === null ? '' : ` (rows=${turn.rowCount})`;
      const status = turn.ok === false ? ' [failed]' : '';
      lines.push(`-- Turn ${n} sql${status}${rows}: ${q}`);
    }
  });
  lines.push(
    '-- Treat the new question as a follow-up; resolve references ("these", "previous", "now", "il precedente") against these turns. Re-emit a full new SQL — do not copy verbatim.'
  );
  lines.push('');
  return lines.join('\n');
}

function renderDdl(schema: SchemaGraph): string {
  const lines: string[] = [];
  for (const t of schema.tables) {
    lines.push(`CREATE TABLE ${t.id} (`);
    const cols = t.columns.map((c) => {
      const flags: string[] = [];
      if (c.isPrimaryKey) flags.push('PRIMARY KEY');
      if (!c.nullable) flags.push('NOT NULL');
      if (c.isUnique && !c.isPrimaryKey) flags.push('UNIQUE');
      const tail = flags.length ? ` ${flags.join(' ')}` : '';
      return `  ${c.name} ${c.dataType.toUpperCase()}${tail}`;
    });
    lines.push(cols.join(',\n'));
    lines.push(`);`);
  }
  if (schema.edges.length) {
    lines.push('-- Foreign key relationships:');
    for (const e of schema.edges) {
      lines.push(`-- ${e.source}.${e.sourceColumn} -> ${e.target}.${e.targetColumn}`);
    }
  }
  return lines.join('\n');
}

/**
 * Extract a single SQL statement from sqlcoder's raw output. Strips markdown
 * fences, leading prose, trailing prose, and ensures the result starts with
 * a real SQL query keyword (SELECT or WITH). Returns "" when no valid
 * statement can be located — caller treats empty as a parse failure and
 * triggers a retry with adjusted temperature.
 */
export function extractSql(raw: string): string {
  let s = raw.trim();
  // Remove leading markdown fence with optional language.
  s = s.replace(/^```(?:sql)?\s*\n?/i, '');
  // Cut at closing fence.
  const fenceEnd = s.indexOf('```');
  if (fenceEnd >= 0) s = s.slice(0, fenceEnd);
  // Drop a trailing `[SQL]` echo if present.
  s = s.replace(/^\[SQL\]\s*/i, '').trim();
  // Locate the first SELECT or WITH keyword and discard any prose before it.
  const startMatch = s.match(/\b(SELECT|WITH)\b/i);
  if (!startMatch) return '';
  s = s.slice(startMatch.index ?? 0);
  // Cut at the first semicolon (statement terminator).
  const semi = s.indexOf(';');
  if (semi >= 0) s = s.slice(0, semi);
  // Cut at the first blank line followed by non-SQL prose ("Note:", "Here is").
  const proseRe = /\n\s*\n+\s*(?:Note|Here|This|The query|Explanation)\b/i;
  const proseMatch = s.match(proseRe);
  if (proseMatch && proseMatch.index !== undefined) {
    s = s.slice(0, proseMatch.index);
  }
  return s.trim();
}

function normalizeBase(raw: string): string {
  let s = raw.trim().replace(/\/+$/, '');
  if (!/\/api$/.test(s)) s = `${s}/api`;
  return s;
}
