/**
 * OpenTelemetry SDK bootstrap. Loaded as the first import in main.ts so the
 * Node module loader hooks are installed before app modules require `http`,
 * `pg`, etc. No-op unless OTEL_EXPORTER_OTLP_ENDPOINT is set.
 */
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
if (endpoint) {
    const serviceName = process.env.OTEL_SERVICE_NAME ?? 'dbview-api';
    const serviceVersion = process.env.APP_VERSION ?? '0.1.0';
    const tracesEndpoint = process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT ?? `${endpoint.replace(/\/$/, '')}/v1/traces`;
    const exporter = new OTLPTraceExporter({ url: tracesEndpoint });
    const sdk = new NodeSDK({
        resource: resourceFromAttributes({
            [ATTR_SERVICE_NAME]: serviceName,
            [ATTR_SERVICE_VERSION]: serviceVersion,
            'deployment.environment': process.env.NODE_ENV ?? 'development',
        }),
        spanProcessor: new BatchSpanProcessor(exporter, {
            maxQueueSize: 2048,
            maxExportBatchSize: 128,
            scheduledDelayMillis: 2000,
            exportTimeoutMillis: 10_000,
        }),
        instrumentations: [
            getNodeAutoInstrumentations({
                // Noisy; we rely on Pino bindings rather than log auto-export.
                '@opentelemetry/instrumentation-fs': { enabled: false },
                '@opentelemetry/instrumentation-http': {
                    ignoreIncomingRequestHook: (req) => {
                        const url = req.url ?? '';
                        return url === '/api/health' || url === '/api/metrics';
                    },
                },
            }),
        ],
    });
    sdk.start();
    const shutdown = () => {
        sdk
            .shutdown()
            .catch((err) => process.stderr.write(`OTel shutdown error: ${String(err)}\n`))
            .finally(() => process.exit(0));
    };
    process.once('SIGTERM', shutdown);
    process.once('SIGINT', shutdown);
}
//# sourceMappingURL=otel.js.map