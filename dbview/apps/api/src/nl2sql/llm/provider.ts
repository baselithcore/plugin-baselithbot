import type { Dialect, LlmProvider, Nl2ConversationTurn, UnifiedSchema } from '@dbview/shared';

/**
 * Structured request context. Adapters that need raw schema/user prompt
 * (e.g. sqlcoder, which uses a model-specific completion template instead
 * of chat + JSON output) read from `structured`. Adapters that operate on
 * pre-rendered chat prompts use `system` and `user`.
 */
export interface LlmCompletionInput {
  system: string;
  user: string;
  temperature?: number;
  structured?: StructuredContext;
}

export interface StructuredContext {
  schema: UnifiedSchema;
  dialect: Dialect;
  userPrompt: string;
  allowDml: boolean;
  rowLimit: number;
  retryFeedback?: string;
  history?: readonly Nl2ConversationTurn[];
}

/**
 * Adapter output. `text` MUST be a JSON string conforming to the
 * `LlmJson` shape consumed by Nl2SqlService.parseJsonResponse.
 * Adapters that emit raw SQL (sqlcoder) wrap it in synthetic JSON.
 */
export interface LlmCompletionResult {
  text: string;
  model: string;
}

export interface LlmAdapter {
  readonly provider: LlmProvider;
  /** Optional human-readable name surfaced in logs/telemetry. */
  readonly name?: string;
  complete(input: LlmCompletionInput, model: string): Promise<LlmCompletionResult>;
}
