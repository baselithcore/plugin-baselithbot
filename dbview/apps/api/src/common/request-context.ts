import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';
import type { LlmProvider } from '@dbview/shared';

/** A governed LLM scope resolved live from the proxy's per-request headers. */
export interface GovernedScope {
  provider: LlmProvider;
  model?: string;
}

/**
 * The operator's current dbview LLM pin, forwarded per request by the
 * BaselithCore proxy (see `plugins/dbview/llm_governance.py`). Preferred over
 * the spawn-time `DBVIEW_LLM_ENFORCED_*` env so a re-pin propagates live.
 */
export interface GovernanceContext {
  translate?: GovernedScope;
  explain?: GovernedScope;
  openaiKey?: string;
  anthropicKey?: string;
  ollamaBase?: string;
}

export interface RequestContext {
  requestId: string;
  governance?: GovernanceContext;
}

const storage = new AsyncLocalStorage<RequestContext>();

export function runWithContext<T>(ctx: RequestContext, fn: () => T): T {
  return storage.run(ctx, fn);
}

export function currentRequestId(): string | undefined {
  return storage.getStore()?.requestId;
}

/** The live LLM governance for the current request, or `undefined`. */
export function currentGovernance(): GovernanceContext | undefined {
  return storage.getStore()?.governance;
}

export function newRequestId(existing?: string | null): string {
  if (existing && existing.length > 0 && existing.length <= 128) return existing;
  return randomUUID();
}
