import { Injectable, Logger } from '@nestjs/common';
import {
  LlmProviderSchema,
  isRemoteLlmProvider,
  type DialectKind,
  type LlmGovernanceState,
  type LlmProvider,
} from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { LlmCredentialsService } from './credentials.service.js';
import { defaultExplainModel, defaultModelFor, type LlmAdapterAuth } from '../nl2sql/llm/factory.js';

/**
 * Central LLM-governance enforcement for the dbview engine.
 *
 * The BaselithCore host injects `DBVIEW_LLM_ENFORCED_<SCOPE>=<provider>` at
 * child spawn (see `plugins/dbview/llm_governance.py`) when the operator has
 * pinned this plugin's LLM provider/model from the central auth console. When
 * a scope is enforced, the pinned provider/model (and the central credential,
 * carried in `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/`OLLAMA_BASE_URL`) MUST win
 * over the per-request `provider`/`model` and any per-user BYOK credential —
 * and the SPA hides the corresponding LLM controls.
 *
 * Ungoverned (env unset) → every method is a pass-through, so behaviour is
 * identical to a deployment with no central LLM policy.
 */
@Injectable()
export class LlmGovernanceService {
  private readonly logger = new Logger('LlmGovernanceService');

  constructor(private readonly credentials: LlmCredentialsService) {}

  /** The provider a scope is pinned to, or `undefined` when ungoverned. */
  private enforcedProvider(scope: 'translate' | 'explain'): LlmProvider | undefined {
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
    const translate = this.enforcedProvider('translate');
    const explain = this.enforcedProvider('explain');
    return {
      enforced: translate !== undefined || explain !== undefined,
      translate: { enforced: translate !== undefined, provider: translate ?? null },
      explain: { enforced: explain !== undefined, provider: explain ?? null },
    };
  }

  /**
   * Effective provider/model/auth for the NL→Query pipeline. Enforced: the
   * pinned provider, its governed default model (from env, ignoring the
   * request's model) and the central credential (empty auth → SDK reads the
   * governed `*_API_KEY`), never the per-user BYOK key.
   */
  resolveTranslate(
    requested: LlmProvider,
    requestedModel: string | undefined,
    kind: DialectKind,
    principal: AuthPrincipal
  ): { provider: LlmProvider; model: string; auth: LlmAdapterAuth } {
    const pinned = this.enforcedProvider('translate');
    const provider = pinned ?? requested;
    const model = pinned ? defaultModelFor(provider, kind) : (requestedModel ?? defaultModelFor(provider, kind));
    return { provider, model, auth: this.resolveAuth(provider, principal, pinned !== undefined) };
  }

  /**
   * Effective provider/model/auth for the explain/summarize pipeline. Enforced
   * on its own scope, independent of the translate scope.
   */
  resolveExplain(
    requested: LlmProvider,
    principal: AuthPrincipal
  ): { provider: LlmProvider; model: string; auth: LlmAdapterAuth } {
    const pinned = this.enforcedProvider('explain');
    const provider = pinned ?? requested;
    return {
      provider,
      model: defaultExplainModel(provider),
      auth: this.resolveAuth(provider, principal, pinned !== undefined),
    };
  }

  /**
   * Adapter auth: Ollama needs none; a governed scope forces the central
   * credential (empty auth → the SDK falls back to the governed env key),
   * otherwise the per-user BYOK key (env fallback preserved).
   */
  private resolveAuth(
    provider: LlmProvider,
    principal: AuthPrincipal,
    enforced: boolean
  ): LlmAdapterAuth {
    if (!isRemoteLlmProvider(provider)) return {};
    if (enforced) return {};
    return { apiKey: this.credentials.resolveApiKey(provider, principal) };
  }
}
