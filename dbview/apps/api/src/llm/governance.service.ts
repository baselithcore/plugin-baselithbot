import { Injectable, Logger } from '@nestjs/common';
import {
  LlmProviderSchema,
  isRemoteLlmProvider,
  type DialectKind,
  type LlmGovernanceState,
  type LlmProvider,
} from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { currentGovernance } from '../common/request-context.js';
import { LlmCredentialsService } from './credentials.service.js';
import {
  defaultExplainModel,
  defaultModelFor,
  type LlmAdapterAuth,
} from '../nl2sql/llm/factory.js';

type Scope = 'translate' | 'explain';

interface EnforcedScope {
  /** Pinned provider, or `undefined` when the scope is ungoverned. */
  provider: LlmProvider | undefined;
  /** Pinned model (live pins only), or `undefined` to use the default model. */
  model: string | undefined;
}

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
@Injectable()
export class LlmGovernanceService {
  private readonly logger = new Logger('LlmGovernanceService');

  constructor(private readonly credentials: LlmCredentialsService) {}

  /**
   * The pin in effect for *scope*: the live per-request value wins; absent it,
   * the spawn-time env. `provider: undefined` when ungoverned.
   */
  private enforced(scope: Scope): EnforcedScope {
    const live =
      scope === 'translate' ? currentGovernance()?.translate : currentGovernance()?.explain;
    if (live) return { provider: live.provider, model: live.model };
    return { provider: this.envProvider(scope), model: undefined };
  }

  private envProvider(scope: Scope): LlmProvider | undefined {
    const raw =
      scope === 'translate'
        ? process.env.DBVIEW_LLM_ENFORCED_NL2SQL
        : process.env.DBVIEW_LLM_ENFORCED_EXPLAIN;
    if (!raw) return undefined;
    const parsed = LlmProviderSchema.safeParse(raw.trim());
    if (!parsed.success) {
      this.logger.warn(`ignoring invalid enforced provider for ${scope}: ${raw}`);
      return undefined;
    }
    return parsed.data;
  }

  /** Governance state for the SPA to hide/lock the LLM controls. */
  state(): LlmGovernanceState {
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
  resolveTranslate(
    requested: LlmProvider,
    requestedModel: string | undefined,
    kind: DialectKind,
    principal: AuthPrincipal
  ): { provider: LlmProvider; model: string; auth: LlmAdapterAuth } {
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
  resolveExplain(
    requested: LlmProvider,
    principal: AuthPrincipal
  ): { provider: LlmProvider; model: string; auth: LlmAdapterAuth } {
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
  private resolveAuth(
    provider: LlmProvider,
    principal: AuthPrincipal,
    enforced: boolean
  ): LlmAdapterAuth {
    if (!isRemoteLlmProvider(provider)) return {};
    if (enforced) {
      const gov = currentGovernance();
      const key = provider === 'openai' ? gov?.openaiKey : gov?.anthropicKey;
      return key ? { apiKey: key } : {};
    }
    return { apiKey: this.credentials.resolveApiKey(provider, principal) };
  }
}
