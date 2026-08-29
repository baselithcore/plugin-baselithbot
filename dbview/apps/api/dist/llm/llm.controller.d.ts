import { type LlmCredentialStatus, type LlmGovernanceState, type OllamaModelsResponse, type RemoteModelsResponse, type TestLlmCredentialResponse } from '@dbview/shared';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { OllamaService } from './ollama.service.js';
import { LlmCredentialsService } from './credentials.service.js';
import { RemoteProviderService } from './remote-provider.service.js';
import { LlmGovernanceService } from './governance.service.js';
export declare class LlmController {
    private readonly ollama;
    private readonly credentials;
    private readonly remote;
    private readonly governance;
    constructor(ollama: OllamaService, credentials: LlmCredentialsService, remote: RemoteProviderService, governance: LlmGovernanceService);
    /**
     * Central LLM-governance state. When a scope is enforced (operator pinned
     * the provider from the auth console), the SPA hides the matching per-user
     * LLM controls — the pin already wins server-side regardless.
     */
    governanceState(): LlmGovernanceState;
    listOllama(): Promise<OllamaModelsResponse>;
    getCredential(providerRaw: string, principal: AuthPrincipal): LlmCredentialStatus;
    setCredential(providerRaw: string, body: {
        apiKey: string;
    }, principal: AuthPrincipal): LlmCredentialStatus;
    deleteCredential(providerRaw: string, principal: AuthPrincipal): LlmCredentialStatus;
    /**
     * Validate a provider key.
     *
     * The body's `apiKey` (when supplied) takes precedence over any stored
     * credential — this lets the UI test a fresh key before persisting it, so
     * users get immediate feedback ("invalid key") without first overwriting
     * a known-good stored value with a typo.
     */
    testCredential(providerRaw: string, body: {
        apiKey?: string;
    }, principal: AuthPrincipal): Promise<TestLlmCredentialResponse>;
    /**
     * List models the calling user's key has access to. Falls back to env key
     * for service-to-service callers. Errors propagate so the UI can surface
     * "invalid key" / "rate limited" / "network" distinctly.
     */
    listRemoteModels(providerRaw: string, principal: AuthPrincipal): Promise<RemoteModelsResponse>;
}
//# sourceMappingURL=llm.controller.d.ts.map