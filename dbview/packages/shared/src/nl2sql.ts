import { z } from 'zod';
import { DialectSchema } from './dialect.js';

export const LlmProviderSchema = z.enum(['ollama', 'openai', 'anthropic']);
export type LlmProvider = z.infer<typeof LlmProviderSchema>;

/**
 * Providers that authenticate via a per-user API key managed through the
 * settings UI. Ollama is excluded — it is a deployment-level resource
 * configured via `OLLAMA_BASE_URL` and shared across all users.
 */
export const RemoteLlmProviderSchema = z.enum(['openai', 'anthropic']);
export type RemoteLlmProvider = z.infer<typeof RemoteLlmProviderSchema>;

export function isRemoteLlmProvider(p: LlmProvider): p is RemoteLlmProvider {
  return p === 'openai' || p === 'anthropic';
}

/**
 * Models known to be unusable for query generation in any pipeline.
 * Embedding models output vectors and have no chat or completion path.
 *
 * Note: sqlcoder is NOT here. It IS a raw-completion model (no chat / no JSON),
 * but it is supported via a dedicated adapter that calls Ollama's /api/generate
 * and wraps the raw SQL output in synthetic JSON. See SqlcoderAdapter.
 */
const INCOMPATIBLE_OLLAMA_MODELS = /^(nomic-embed|all-minilm|mxbai-embed)/i;

export function isIncompatibleOllamaModel(name: string): boolean {
  return INCOMPATIBLE_OLLAMA_MODELS.test(name);
}

/**
 * Models that require the dedicated raw-completion sqlcoder adapter
 * (relational schemas only, /api/generate endpoint).
 */
const SQLCODER_FAMILY = /^sqlcoder/i;
export function isSqlcoderModel(name: string): boolean {
  return SQLCODER_FAMILY.test(name);
}

/**
 * Coding-tuned Ollama models suitable for NL2Query.
 *
 * Heuristic: name matches a known code-LLM family. Embedding and pure
 * chat-only models are excluded so the picker only surfaces models that
 * can generate SQL/Cypher/Qdrant DSL with acceptable quality.
 */
const CODING_OLLAMA_MODELS =
  /(^|[-_/:])(sqlcoder|codellama|deepseek-?coder|codegemma|starcoder|codestral|granite-?code|phind-codellama|qwen[\d.]*-?coder|magicoder|wizardcoder|opencodeinterpreter|coder|code-)/i;

export function isCodingOllamaModel(name: string): boolean {
  if (isIncompatibleOllamaModel(name)) return false;
  return CODING_OLLAMA_MODELS.test(name);
}

export const QueryLanguageSchema = z.enum(['sql', 'cypher', 'qdrant', 'soql']);
export type QueryLanguage = z.infer<typeof QueryLanguageSchema>;

/**
 * Natural-language locale used for assistant prose (summary + explanation).
 * The generated query itself is always SQL/Cypher/Qdrant — locale only
 * affects the user-visible narrative.
 */
export const ResponseLocaleSchema = z.enum(['en', 'it']);
export type ResponseLocale = z.infer<typeof ResponseLocaleSchema>;

/**
 * Compact record of a prior conversation turn, replayed back to the LLM so
 * follow-up prompts can resolve anaphora ("now group by month", "only Italy",
 * "the previous one"). Only metadata is sent — never the result rows — to
 * keep the prompt budget bounded and avoid leaking row content into the model.
 */
export const Nl2ConversationTurnSchema = z.object({
  prompt: z.string().min(1).max(2000),
  query: z.string().max(8000).optional(),
  language: QueryLanguageSchema.optional(),
  rowCount: z.number().int().nonnegative().nullable().optional(),
  ok: z.boolean().optional(),
});
export type Nl2ConversationTurn = z.infer<typeof Nl2ConversationTurnSchema>;

/** Max prior turns accepted per request — cap is a hard prompt-budget guard. */
export const NL2_HISTORY_MAX_TURNS = 6;

export const Nl2SqlRequestSchema = z.object({
  connectionId: z.string().uuid(),
  prompt: z.string().min(3).max(2000),
  provider: LlmProviderSchema.default('ollama'),
  model: z.string().optional(),
  allowDml: z.boolean().default(false),
  rowLimit: z.number().int().positive().max(10_000).default(100),
  locale: ResponseLocaleSchema.default('en'),
  history: z.array(Nl2ConversationTurnSchema).max(NL2_HISTORY_MAX_TURNS).default([]),
});
export type Nl2SqlRequest = z.infer<typeof Nl2SqlRequestSchema>;

