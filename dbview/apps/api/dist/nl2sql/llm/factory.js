import { generateObject, generateText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { LlmProviderError } from '@dbview/shared';
import { OllamaAdapter } from './ollama-adapter.js';
import { SqlcoderAdapter } from './sqlcoder-adapter.js';
import { Nl2QueryOutputSchema } from './output-schema.js';
const SQLCODER_FAMILY = /^sqlcoder/i;
/** The AI SDK's usage block, or undefined when the provider reported none. */
function sdkUsage(usage) {
    if (!usage)
        return undefined;
    return {
        promptTokens: usage.promptTokens ?? 0,
        completionTokens: usage.completionTokens ?? 0,
    };
}
const DEFAULT_OLLAMA_MODEL_BY_KIND = {
    sql: process.env.OLLAMA_MODEL_SQL ?? 'sqlcoder:7b',
    graph: process.env.OLLAMA_MODEL_GRAPH ?? 'codellama:7b',
    document: process.env.OLLAMA_MODEL_DOCUMENT ?? 'codellama:7b',
    vector: process.env.OLLAMA_MODEL_VECTOR ?? 'codellama:7b',
    keyvalue: process.env.OLLAMA_MODEL_KEYVALUE ?? 'codellama:7b',
    search: process.env.OLLAMA_MODEL_SEARCH ?? 'codellama:7b',
    saas: process.env.OLLAMA_MODEL_SAAS ?? 'codellama:7b',
};
const DEFAULT_REMOTE_MODEL = {
    openai: process.env.OPENAI_MODEL ?? 'gpt-4o-mini',
    anthropic: process.env.ANTHROPIC_MODEL ?? 'claude-sonnet-4-6',
};
export function defaultModelFor(provider, kind) {
    if (provider === 'ollama')
        return DEFAULT_OLLAMA_MODEL_BY_KIND[kind];
    return DEFAULT_REMOTE_MODEL[provider];
}
/**
 * OpenAI/Anthropic adapter that uses `generateObject` with a Zod schema so
 * the JSON envelope is enforced at the provider rather than parsed best-effort
 * from free-form text. Eliminates the "fenced JSON" / "extra prose" /
 * "missing field" parse-error retries that dominated remote-provider failure
 * modes.
 *
 * Falls back to `generateText` when:
 *   - the provider rejects the schema (older API version, unsupported model)
 *   - `NoObjectGeneratedError` is raised (model emitted invalid JSON despite
 *     the schema — rare but recoverable via the legacy text path + parser)
 *   - the caller explicitly disables structured mode (sql-cipher style chat
 *     adapters used by the explain/summarize flow already get plain text)
 *
 * The fallback returns the raw text so the existing `parseJsonResponse` path
 * can take over; we never silently downgrade quality without surfacing the
 * model output to the validator.
 */
class GenericRemoteAdapter {
    provider;
    resolveModel;
    options;
    name;
    constructor(provider, resolveModel, options = { structured: true }) {
        this.provider = provider;
        this.resolveModel = resolveModel;
        this.options = options;
        this.name = `${provider}-sdk${options.structured ? '' : '-text'}`;
    }
    async complete(input, model) {
        if (this.options.structured) {
            try {
                const res = await generateObject({
                    model: this.resolveModel(model),
                    schema: Nl2QueryOutputSchema,
                    system: input.system,
                    prompt: input.user,
                    temperature: input.temperature ?? 0,
                });
                return { text: JSON.stringify(res.object), model, usage: sdkUsage(res.usage) };
            }
            catch {
                // Fall through to generateText. Reasons we get here:
                //   - NoObjectGeneratedError: model refused to match the schema.
                //   - Network / auth: text path will likely fail too and surface the
                //     real provider error.
                //   - Self-hosted gateway that advertises the OpenAI API but rejects
                //     response_format=json_schema.
                // The legacy `parseJsonResponse` handles fenced/prose JSON, so the
                // text path still produces usable output for cooperative models.
            }
        }
        try {
            const res = await generateText({
                model: this.resolveModel(model),
                system: input.system,
                prompt: input.user,
                temperature: input.temperature ?? 0,
            });
            return { text: res.text, model, usage: sdkUsage(res.usage) };
        }
        catch (err) {
            throw new LlmProviderError(`${this.provider} (${model}) failed: ${err.message}`);
        }
    }
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
export function createLlmAdapter(provider, model, auth = {}) {
    switch (provider) {
        case 'ollama': {
            const baseUrl = resolveOllamaBaseUrl();
            if (SQLCODER_FAMILY.test(model))
                return new SqlcoderAdapter(baseUrl);
            return new OllamaAdapter(baseUrl);
        }
        case 'openai': {
            const openai = createOpenAI({ apiKey: auth.apiKey ?? process.env.OPENAI_API_KEY });
            return new GenericRemoteAdapter('openai', (id) => openai(id));
        }
        case 'anthropic': {
            const anthropic = createAnthropic({ apiKey: auth.apiKey ?? process.env.ANTHROPIC_API_KEY });
            return new GenericRemoteAdapter('anthropic', (id) => anthropic(id));
        }
    }
}
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
export function createChatAdapter(provider, auth = {}) {
    switch (provider) {
        case 'ollama':
            return new OllamaAdapter(resolveOllamaBaseUrl());
        case 'openai': {
            const openai = createOpenAI({ apiKey: auth.apiKey ?? process.env.OPENAI_API_KEY });
            return new GenericRemoteAdapter('openai', (id) => openai(id), { structured: false });
        }
        case 'anthropic': {
            const anthropic = createAnthropic({ apiKey: auth.apiKey ?? process.env.ANTHROPIC_API_KEY });
            return new GenericRemoteAdapter('anthropic', (id) => anthropic(id), { structured: false });
        }
    }
}
const DEFAULT_EXPLAIN_MODEL = {
    ollama: process.env.OLLAMA_MODEL_EXPLAIN ?? 'codellama:7b',
    openai: process.env.OPENAI_MODEL_EXPLAIN ?? 'gpt-4o-mini',
    anthropic: process.env.ANTHROPIC_MODEL_EXPLAIN ?? 'claude-haiku-4-5-20251001',
};
export function defaultExplainModel(provider) {
    return DEFAULT_EXPLAIN_MODEL[provider];
}
function resolveOllamaBaseUrl() {
    return process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434/api';
}
//# sourceMappingURL=factory.js.map