import type { LlmUsage } from '../nl2sql/llm/provider.js';
/**
 * Per-request LLM token accounting, reported back to the gateway.
 *
 * The engine runs as a child process, so the host it is proxied from cannot see
 * the tokens it spends: the host's per-plugin cost ledger only learns about a
 * call if the child says so. This store accumulates what each request's
 * providers reported and the interceptor stamps it on the response as
 * `x-dbview-llm-usage`, which the gateway attributes to the caller that is
 * still in-flight (plugin + user), then forwards to the framework's token seam.
 *
 * Measured counts only: a provider that reports no usage contributes nothing
 * rather than an estimate.
 */
export declare const USAGE_HEADER = "x-dbview-llm-usage";
/** One `(model, promptTokens, completionTokens)` row per completion. */
export interface UsageRow extends LlmUsage {
    model: string;
}
/** Run `fn` with a fresh per-request accumulator bound to its async context. */
export declare function withUsageCapture<T>(rows: UsageRow[], fn: () => T): T;
/** Record one completion's usage against the in-flight request (no-op outside one). */
export declare function recordLlmUsage(model: string, usage: LlmUsage | undefined): void;
/**
 * Serialize rows for the response header: `model;prompt;completion` entries
 * joined by `,`. Compact and header-safe — the model id is sanitized of the
 * separators and of anything outside the token charset a header allows.
 */
export declare function serializeUsage(rows: readonly UsageRow[]): string;
//# sourceMappingURL=llm-usage.store.d.ts.map