import type { LlmAdapter, LlmCompletionInput, LlmCompletionResult } from './provider.js';
/**
 * Direct Ollama adapter using `/api/chat`. Avoids `ollama-ai-provider` package
 * which has parser issues with recent Ollama response formats.
 */
export declare class OllamaAdapter implements LlmAdapter {
    private readonly baseUrl;
    readonly provider: "ollama";
    constructor(baseUrl: string);
    complete(input: LlmCompletionInput, model: string): Promise<LlmCompletionResult>;
}
//# sourceMappingURL=ollama-adapter.d.ts.map