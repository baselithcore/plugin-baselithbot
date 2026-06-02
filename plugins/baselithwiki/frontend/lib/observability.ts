/**
 * Frontend RUM via Grafana Faro (opt-in).
 *
 * Forwarda web-vitals, navigation timing, fetch/XHR spans, errori, console
 * logs all'OTEL collector self-hosted (porta 4319 di default sull'host).
 *
 * Config via env Vite:
 *  - VITE_OTLP_ENDPOINT: URL completo OTLP HTTP (es. http://<vm-ip>:4319).
 *    Default: stesso host del frontend, porta 4319.
 *  - VITE_APP_VERSION: stringa versione (default 'dev').
 *  - VITE_APP_ENV: 'prod' | 'staging' | 'dev'.
 *
 * Senza i package `@grafana/faro-*` installati la funzione è no-op:
 * import dinamico, fallback silenzioso. Permette di mantenere il frontend
 * buildable senza dipendere dallo stack obs.
 */

let _initialized = false;

function resolveOtlpEndpoint(): string | null {
  const explicit = (import.meta.env.VITE_OTLP_ENDPOINT as string | undefined)?.trim();
  if (explicit) return explicit.replace(/\/$/, '');
  if (typeof window === 'undefined') return null;
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:4319`;
}

export async function initObservability(): Promise<void> {
  if (_initialized) return;
  if (typeof window === 'undefined') return;

  const otlpBase = resolveOtlpEndpoint();
  if (!otlpBase) return;

  const appName = 'llm-wiki-frontend';
  const appVersion = (import.meta.env.VITE_APP_VERSION as string | undefined) || 'dev';
  const appEnv = (import.meta.env.VITE_APP_ENV as string | undefined) || 'dev';

  // Concatenazione runtime: nasconde lo specifier all'analisi statica
  // di Vite/Rollup. Senza i package installati l'import fallisce a
  // runtime e l'app prosegue senza RUM (catch sotto).
  const sdkSpec = '@grafana/' + 'faro-web-sdk';
  const tracingSpec = '@grafana/' + 'faro-web-tracing';
  try {
    const [sdkMod, tracingMod] = await Promise.all([
      import(/* @vite-ignore */ sdkSpec),
      import(/* @vite-ignore */ tracingSpec),
    ]);
    const { initializeFaro, getWebInstrumentations } = sdkMod;
    const { TracingInstrumentation } = tracingMod;

    initializeFaro({
      url: `${otlpBase}/v1/traces`,
      app: { name: appName, version: appVersion, environment: appEnv },
      instrumentations: [
        ...getWebInstrumentations({ captureConsole: true }),
        new TracingInstrumentation({
          instrumentationOptions: {
            propagateTraceHeaderCorsUrls: [/.*/],
          },
        }),
      ],
      sessionTracking: { enabled: true, persistent: true },
      batching: { enabled: true, sendTimeout: 250, itemLimit: 50 },
    });
    _initialized = true;
    // eslint-disable-next-line no-console
    console.info('[obs] Faro initialized →', otlpBase);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[obs] Faro init skipped (package non installato o init fallito):', err);
  }
}
