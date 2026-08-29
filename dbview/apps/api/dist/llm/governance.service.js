var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Injectable, Logger } from '@nestjs/common';
import { LlmProviderSchema, isRemoteLlmProvider, } from '@dbview/shared';
import { currentGovernance } from '../common/request-context.js';
import { LlmCredentialsService } from './credentials.service.js';
import { defaultExplainModel, defaultModelFor, } from '../nl2sql/llm/factory.js';
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
let LlmGovernanceService = class LlmGovernanceService {
    credentials;
    logger = new Logger('LlmGovernanceService');
    constructor(credentials) {
        this.credentials = credentials;
    }
    /**
     * The pin in effect for *scope*: the live per-request value wins; absent it,
     * the spawn-time env. `provider: undefined` when ungoverned.
     */
    enforced(scope) {
        const live = scope === 'translate' ? currentGovernance()?.translate : currentGovernance()?.explain;
        if (live)
            return { provider: live.provider, model: live.model };
        return { provider: this.envProvider(scope), model: undefined };
    }
    envProvider(scope) {
        const raw = scope === 'translate'
            ? process.env.DBVIEW_LLM_ENFORCED_NL2SQL
            : process.env.DBVIEW_LLM_ENFORCED_EXPLAIN;
        if (!raw)
            return undefined;
        const parsed = LlmProviderSchema.safeParse(raw.trim());
        if (!parsed.success) {
            this.logger.warn(`ignoring invalid enforced provider for ${scope}: ${raw}`);
            return undefined;
        }
        return parsed.data;
    }
    /** Governance state for the SPA to hide/lock the LLM controls. */
    state() {
        const translate = this.enforced('translate').provider;
        const explain = this.enforced('explain').provider;
        return {
            enforced: translate !== undefined || explain !== undefined,
            translate: { enforced: translate !== undefined, provider: translate ?? null },
            explain: { enforced: explain !== undefined, provider: explain ?? null },
        };
    }
    /**
     * Effective provider/model/auth for the NL→Query pipeline. Enforced: the
     * pinned provider, its governed model (the live pin's model, else the
     * provider default, ignoring the request's model) and the central credential.
     */
    resolveTranslate(requested, requestedModel, kind, principal) {
        const pin = this.enforced('translate');
        const provider = pin.provider ?? requested;
        const model = pin.provider
            ? (pin.model ?? defaultModelFor(provider, kind))
            : (requestedModel ?? defaultModelFor(provider, kind));
        return {
            provider,
            model,
            auth: this.resolveAuth(provider, principal, pin.provider !== undefined),
        };
    }
    /**
     * Effective provider/model/auth for the explain/summarize pipeline. Enforced
     * on its own scope, independent of the translate scope.
     */
    resolveExplain(requested, principal) {
        const pin = this.enforced('explain');
        const provider = pin.provider ?? requested;
        const model = pin.model ?? defaultExplainModel(provider);
        return {
            provider,
            model,
            auth: this.resolveAuth(provider, principal, pin.provider !== undefined),
        };
    }
    /**
     * Adapter auth. Ollama needs none. A governed scope forces the central
     * credential: the live key the proxy forwarded, else `{}` so the SDK falls
     * back to the governed `*_API_KEY` spawn env — never the per-user BYOK key.
     * Ungoverned → the per-user BYOK key (env fallback preserved).
     */
    resolveAuth(provider, principal, enforced) {
        if (!isRemoteLlmProvider(provider))
            return {};
        if (enforced) {
            const gov = currentGovernance();
            const key = provider === 'openai' ? gov?.openaiKey : gov?.anthropicKey;
            return key ? { apiKey: key } : {};
        }
        return { apiKey: this.credentials.resolveApiKey(provider, principal) };
    }
};
LlmGovernanceService = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [LlmCredentialsService])
], LlmGovernanceService);
export { LlmGovernanceService };
//# sourceMappingURL=governance.service.js.map