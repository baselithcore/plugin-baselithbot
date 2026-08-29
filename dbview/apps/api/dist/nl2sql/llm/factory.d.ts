import { type DialectKind, type LlmProvider } from '@dbview/shared';
import type { LlmAdapter } from './provider.js';
export declare function defaultModelFor(provider: LlmProvider, kind: DialectKind): string;
/**
 * Caller-supplied authentication context for adapter construction.
 *
 * `apiKey` is resolved upstream (per-user stored credential ▶ env fallback)
 * by `LlmCredentialsService`. When undefined and the provider needs a key,
 * the SDK will surface the provider's own "missing API key" error on the
 * first call; we don't pre-flight check here because Ollama does not need
 * one and a unified call path keeps the factory provider-agnostic.
 */
export interface LlmAdapterAuth {
    apiKey?: string;
}
/**
 * Resolve the adapter best suited for a (provider, model) pair.
 *
 * Routing rules:
 *   - provider=ollama + model matches sqlcoder family → SqlcoderAdapter (raw completion).
 *   - provider=ollama otherwise → OllamaAdapter (chat + JSON output).
 *   - provider=openai/anthropic → AI SDK generic adapter.
 *
 * The Ollama endpoint is read from `OLLAMA_BASE_URL` (deployment-level
 * configuration) and is not overridable per-request.
 *
 * `auth.apiKey` is consulted only for openai/anthropic. When omitted, the
 * underlying SDK falls back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` so
 * service-to-service callers without a per-user credential keep working.
 */
export declare function createLlmAdapter(provider: LlmProvider, model: string, auth?: LlmAdapterAuth): LlmAdapter;
/**
 * Pick a chat-tuned adapter for downstream tasks (explanation, summarization)
 * regardless of which model generated the query. Always returns a JSON-capable
 * chat adapter — never the raw-completion sqlcoder adapter.
 *
 * Structured output is intentionally OFF here: explain/summarize call sites
 * have their own JSON shapes (different fields per task) and parse the result
 * with their own lenient parsers. Forcing the Nl2QueryOutput schema would
 * reject every valid explanation/summary.
 */
export declare function createChatAdapter(provider: LlmProvider, auth?: LlmAdapterAuth): LlmAdapter;
export declare function defaultExplainModel(provider: LlmProvider): string;
//# sourceMappingURL=factory.d.ts.map