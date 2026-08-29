import { type DialectKind, type LlmGovernanceState, type LlmProvider } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { LlmCredentialsService } from './credentials.service.js';
import { type LlmAdapterAuth } from '../nl2sql/llm/factory.js';
/**
 * Central LLM-governance enforcement for the dbview engine.
 *
 * The operator's pin reaches this service two ways, live-first:
 *
 * 1. **Live** — the BaselithCore proxy resolves the current pin per request and
 *    forwards it as trusted headers, parsed into the request context
 *    (`currentGovernance()`). A re-pin therefore takes effect with no restart.
 * 2. **Spawn env** — `DBVIEW_LLM_ENFORCED_<SCOPE>=<provider>` injected at child
 *    spawn (see `plugins/dbview/llm_governance.py`). Used when a request did not
 *    come through the governing proxy (e.g. direct/service calls).
 *
 * When a scope is enforced, the pinned provider/model and the central
 * credential win over the per-request `provider`/`model` and any per-user BYOK
 * key — and the SPA hides the corresponding LLM controls. Ungoverned (neither
 * source set) → every method is a pass-through, identical to a deployment with
 * no central LLM policy.
 */
export declare class LlmGovernanceService {
    private readonly credentials;
    private readonly logger;
    constructor(credentials: LlmCredentialsService);
    /**
     * The pin in effect for *scope*: the live per-request value wins; absent it,
     * the spawn-time env. `provider: undefined` when ungoverned.
     */
    private enforced;
    private envProvider;
    /** Governance state for the SPA to hide/lock the LLM controls. */
    state(): LlmGovernanceState;
    /**
     * Effective provider/model/auth for the NL→Query pipeline. Enforced: the
     * pinned provider, its governed model (the live pin's model, else the
     * provider default, ignoring the request's model) and the central credential.
     */
    resolveTranslate(requested: LlmProvider, requestedModel: string | undefined, kind: DialectKind, principal: AuthPrincipal): {
        provider: LlmProvider;
        model: string;
        auth: LlmAdapterAuth;
    };
    /**
     * Effective provider/model/auth for the explain/summarize pipeline. Enforced
     * on its own scope, independent of the translate scope.
     */
    resolveExplain(requested: LlmProvider, principal: AuthPrincipal): {
        provider: LlmProvider;
        model: string;
        auth: LlmAdapterAuth;
    };
    /**
     * Adapter auth. Ollama needs none. A governed scope forces the central
     * credential: the live key the proxy forwarded, else `{}` so the SDK falls
     * back to the governed `*_API_KEY` spawn env — never the per-user BYOK key.
     * Ungoverned → the per-user BYOK key (env fallback preserved).
     */
    private resolveAuth;
}
//# sourceMappingURL=governance.service.d.ts.map