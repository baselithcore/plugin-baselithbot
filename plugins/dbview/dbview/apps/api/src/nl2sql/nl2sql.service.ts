import { Injectable, Logger } from '@nestjs/common';
import {
  LlmProviderError,
  ModelOutputError,
  SchemaMismatchError,
  UnsafeSqlError,
  dialectKind,
  isGraphDialect,
  isRemoteLlmProvider,
  isSaasDialect,
  isSqlDialect,
  type LlmProvider,
  type Nl2SqlRequest,
  type Nl2SqlResponse,
  type QueryLanguage,
  type SafetyWarning,
  type UnifiedSchema,
} from '@dbview/shared';
import { SqlSafetyValidator, buildKnownSetsMemoized } from '@dbview/sql-core';
import { CypherSafetyValidator } from '@dbview/cypher-core';
import { SalesforceSafetyValidator } from '../engine/salesforce/safety.js';
import { SalesforceDataCloudSafetyValidator } from '../engine/salesforce-data-cloud/safety.js';
import { SchemaService } from '../schema/schema.service.js';
import { ConnectionsService } from '../connections/connections.service.js';
import { LlmCredentialsService } from '../llm/credentials.service.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import {
  createChatAdapter,
  createLlmAdapter,
  defaultExplainModel,
  defaultModelFor,
  type LlmAdapterAuth,
} from './llm/factory.js';
import type { StructuredContext } from './llm/provider.js';
import {
  buildSystemPrompt,
  buildUserPromptBase,
  renderHistoryBlock,
  withRetryFeedback,
} from './prompt.js';
import { explainQuery } from './explainer.js';
import { buildSuggestionMap } from './grounding/suggest.js';
import { sanitize } from './grounding/sanitize.js';
import { pruneRelationalSchema } from './grounding/prune.js';
import { instrumentLlmAdapter } from '../observability/instrument-llm.js';

interface LlmJson {
  query: string;
  language: QueryLanguage;
  explanation: string;
  joinNotes: string[];
  involvedEntities: string[];
}

/**
 * Maximum retry attempts when the validator rejects an LLM-generated query
 * (unknown table/column/sObject/field, parse error, etc.). Each retry feeds
 * the rejection reason back to the model.
 *
 * Cost trade-off: each retry is one extra LLM round-trip. With a slow local
 * Ollama model (~10–30s/call) a worst-case run is `(MAX_RETRIES + 1)` calls.
 * Override with `DBVIEW_NL2SQL_MAX_RETRIES` (clamped to 0..4). Set to 0 to
 * disable retries — the first hallucination then surfaces as the final error.
 */
const MAX_RETRIES = clampRetries(process.env.DBVIEW_NL2SQL_MAX_RETRIES, 2);

function clampRetries(raw: string | undefined, fallback: number): number {
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(4, n));
}

/**
 * Schemas with at most this many tables are sent to the LLM in full. Above the
 * threshold, the prompt is pruned to the tables whose name/displayName/columns
 * overlap with the user question (plus a 1-hop FK closure for joins). The
 * full schema remains available as a fallback when validation rejects an
 * unknown-table reference.
 *
 * Override with `DBVIEW_NL2SQL_PRUNE_THRESHOLD` (clamped to 0..1000); set to a
 * very high number to disable pruning. `DBVIEW_NL2SQL_PRUNE_TOPK` controls how
 * many seed tables to pick before FK closure (default 12, clamped to 1..200).
 */
const PRUNE_THRESHOLD = clampNumber(process.env.DBVIEW_NL2SQL_PRUNE_THRESHOLD, 30, 0, 1000);
const PRUNE_TOPK = clampNumber(process.env.DBVIEW_NL2SQL_PRUNE_TOPK, 12, 1, 200);

function clampNumber(raw: string | undefined, fallback: number, lo: number, hi: number): number {
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(lo, Math.min(hi, n));
}