export const OllamaModelSchema = z.object({
  name: z.string(),
  size: z.number().int().nonnegative().optional(),
  digest: z.string().optional(),
  modifiedAt: z.string().optional(),
  family: z.string().optional(),
  parameterSize: z.string().optional(),
});
export type OllamaModel = z.infer<typeof OllamaModelSchema>;

export const OllamaModelsResponseSchema = z.object({
  baseUrl: z.string(),
  models: z.array(OllamaModelSchema),
});
export type OllamaModelsResponse = z.infer<typeof OllamaModelsResponseSchema>;

/**
 * Remote-provider model descriptor surfaced to the UI. Only the `id` is
 * required — extra fields are best-effort metadata for grouping/sorting.
 */
export const RemoteModelSchema = z.object({
  id: z.string(),
  displayName: z.string().optional(),
  family: z.string().optional(),
  /** ISO-8601 timestamp from the provider when available. */
  createdAt: z.string().optional(),
  contextWindow: z.number().int().positive().optional(),
});
export type RemoteModel = z.infer<typeof RemoteModelSchema>;

export const RemoteModelsResponseSchema = z.object({
  provider: RemoteLlmProviderSchema,
  models: z.array(RemoteModelSchema),
  /** Source of the key used to fetch: 'stored' (per-user) or 'env' fallback. */
  source: z.enum(['stored', 'env']),
});
export type RemoteModelsResponse = z.infer<typeof RemoteModelsResponseSchema>;

/**
 * Status payload for `GET /api/llm/providers/:provider/credential`.
 * Plaintext is never returned. `maskedTail` shows the last 4 chars so
 * the user can recognize which key is stored without exposing the secret.
 */
export const LlmCredentialStatusSchema = z.object({
  provider: RemoteLlmProviderSchema,
  hasKey: z.boolean(),
  /** True when the resolved key comes from `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. */
  envFallback: z.boolean(),
  maskedTail: z.string().optional(),
  updatedAt: z.string().optional(),
});
export type LlmCredentialStatus = z.infer<typeof LlmCredentialStatusSchema>;

/**
 * Central LLM-governance state for one pipeline scope.
 *
 * When the BaselithCore host operator pins this plugin's LLM provider/model
 * from the central auth console, the pin is *enforced*: it overrides the
 * per-request provider/model and any per-user BYOK credential, and the UI
 * hides the corresponding controls. `enforced=false` means the scope is
 * ungoverned and the user's own choices apply (default behaviour).
 */
export const LlmGovernanceScopeSchema = z.object({
  enforced: z.boolean(),
  /** The provider the pin forces, or `null` when not enforced. */
  provider: LlmProviderSchema.nullable(),
});
export type LlmGovernanceScope = z.infer<typeof LlmGovernanceScopeSchema>;

/** Response for `GET /api/llm/governance`. */
export const LlmGovernanceStateSchema = z.object({
  /** True when any pipeline scope is centrally enforced. */
  enforced: z.boolean(),
  /** NL→Query translation pipeline. */
  translate: LlmGovernanceScopeSchema,
  /** Explain/summarize pipeline. */
  explain: LlmGovernanceScopeSchema,
});
export type LlmGovernanceState = z.infer<typeof LlmGovernanceStateSchema>;

/** Body for `PUT /api/llm/providers/:provider/credential`. */
export const SetLlmCredentialSchema = z.object({
  apiKey: z.string().min(8).max(512),
});
export type SetLlmCredentialRequest = z.infer<typeof SetLlmCredentialSchema>;

/**
 * Body for `POST /api/llm/providers/:provider/test`.
 * When `apiKey` is omitted, the server uses the stored credential (or env
 * fallback). This lets the UI test a key *before* saving it.
 */
export const TestLlmCredentialSchema = z.object({
  apiKey: z.string().min(8).max(512).optional(),
});
export type TestLlmCredentialRequest = z.infer<typeof TestLlmCredentialSchema>;

