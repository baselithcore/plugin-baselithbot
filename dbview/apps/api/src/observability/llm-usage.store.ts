import { AsyncLocalStorage } from 'node:async_hooks';
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
export const USAGE_HEADER = 'x-dbview-llm-usage';

/** One `(model, promptTokens, completionTokens)` row per completion. */
export interface UsageRow extends LlmUsage {
  model: string;
}

const storage = new AsyncLocalStorage<UsageRow[]>();

/** Run `fn` with a fresh per-request accumulator bound to its async context. */
export function withUsageCapture<T>(rows: UsageRow[], fn: () => T): T {
  return storage.run(rows, fn);
}

/** Record one completion's usage against the in-flight request (no-op outside one). */
export function recordLlmUsage(model: string, usage: LlmUsage | undefined): void {
  if (!usage) return;
  const promptTokens = Math.max(usage.promptTokens ?? 0, 0);
  const completionTokens = Math.max(usage.completionTokens ?? 0, 0);
  if (promptTokens === 0 && completionTokens === 0) return;
  storage.getStore()?.push({ model, promptTokens, completionTokens });
}

/**
 * Serialize rows for the response header: `model;prompt;completion` entries
 * joined by `,`. Compact and header-safe — the model id is sanitized of the
 * separators and of anything outside the token charset a header allows.
 */
export function serializeUsage(rows: readonly UsageRow[]): string {
  return rows
    .filter((row) => row.promptTokens > 0 || row.completionTokens > 0)
    .map(
      (row) =>
        `${sanitizeModel(row.model)};${Math.trunc(row.promptTokens)};${Math.trunc(row.completionTokens)}`
    )
    .join(',');
}

function sanitizeModel(model: string): string {
  const cleaned = (model || 'unknown').replace(/[^A-Za-z0-9._:@/-]/g, '');
  return cleaned.slice(0, 120) || 'unknown';
}
