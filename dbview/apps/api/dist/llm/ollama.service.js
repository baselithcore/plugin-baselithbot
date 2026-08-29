var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable } from '@nestjs/common';
import { LlmProviderError } from '@dbview/shared';
let OllamaService = class OllamaService {
    /** Default base URL when none provided. Mirrors LLM adapter default. */
    defaultBaseUrl() {
        return process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434/api';
    }
    /**
     * Fetch installed models from the Ollama instance configured via env.
     * The endpoint is intentionally not overridable per request — it is a
     * deployment-level setting (OLLAMA_BASE_URL).
     */
    async listModels() {
        const url = normalizeBase(this.defaultBaseUrl());
        const tagsUrl = `${url}/tags`;
        const ctrl = new AbortController();
        const timeout = setTimeout(() => ctrl.abort(), 5_000);
        try {
            const res = await fetch(tagsUrl, { signal: ctrl.signal });
            if (!res.ok) {
                throw new LlmProviderError(`Ollama ${tagsUrl} returned ${res.status} ${res.statusText}.`);
            }
            const json = (await res.json());
            const models = (json.models ?? []).map(toModel);
            return { baseUrl: url, models };
        }
        catch (err) {
            if (err instanceof LlmProviderError)
                throw err;
            throw new LlmProviderError(`Cannot reach Ollama at ${tagsUrl}: ${err.message}`);
        }
        finally {
            clearTimeout(timeout);
        }
    }
};
OllamaService = __decorate([
    Injectable()
], OllamaService);
export { OllamaService };
function toModel(r) {
    return {
        name: r.name,
        size: r.size,
        digest: r.digest,
        modifiedAt: r.modified_at,
        family: r.details?.family,
        parameterSize: r.details?.parameter_size,
    };
}
function normalizeBase(raw) {
    let s = raw.trim().replace(/\/+$/, '');
    if (!/\/api$/.test(s))
        s = `${s}/api`;
    return s;
}
//# sourceMappingURL=ollama.service.js.map