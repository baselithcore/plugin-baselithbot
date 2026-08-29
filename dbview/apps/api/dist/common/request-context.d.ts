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
export declare function runWithContext<T>(ctx: RequestContext, fn: () => T): T;
export declare function currentRequestId(): string | undefined;
/** The live LLM governance for the current request, or `undefined`. */
export declare function currentGovernance(): GovernanceContext | undefined;
export declare function newRequestId(existing?: string | null): string;
//# sourceMappingURL=request-context.d.ts.map