import { LlmProviderSchema } from '@dbview/shared';
function readHeader(headers, name) {
    const value = headers[name];
    const single = Array.isArray(value) ? value[0] : value;
    return single && single.length > 0 ? single : undefined;
}
function readScope(headers, providerHeader, modelHeader) {
    const raw = readHeader(headers, providerHeader);
    if (!raw)
        return undefined;
    const parsed = LlmProviderSchema.safeParse(raw);
    if (!parsed.success)
        return undefined;
    return { provider: parsed.data, model: readHeader(headers, modelHeader) };
}
export function parseGovernanceHeaders(headers) {
    const translate = readScope(headers, 'x-dbview-gov-nl2sql-provider', 'x-dbview-gov-nl2sql-model');
    const explain = readScope(headers, 'x-dbview-gov-explain-provider', 'x-dbview-gov-explain-model');
    const openaiKey = readHeader(headers, 'x-dbview-gov-openai-key');
    const anthropicKey = readHeader(headers, 'x-dbview-gov-anthropic-key');
    const ollamaBase = readHeader(headers, 'x-dbview-gov-ollama-base');
    if (!translate && !explain && !openaiKey && !anthropicKey && !ollamaBase) {
        return undefined;
    }
    return { translate, explain, openaiKey, anthropicKey, ollamaBase };
}
//# sourceMappingURL=governance-headers.js.map