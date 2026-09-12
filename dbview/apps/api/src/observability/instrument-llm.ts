import { llmCallLatency, llmCalls } from './metrics.registry.js';
import { recordLlmUsage } from './llm-usage.store.js';
import type {
  LlmAdapter,
  LlmCompletionInput,
  LlmCompletionResult,
} from '../nl2sql/llm/provider.js';

export type LlmMode = 'translate' | 'ask' | 'explain' | 'summarize';

export function instrumentLlmAdapter(adapter: LlmAdapter, mode: LlmMode): LlmAdapter {
  return {
    provider: adapter.provider,
    name: adapter.name,
    async complete(input: LlmCompletionInput, model: string): Promise<LlmCompletionResult> {
      const start = process.hrtime.bigint();
      const labels = { provider: adapter.provider, model, mode };
      try {
        const res = await adapter.complete(input, model);
        const seconds = Number(process.hrtime.bigint() - start) / 1e9;
        llmCallLatency.labels(labels).observe(seconds);
        llmCalls.labels({ ...labels, status: 'ok' }).inc();
        // Also hand the provider-reported tokens to the per-request
        // accumulator: the gateway reads them off the response and files the
        // spend against this plugin in the host's cost ledger.
        recordLlmUsage(res.model || model, res.usage);
        return res;
      } catch (err) {
        const seconds = Number(process.hrtime.bigint() - start) / 1e9;
        llmCallLatency.labels(labels).observe(seconds);
        llmCalls.labels({ ...labels, status: 'error' }).inc();
        throw err;
      }
    },
  };
}