const UNKNOWN_TABLE_RE = /Table\s+'([^']+)'\s+not in schema/g;
const UNKNOWN_COLUMN_RE = /Column\s+'([^']+)'\s+not in schema/g;
const UNKNOWN_LABEL_RE = /Label\s+'([^']+)'\s+not in schema/g;
const UNKNOWN_SOBJECT_RE = /Unknown sObject\s+'([^']+)'/g;
const UNKNOWN_FIELD_RE = /Field\s+'([^']+)'\s+not in schema/g;

@Injectable()
export class Nl2SqlService {
  private readonly logger = new Logger('Nl2SqlService');
  private readonly sqlValidator = new SqlSafetyValidator();
  private readonly cypherValidator = new CypherSafetyValidator();
  private readonly soqlValidator = new SalesforceSafetyValidator();
  private readonly sdcValidator = new SalesforceDataCloudSafetyValidator();

  constructor(
    private readonly connections: ConnectionsService,
    private readonly schema: SchemaService,
    private readonly credentials: LlmCredentialsService,
  ) {}

  async translate(req: Nl2SqlRequest, principal: AuthPrincipal): Promise<Nl2SqlResponse> {
    const conn = this.connections.get(req.connectionId, principal);
    const fullGraph = await this.schema.getGraph(req.connectionId, principal);
    const kind = dialectKind(conn.dialect);
    const model = req.model ?? defaultModelFor(req.provider, kind);
    const auth = this.resolveAuth(req.provider, principal);
    const adapter = instrumentLlmAdapter(createLlmAdapter(req.provider, model, auth), 'translate');

    // Wide relational schemas dilute the LLM's attention. Prune to the tables
    // matching the question; keep the full graph available so the retry loop
    // can fall back to it on `unknown table` rejections (in case pruning was
    // too aggressive for an oblique question).
    let graph: UnifiedSchema = fullGraph;
    let usingPruned = false;
    if (fullGraph.kind === 'relational') {
      const pruneResult = pruneRelationalSchema(fullGraph, req.prompt, {
        threshold: PRUNE_THRESHOLD,
        maxTables: PRUNE_TOPK,
      });
      if (pruneResult.pruned) {
        graph = pruneResult.graph;
        usingPruned = true;
        this.logger.log(
          `nl2query schema-pruned ${fullGraph.tables.length}->${pruneResult.graph.tables.length} tokens=[${pruneResult.matchedTokens.slice(0, 8).join(',')}]`,
        );
      }
    }

    let system = buildSystemPrompt(graph, conn.dialect, req.allowDml);
    let userPromptBase = buildUserPromptBase({
      graph,
      dialect: conn.dialect,
      userPrompt: req.prompt,
      rowLimit: req.rowLimit,
      allowDml: req.allowDml,
    });
    let knownEntities = collectKnownEntities(graph);
    let feedback: string | undefined;
    let lastError: Error | null = null;
    let lastRejectedQuery: string | null = null;
    let groundingFailure: { unknown: string[]; reason: string } | null = null;
    const historyBlock = renderHistoryBlock(req.history);
    const t0 = Date.now();

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      const userWithRetry = withRetryFeedback(userPromptBase, feedback);
      const user = historyBlock ? `${historyBlock}\n\n${userWithRetry}` : userWithRetry;
      const structured: StructuredContext = {
        schema: graph,
        dialect: conn.dialect,
        userPrompt: req.prompt,
        allowDml: req.allowDml,
        rowLimit: req.rowLimit,
        retryFeedback: feedback,
        history: req.history,
      };

      // Deterministic on first attempt; raise temperature on retries so the
      // model actually explores a different output instead of repeating the
      // exact same hallucinated tokens.
      const temperature = attempt === 0 ? 0 : Math.min(0.7, 0.3 * attempt);

      let completion: { text: string; model: string };
      try {
        completion = await adapter.complete({ system, user, temperature, structured }, model);
      } catch (err) {
        if (err instanceof ModelOutputError) {
          feedback = `Model returned unusable output: ${err.message}. Output a single SELECT or WITH statement, no prose.`;
          lastError = err;
          this.logger.warn(
            `nl2query model-output-invalid attempt=${attempt} adapter=${adapter.name ?? adapter.provider} model=${model}: ${err.message}`,
          );
          continue;
        }
        throw err;
      }

      let parsed: LlmJson;
      try {
        parsed = parseJsonResponse(completion.text);
      } catch (err) {
        feedback = `Output was not valid JSON: ${(err as Error).message}`;
        lastError = err as Error;
        this.logger.warn(
          `nl2query parse-error attempt=${attempt} adapter=${adapter.name ?? adapter.provider} model=${model} dialect=${conn.dialect}: ${(err as Error).message}`,
        );
        continue;
      }

      try {
        if (parsed.language === 'sql' || parsed.language === 'cypher') {
          const sanitized = sanitize(parsed.query, {
            rowLimit: req.rowLimit,
            language: parsed.language,
            knownTables:
              graph.kind === 'relational' ? new Set(graph.tables.map((t) => t.id)) : undefined,
            stripAllSchemaPrefixes:
              conn.dialect === 'sqlite' || conn.dialect === 'salesforce-data-cloud',
          });
          if (sanitized.fixes.length > 0) {
            this.logger.warn(
              `nl2query sanitized attempt=${attempt} dialect=${conn.dialect} fixes=[${sanitized.fixes.join('; ')}]`,
            );
            parsed = { ...parsed, query: sanitized.query };
          }
        }
        // Log the full query about to be validated at INFO so it always shows.
        // Without this, weak-model failures look like opaque parser errors.
        this.logger.log(
          `nl2query candidate attempt=${attempt} dialect=${conn.dialect} query=${JSON.stringify(parsed.query)}`,
        );
        const annotated = this.validate(parsed, graph, req);
        const explanationMissing =
          !annotated.explanation || annotated.explanation.trim().length === 0;
        const joinNotesMissing = annotated.joinNotes.length === 0;
        if (
          (explanationMissing || joinNotesMissing) &&
          (annotated.language === 'sql' || annotated.language === 'cypher')
        ) {
          const explainer = instrumentLlmAdapter(createChatAdapter(req.provider, auth), 'explain');
          const explainModel = defaultExplainModel(req.provider);
          const explainStart = Date.now();
          const enriched = await explainQuery(explainer, explainModel, {
            query: annotated.query,
            language: annotated.language,
            dialect: conn.dialect,
            userPrompt: req.prompt,
            schema: graph,
            locale: req.locale,
          });
          if (explanationMissing && enriched.explanation)
            annotated.explanation = enriched.explanation;
          if (joinNotesMissing && enriched.joinNotes.length > 0)
            annotated.joinNotes = enriched.joinNotes;
          this.logger.log(
            `nl2query explained adapter=${explainer.name ?? explainer.provider} model=${explainModel} durationMs=${Date.now() - explainStart} hasExplanation=${enriched.explanation.length > 0}`,
          );
        }
        const durationMs = Date.now() - t0;
        this.logger.log(
          `nl2query ok adapter=${adapter.name ?? adapter.provider} model=${model} dialect=${conn.dialect} kind=${kind} retries=${attempt} durationMs=${durationMs} entities=${annotated.involvedEntities.length}`,
        );
        return {
          ...annotated,
          dialect: conn.dialect,
          provider: req.provider,
          model: completion.model,
          retries: attempt,
        };
      } catch (err) {
        if (err instanceof UnsafeSqlError) {
          const unknown = extractUnknownEntities(err.message);
          // If the rejection cited a table/column that exists in the FULL
          // schema but not in the pruned slice we sent, the prune was the
          // problem — reset to the full graph and let the next retry use the
          // complete entity list. We do this once: subsequent failures are
          // genuine hallucinations.
          if (usingPruned && unknown.length > 0 && fullGraph.kind === 'relational') {
            const fullKnown = collectKnownEntities(fullGraph);
            const fullSet = new Set(fullKnown.map((e) => e.toLowerCase()));
            const recoverable = unknown.some((u) => fullSet.has(u.toLowerCase()));
            if (recoverable) {
              graph = fullGraph;
              usingPruned = false;
              system = buildSystemPrompt(graph, conn.dialect, req.allowDml);
              userPromptBase = buildUserPromptBase({
                graph,
                dialect: conn.dialect,
                userPrompt: req.prompt,
                rowLimit: req.rowLimit,
                allowDml: req.allowDml,
              });
              knownEntities = collectKnownEntities(graph);
              this.logger.log(
                `nl2query schema-pruned-fallback attempt=${attempt} unknown=[${unknown.join(',')}] reverted to full schema`,
              );
            }
          }
          if (unknown.length > 0) {
            const suggestions = buildSuggestionMap(unknown, knownEntities);
            const hint = formatSuggestions(suggestions, knownEntities);
            const columnLocations =
              graph.kind === 'relational' ? buildColumnLocationHint(unknown, graph) : '';
            feedback = `Generated query rejected: ${err.message}. ${hint}${columnLocations} Regenerate using ONLY the allowed entities listed in the user prompt.`;
            groundingFailure = { unknown, reason: err.message };
          } else {
            feedback = `Generated query rejected by safety validator: ${err.message}. Regenerate fixing this.`;
            groundingFailure = null;
          }
          lastError = err;
          lastRejectedQuery = parsed.query;
          this.logger.warn(
            `nl2query unsafe attempt=${attempt} adapter=${adapter.name ?? adapter.provider} model=${model} dialect=${conn.dialect} unknown=[${unknown.join(',')}]: ${err.message}`,
          );
          this.logger.warn(`nl2query rejected query=${JSON.stringify(parsed.query)}`);
          continue;
        }
        throw err;
      }
    }

