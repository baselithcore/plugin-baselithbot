import { initializeFaro, getWebInstrumentations } from '@grafana/faro-web-sdk';
import { TracingInstrumentation } from '@grafana/faro-web-tracing';

/**
 * Initialize Grafana Faro web SDK if VITE_OTLP_ENDPOINT is set.
 * No-op otherwise (dev/local). Mirrors agent-jira's `observability.ts`.
 */
export function initObservability(): void {
  const endpoint = import.meta.env.VITE_OTLP_ENDPOINT as string | undefined;
  if (!endpoint) return;

  const appName = (import.meta.env.VITE_APP_NAME as string | undefined) ?? 'dbview-web';
  const appVersion = (import.meta.env.VITE_APP_VERSION as string | undefined) ?? '0.1.0';
  const environment =
    (import.meta.env.VITE_DEPLOY_ENV as string | undefined) ??
    (import.meta.env.MODE === 'production' ? 'production' : 'development');

  initializeFaro({
    url: `${endpoint.replace(/\/$/, '')}/v1/traces`,
    app: { name: appName, version: appVersion, environment },
    instrumentations: [
      ...getWebInstrumentations({ captureConsole: true }),
      new TracingInstrumentation(),
    ],
    sessionTracking: { enabled: true, persistent: true },
    batching: { enabled: true, sendTimeout: 250, itemLimit: 50 },
  });
}
