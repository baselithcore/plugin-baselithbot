import { type RemoteLlmProvider, type RemoteModel } from '@dbview/shared';
/**
 * Talks directly to the provider's REST API to:
 *   - list available models (so the UI can filter to models the caller's
 *     account can actually invoke, rather than a hard-coded allowlist that
 *     ages out as providers release new models)
 *   - validate an API key in a single round-trip
 *
 * We intentionally use the raw REST endpoints rather than going through the
 * `ai` SDK: the SDK is shaped around generation, not metadata listing, and
 * the model-list endpoints are stable and trivial to hit directly.
 */
export declare class RemoteProviderService {
    private readonly logger;
    listModels(provider: RemoteLlmProvider, apiKey: string): Promise<RemoteModel[]>;
    /**
     * Probe the provider with the supplied key. Reuses the model-list endpoint
     * because it is the cheapest authenticated GET available on both providers
     * (no token cost, no usage quota impact).
     */
    test(provider: RemoteLlmProvider, apiKey: string): Promise<{
        modelCount: number;
        latencyMs: number;
    }>;
    private listOpenAi;
    private listAnthropic;
    private fetchJson;
}
//# sourceMappingURL=remote-provider.service.d.ts.map