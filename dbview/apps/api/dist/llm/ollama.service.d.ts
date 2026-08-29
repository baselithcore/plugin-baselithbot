import { type OllamaModel } from '@dbview/shared';
export declare class OllamaService {
    /** Default base URL when none provided. Mirrors LLM adapter default. */
    defaultBaseUrl(): string;
    /**
     * Fetch installed models from the Ollama instance configured via env.
     * The endpoint is intentionally not overridable per request — it is a
     * deployment-level setting (OLLAMA_BASE_URL).
     */
    listModels(): Promise<{
        baseUrl: string;
        models: OllamaModel[];
    }>;
}
//# sourceMappingURL=ollama.service.d.ts.map