    const attempts = MAX_RETRIES + 1;
    this.logger.error(
      `nl2query failed adapter=${adapter.name ?? adapter.provider} model=${model} dialect=${conn.dialect} retries=${attempts} lastQuery=${JSON.stringify(lastRejectedQuery ?? '')}: ${lastError?.message ?? 'unknown'}`,
    );
    if (groundingFailure) {
      const suggestions = buildSuggestionMap(groundingFailure.unknown, knownEntities);
      const columnLocations =
        graph.kind === 'relational'
          ? buildColumnLocationMap(groundingFailure.unknown, graph)
          : undefined;
      throw new SchemaMismatchError(
        `Could not generate a query grounded in the schema after ${attempts} attempts. ${groundingFailure.reason}`,
        {
          attempts,
          unknownEntities: groundingFailure.unknown,
          availableEntities: knownEntities,
          suggestions,
          lastRejectedQuery: lastRejectedQuery ?? undefined,
          columnLocations,
        },
      );
    }
    const tail = lastRejectedQuery
      ? ` Last attempt: ${truncateOneLine(lastRejectedQuery, 200)}`
      : '';
    throw new LlmProviderError(
      `NL2Query failed after ${attempts} attempts: ${lastError?.message ?? 'unknown'}.${tail}`,
    );
  }

  /**
   * Resolve adapter auth for a request. Ollama (local) needs none; remote
   * providers get a per-user key if stored, else fall back to env (preserves
   * the original deployment-level configuration path so existing installs
   * keep working without per-user onboarding).
   */
  resolveAuth(provider: LlmProvider, principal: AuthPrincipal): LlmAdapterAuth {
    if (!isRemoteLlmProvider(provider)) return {};
    return { apiKey: this.credentials.resolveApiKey(provider, principal) };
  }

  private validate(
    parsed: LlmJson,
    graph: UnifiedSchema,
    req: Nl2SqlRequest,
  ): {
    query: string;
    language: QueryLanguage;
    explanation: string;
    joinNotes: string[];
    involvedEntities: string[];
    warnings: SafetyWarning[];
  } {
    if (graph.kind === 'relational' && isSqlDialect(graph.dialect)) {
      const { knownTables, knownColumns } = buildKnownSetsMemoized(graph);
      const r = this.sqlValidator.validate(parsed.query, {
        dialect: graph.dialect,
        allowDml: req.allowDml,
        rowLimit: req.rowLimit,
        knownTables,
        knownColumns,
      });
      return {
        query: r.sql,
        language: 'sql',
        explanation: parsed.explanation,
        joinNotes: parsed.joinNotes ?? [],
        involvedEntities: r.involvedTables,
        warnings: r.warnings,
      };
    }
    if (graph.kind === 'relational' && isSaasDialect(graph.dialect)) {
      if (graph.dialect === 'salesforce-data-cloud') {
        const { knownTables, knownColumns } = buildKnownSetsMemoized(graph);
        const r = this.sdcValidator.validate(parsed.query, {
          rowLimit: req.rowLimit,
          knownTables,
          knownColumns,
        });
        return {
          query: r.sql,
          language: 'sql',
          explanation: parsed.explanation,
          joinNotes: parsed.joinNotes ?? [],
          involvedEntities: r.involvedTables,
          warnings: r.warnings,
        };
      }
      const knownSObjects = new Set(graph.tables.map((t) => t.name.toLowerCase()));
      const knownFields = new Map<string, Set<string>>();
      for (const t of graph.tables) {
        knownFields.set(t.name.toLowerCase(), new Set(t.columns.map((c) => c.name.toLowerCase())));
      }
      const r = this.soqlValidator.validate(parsed.query, {
        rowLimit: req.rowLimit,
        knownSObjects,
        knownFields,
      });
      const involved = r.query.match(/\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b/i)?.[1];
      return {
        query: r.query,
        language: 'soql',
        explanation: parsed.explanation,
        joinNotes: parsed.joinNotes ?? [],
        involvedEntities: involved ? [involved] : [],
        warnings: [],
      };
    }
    if (graph.kind === 'vector') {
      const allowedOps = new Set(['collections', 'count', 'scroll', 'search']);
      const writeOps = new Set(['upsert', 'delete', 'create', 'recreate', 'set', 'update']);
      const collections = new Set(graph.collections.map((c) => c.name));
      let envelope: { op?: unknown; collection?: unknown };
      try {
        envelope = JSON.parse(parsed.query) as { op?: unknown; collection?: unknown };
      } catch (err) {
        throw new UnsafeSqlError(
          `Qdrant query must be a JSON envelope string: ${(err as Error).message}`,
        );
      }
      const opName = typeof envelope.op === 'string' ? envelope.op : '';
      if (!opName) throw new UnsafeSqlError('Qdrant envelope missing "op".');
      if (writeOps.has(opName.toLowerCase())) {
        throw new UnsafeSqlError(`Mutating Qdrant op '${opName}' is blocked.`);
      }
      if (!allowedOps.has(opName)) {
        throw new UnsafeSqlError(`Unsupported Qdrant op '${opName}'.`);
      }
      const involved: string[] = [];
      if (opName !== 'collections') {
        const collection = typeof envelope.collection === 'string' ? envelope.collection : '';
        if (!collection) throw new UnsafeSqlError(`Qdrant op '${opName}' missing "collection".`);
        if (!collections.has(collection)) {
          throw new UnsafeSqlError(`Unknown collection '${collection}'.`);
        }
        involved.push(collection);
      }
      return {
        query: parsed.query,
        language: 'qdrant',
        explanation: parsed.explanation,
        joinNotes: parsed.joinNotes ?? [],
        involvedEntities: involved,
        warnings: [],
      };
    }
    if (graph.kind === 'graph' && isGraphDialect(graph.dialect)) {
      const r = this.cypherValidator.validate(parsed.query, {
        schema: graph,
        rowLimit: req.rowLimit,
        allowWrites: req.allowDml,
      });
      return {
        query: r.query,
        language: 'cypher',
        explanation: parsed.explanation,
        joinNotes: parsed.joinNotes ?? [],
        involvedEntities: r.involvedLabels,
        warnings: r.warnings,
      };
    }
    throw new Error(`Schema kind '${graph.kind}' incompatible with dialect '${graph.dialect}'.`);
  }
}

