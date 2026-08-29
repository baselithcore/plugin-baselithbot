import { collectDefaultMetrics, Counter, Gauge, Histogram, Registry } from 'prom-client';
export const registry = new Registry();
registry.setDefaultLabels({
    service: process.env.OTEL_SERVICE_NAME ?? 'dbview-api',
});
collectDefaultMetrics({ register: registry });
const LATENCY_BUCKETS = [
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5, 7.5, 10, 15, 30,
];
export const httpRequestLatency = new Histogram({
    name: 'dbview_http_request_latency_seconds',
    help: 'HTTP request latency in seconds',
    labelNames: ['method', 'route', 'status_bucket'],
    buckets: LATENCY_BUCKETS,
    registers: [registry],
});
export const httpRequestErrors = new Counter({
    name: 'dbview_http_request_errors_total',
    help: 'HTTP request errors total',
    labelNames: ['method', 'route', 'status_bucket', 'reason'],
    registers: [registry],
});
export const llmCalls = new Counter({
    name: 'dbview_llm_calls_total',
    help: 'LLM provider calls total',
    labelNames: ['provider', 'model', 'mode', 'status'],
    registers: [registry],
});
export const llmCallLatency = new Histogram({
    name: 'dbview_llm_call_latency_seconds',
    help: 'LLM provider call latency in seconds',
    labelNames: ['provider', 'model', 'mode'],
    buckets: LATENCY_BUCKETS,
    registers: [registry],
});
export const llmTokens = new Counter({
    name: 'dbview_llm_tokens_total',
    help: 'LLM tokens consumed',
    labelNames: ['provider', 'model', 'type'],
    registers: [registry],
});
export const queryExecutions = new Counter({
    name: 'dbview_query_executions_total',
    help: 'Query executions total',
    labelNames: ['dialect', 'status'],
    registers: [registry],
});
export const queryExecutionLatency = new Histogram({
    name: 'dbview_query_execution_latency_seconds',
    help: 'Query execution latency in seconds',
    labelNames: ['dialect'],
    buckets: LATENCY_BUCKETS,
    registers: [registry],
});
export const introspectionFailures = new Counter({
    name: 'dbview_schema_introspection_failures_total',
    help: 'Schema introspection failures total',
    labelNames: ['dialect', 'reason'],
    registers: [registry],
});
export const authEvents = new Counter({
    name: 'dbview_auth_events_total',
    help: 'Authentication events total',
    labelNames: ['event'],
    registers: [registry],
});
export const connectionsUp = new Gauge({
    name: 'dbview_connections_up',
    help: '1 if the stored connection is reachable, 0 otherwise',
    labelNames: ['connection_id', 'dialect'],
    registers: [registry],
});
export function statusBucket(status) {
    if (status < 200)
        return '1xx';
    if (status < 300)
        return '2xx';
    if (status < 400)
        return '3xx';
    if (status < 500)
        return '4xx';
    return '5xx';
}
//# sourceMappingURL=metrics.registry.js.map