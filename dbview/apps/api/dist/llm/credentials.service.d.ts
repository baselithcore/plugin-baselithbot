import type { LlmCredentialStatus, RemoteLlmProvider } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
/**
 * Per-user encrypted LLM API key storage.
 *
 * Keys are stored ciphered at rest (AES-256-GCM via the shared `DBVIEW_SECRET`),
 * the same pattern used by database connection strings.
 *
 * Resolution order at adapter-build time:
 *   1. Per-user stored key (decrypted on demand, kept in memory only for the
 *      duration of the request).
 *   2. Process env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) — preserved as a
 *      fallback so existing deployments keep working without re-onboarding,
 *      and so the service-to-service synthetic admin (api-key guard) still
 *      authenticates remote providers.
 */
export declare class LlmCredentialsService {
    private readonly logger;
    private readonly store;
    status(provider: RemoteLlmProvider, principal: AuthPrincipal): LlmCredentialStatus;
    upsert(provider: RemoteLlmProvider, apiKey: string, principal: AuthPrincipal): LlmCredentialStatus;
    remove(provider: RemoteLlmProvider, principal: AuthPrincipal): LlmCredentialStatus;
    /**
     * Resolve the API key to use for an outgoing request. Per-user stored key
     * wins over env. Returns `undefined` when neither is configured — callers
     * must handle the "no key" case so the SDK doesn't silently send unauth'd
     * requests that fail with a generic 401.
     */
    resolveApiKey(provider: RemoteLlmProvider, principal: AuthPrincipal): string | undefined;
}
//# sourceMappingURL=credentials.service.d.ts.map