export const TestLlmCredentialResponseSchema = z.object({
  ok: z.literal(true),
  provider: RemoteLlmProviderSchema,
  /** Number of models the provider returned during the probe. */
  modelCount: z.number().int().nonnegative(),
  latencyMs: z.number().nonnegative(),
});
export type TestLlmCredentialResponse = z.infer<typeof TestLlmCredentialResponseSchema>;

export const SafetyWarningSchema = z.object({
  code: z.enum([
    'select_star',
    'missing_limit',
    'unknown_table',
    'unknown_column',
    'unknown_label',
    'dml_blocked',
    'ddl_blocked',
    'ambiguous_join',
    'cypher_write_blocked',
  ]),
  message: z.string(),
  severity: z.enum(['info', 'warn', 'error']),
});
export type SafetyWarning = z.infer<typeof SafetyWarningSchema>;

export const Nl2SqlResponseSchema = z.object({
  query: z.string(),
  language: QueryLanguageSchema,
  dialect: DialectSchema,
  explanation: z.string(),
  joinNotes: z.array(z.string()),
  involvedEntities: z.array(z.string()),
  warnings: z.array(SafetyWarningSchema),
  retries: z.number().int().nonnegative(),
  provider: LlmProviderSchema,
  model: z.string(),
});
export type Nl2SqlResponse = z.infer<typeof Nl2SqlResponseSchema>;

export const ExecuteQueryRequestSchema = z.object({
  connectionId: z.string().uuid(),
  query: z.string().min(1),
  rowLimit: z.number().int().positive().max(10_000).default(100),
});
export type ExecuteQueryRequest = z.infer<typeof ExecuteQueryRequestSchema>;

export const ExecuteQueryResponseSchema = z.object({
  columns: z.array(z.string()),
  rows: z.array(z.array(z.unknown())),
  rowCount: z.number().int().nonnegative(),
  durationMs: z.number().nonnegative(),
  truncated: z.boolean(),
});
export type ExecuteQueryResponse = z.infer<typeof ExecuteQueryResponseSchema>;

export const SampleRequestSchema = z.object({
  connectionId: z.string().uuid(),
  tableId: z.string().min(1).max(256),
  rowLimit: z.number().int().positive().max(1_000).default(20),
});
export type SampleRequest = z.infer<typeof SampleRequestSchema>;

/**
 * "Ask" flow — single-shot pipeline that:
 *   1. Translates the natural-language prompt into a safe query.
 *   2. Executes that query against the connection.
 *   3. Summarizes the resulting rows in plain language.
 *
 * The response always includes the translation. Execution + summary are
 * best-effort: a translated-but-unexecutable query still returns
 * `translation` with `executionError` populated so the UI can surface it
 * without losing the generated query.
 */
export const Nl2QueryAskRequestSchema = z.object({
  connectionId: z.string().uuid(),
  prompt: z.string().min(3).max(2000),
  provider: LlmProviderSchema.default('ollama'),
  model: z.string().optional(),
  rowLimit: z.number().int().positive().max(10_000).default(100),
  locale: ResponseLocaleSchema.default('en'),
  history: z.array(Nl2ConversationTurnSchema).max(NL2_HISTORY_MAX_TURNS).default([]),
});
export type Nl2QueryAskRequest = z.infer<typeof Nl2QueryAskRequestSchema>;

export const AskExecutionErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
});
export type AskExecutionError = z.infer<typeof AskExecutionErrorSchema>;

export const Nl2QueryAskResponseSchema = z.object({
  translation: Nl2SqlResponseSchema,
  result: ExecuteQueryResponseSchema.nullable(),
  executionError: AskExecutionErrorSchema.nullable(),
  /** One- to three-sentence headline answer in the user's locale. */
  summary: z.string(),
  /**
   * Optional bullets that pull concrete values from the rows ("Acme: $1.2M",
   * "TopCo: $980k"). Rendered in the chat bubble below the summary so the
   * conversation reads as a natural, data-grounded reply rather than just
   * "see the table below".
   */
  highlights: z.array(z.string()).default([]),
  /**
   * Suggested follow-up questions the user might ask next (locale-aware).
   * Rendered as clickable chips that immediately fire a new turn.
   */
  followUps: z.array(z.string()).default([]),
  totalDurationMs: z.number().nonnegative(),
});
export type Nl2QueryAskResponse = z.infer<typeof Nl2QueryAskResponseSchema>;
