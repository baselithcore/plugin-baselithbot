import { llmCallLatency, llmCalls } from './metrics.registry.js';
export function instrumentLlmAdapter(adapter, mode) {
    return {
        provider: adapter.provider,
        name: adapter.name,
        async complete(input, model) {
            const start = process.hrtime.bigint();
            const labels = { provider: adapter.provider, model, mode };
            try {
                const res = await adapter.complete(input, model);
                const seconds = Number(process.hrtime.bigint() - start) / 1e9;
                llmCallLatency.labels(labels).observe(seconds);
                llmCalls.labels({ ...labels, status: 'ok' }).inc();
                return res;
            }
            catch (err) {
                const seconds = Number(process.hrtime.bigint() - start) / 1e9;
                llmCallLatency.labels(labels).observe(seconds);
                llmCalls.labels({ ...labels, status: 'error' }).inc();
                throw err;
            }
        },
    };
}
//# sourceMappingURL=instrument-llm.js.map