function truncateOneLine(s: string, max: number): string {
  const flat = s.replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max)}…` : flat;
}

/**
 * For each unknown column reference like `T1.MediaTypeId` or bare `MediaTypeId`,
 * list the real tables that actually have a column with that bare name. Helps
 * the retry LLM fix wrong alias mappings (model often hallucinates which
 * table an alias points to).
 */
function buildColumnLocationMap(
  unknown: string[],
  graph: Extract<UnifiedSchema, { kind: 'relational' }>,
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const u of unknown) {
    const bare = u.includes('.') ? (u.split('.').pop() ?? '') : u;
    if (!bare) continue;
    const lower = bare.toLowerCase();
    const owners = graph.tables
      .filter((t) => t.columns.some((c) => c.name.toLowerCase() === lower))
      .map((t) => t.id);
    if (owners.length > 0) out[bare] = owners;
  }
  return out;
}

function buildColumnLocationHint(
  unknown: string[],
  graph: Extract<UnifiedSchema, { kind: 'relational' }>,
): string {
  const map = buildColumnLocationMap(unknown, graph);
  const lines = Object.entries(map).map(
    ([col, owners]) => `Column '${col}' exists on: ${owners.join(', ')}.`,
  );
  return lines.length > 0 ? ` ${lines.join(' ')} Pick the correct table/alias.` : '';
}

function collectKnownEntities(graph: UnifiedSchema): string[] {
  if (graph.kind === 'relational') {
    // Salesforce Data Cloud has no schema namespace — surface bare entity
    // names so the LLM never sees (and never copies) the `data_cloud.` prefix.
    if (graph.dialect === 'salesforce-data-cloud') {
      return graph.tables.map((t) => t.name);
    }
    return graph.tables.map((t) => t.id);
  }
  if (graph.kind === 'graph') {
    return graph.labels.map((l) => l.label);
  }
  if (graph.kind === 'vector') {
    return graph.collections.map((c) => c.name);
  }
  if (graph.kind === 'keyvalue') {
    return graph.namespaces.map((n) => n.pattern);
  }
  if (graph.kind === 'search') {
    return graph.indices.map((i) => i.name);
  }
  return graph.collections.map((c) => c.name);
}

function extractUnknownEntities(message: string): string[] {
  const out = new Set<string>();
  for (const re of [
    UNKNOWN_TABLE_RE,
    UNKNOWN_COLUMN_RE,
    UNKNOWN_LABEL_RE,
    UNKNOWN_SOBJECT_RE,
    UNKNOWN_FIELD_RE,
  ]) {
    const matches = message.matchAll(re);
    for (const m of matches) {
      if (m[1]) out.add(m[1]);
    }
  }
  return [...out];
}

function formatSuggestions(suggestions: Record<string, string[]>, available: string[]): string {
  const parts: string[] = [];
  const entries = Object.entries(suggestions);
  if (entries.length > 0) {
    const lines = entries.map(
      ([k, v]) => `'${k}' → did you mean ${v.map((x) => `'${x}'`).join(', ')}?`,
    );
    parts.push(`Suggestions: ${lines.join(' ')}`);
  }
  parts.push(`Available entities: [${available.join(', ')}].`);
  return parts.join(' ');
}

function parseJsonResponse(text: string): LlmJson {
  const stripped = text
    .trim()
    .replace(/^```json\s*/i, '')
    .replace(/^```\s*/i, '')
    .replace(/```\s*$/i, '');
  const start = stripped.indexOf('{');
  const end = stripped.lastIndexOf('}');
  if (start < 0 || end < start) throw new Error('No JSON object found.');
  const slice = stripped.slice(start, end + 1);
  const obj = JSON.parse(slice) as Partial<LlmJson> & { sql?: string };
  const query = obj.query ?? obj.sql;
  if (typeof query !== 'string' || !query.trim()) throw new Error('Missing query field.');
  const lang: QueryLanguage =
    obj.language === 'cypher' ? 'cypher' : obj.language === 'qdrant' ? 'qdrant' : 'sql';
  return {
    query,
    language: lang,
    explanation: typeof obj.explanation === 'string' ? obj.explanation : '',
    joinNotes: Array.isArray(obj.joinNotes)
      ? obj.joinNotes.filter((x) => typeof x === 'string')
      : [],
    involvedEntities: Array.isArray(obj.involvedEntities)
      ? obj.involvedEntities.filter((x) => typeof x === 'string')
      : [],
  };
}
