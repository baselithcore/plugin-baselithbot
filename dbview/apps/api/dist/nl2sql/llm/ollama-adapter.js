import { LlmProviderError, isIncompatibleOllamaModel } from '@dbview/shared';
/**
 * Direct Ollama adapter using `/api/chat`. Avoids `ollama-ai-provider` package
 * which has parser issues with recent Ollama response formats.
 */
export class OllamaAdapter {
    baseUrl;
    provider = 'ollama';
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    async complete(input, model) {
        if (isIncompatibleOllamaModel(model)) {
            throw new LlmProviderError(`ollama model "${model}" is not chat/JSON-tuned and cannot generate structured queries. Pick a chat-tuned model (e.g. codellama:7b, mistral:latest, llama3.2:latest).`);
        }
        const url = `${normalizeBase(this.baseUrl)}/chat`;
        const body = {
            model,
            stream: false,
            // Force structured JSON output. Ollama constrains the sampler to emit a single
            // JSON value, eliminating "No JSON object found" drift on smaller models.
            format: 'json',
            options: {
                temperature: input.temperature ?? 0,
            },
            messages: [
                { role: 'system', content: input.system },
                { role: 'user', content: input.user },
            ],
        };
        const ctrl = new AbortController();
        const timeout = setTimeout(() => ctrl.abort(), 120_000);
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'content-type': 'application/json' },
                body: JSON.stringify(body),
                signal: ctrl.signal,
            });
            if (!res.ok) {
                const text = await res.text().catch(() => '');
                throw new LlmProviderError(`ollama (${model}) returned ${res.status}: ${text.slice(0, 200) || res.statusText}`);
            }
            const json = (await res.json());
            if (json.error) {
                throw new LlmProviderError(`ollama (${model}) error: ${json.error}`);
            }
            const text = json.message?.content ?? json.response ?? '';
            if (!text) {
                throw new LlmProviderError(`ollama (${model}) returned empty content. The model likely does not support chat/JSON output. Pick a chat-tuned model (e.g. codellama:7b, mistral:latest, llama3.2:latest) in Settings.`);
            }
            return { text, model };
        }
        catch (err) {
            if (err instanceof LlmProviderError)
                throw err;
            if (err.name === 'AbortError') {
                throw new LlmProviderError(`ollama (${model}) timed out after 120s.`);
            }
            throw new LlmProviderError(`ollama (${model}) failed: ${err.message}`);
        }
        finally {
            clearTimeout(timeout);
        }
    }
}
function normalizeBase(raw) {
    let s = raw.trim().replace(/\/+$/, '');
    if (!/\/api$/.test(s))
        s = `${s}/api`;
    return s;
}
//# sourceMappingURL=ollama-adapter.js.map