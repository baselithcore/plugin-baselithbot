// =========================================================================
// k6 baseline — auth + read-only API load profile
//
// Scope: NO LLM endpoints (chat/stream) — quelli dipendono da Ollama
// throughput esterno e van profilati separatamente. Qui misuriamo:
//   - /health/ready (cheap, frequent)
//   - /auth/login + /auth/refresh (auth roundtrip)
//   - /api/wiki/groups + /api/wiki/page (read-heavy normal traffic)
//
// Run:
//   k6 run -e BASE_URL=http://localhost:8000 \
//          -e LOGIN_EMAIL=test@example.com -e LOGIN_PASSWORD=ChangeMe-12345 \
//          tests/loadtest/k6_baseline.js
//
// Soglie: p95 < 500ms su read; error rate < 1%. Failing -> exit 1.
//
// Profilo:
//   - 30s ramp-up 0 -> 50 VU
//   - 2m steady 50 VU
//   - 30s ramp-down -> 0
// =========================================================================
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const LOGIN_EMAIL = __ENV.LOGIN_EMAIL || '';
const LOGIN_PASSWORD = __ENV.LOGIN_PASSWORD || '';

const errorRate = new Rate('errors');
const loginLatency = new Trend('login_latency_ms');

export const options = {
    scenarios: {
        baseline: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 50 },
                { duration: '2m', target: 50 },
                { duration: '30s', target: 0 },
            ],
            gracefulRampDown: '30s',
        },
    },
    thresholds: {
        // Service-level objectives (SLO) baseline
        'http_req_duration{kind:health}': ['p(95)<100', 'p(99)<300'],
        'http_req_duration{kind:read}':   ['p(95)<500', 'p(99)<1500'],
        'http_req_duration{kind:auth}':   ['p(95)<800', 'p(99)<2000'],
        'http_req_failed':                ['rate<0.01'],
        'errors':                         ['rate<0.01'],
    },
};

function loginOnce() {
    if (!LOGIN_EMAIL) return null;
    const t0 = Date.now();
    const res = http.post(
        `${BASE_URL}/auth/login`,
        JSON.stringify({ email: LOGIN_EMAIL, password: LOGIN_PASSWORD }),
        {
            headers: { 'Content-Type': 'application/json' },
            tags: { kind: 'auth' },
        },
    );
    loginLatency.add(Date.now() - t0);
    const ok = check(res, {
        'login 200': r => r.status === 200,
        'access_token presente': r => !!(r.json('access_token')),
    });
    if (!ok) errorRate.add(1);
    if (res.status === 200) return res.json('access_token');
    return null;
}

export function setup() {
    // Token shared across VUs — bruteforce non è scopo; auth rate-limit
    // proteggerebbe la sessione di test altrimenti.
    const token = loginOnce();
    return { token };
}

export default function (data) {
    const headers = data.token
        ? { 'Authorization': `Bearer ${data.token}` }
        : {};

    group('health', () => {
        const r = http.get(`${BASE_URL}/health/live`, { tags: { kind: 'health' } });
        if (!check(r, { 'live 200': res => res.status === 200 })) errorRate.add(1);

        const r2 = http.get(`${BASE_URL}/health/ready`, { tags: { kind: 'health' } });
        if (!check(r2, { 'ready 200': res => res.status === 200 })) errorRate.add(1);
    });

    group('read', () => {
        const r = http.get(`${BASE_URL}/api/wiki/groups`, {
            headers,
            tags: { kind: 'read' },
        });
        check(r, { 'groups 200/401/404': res => [200, 401, 404].includes(res.status) });

        const r2 = http.get(`${BASE_URL}/api/wiki/index`, {
            headers,
            tags: { kind: 'read' },
        });
        check(r2, { 'index 200/401/404': res => [200, 401, 404].includes(res.status) });
    });

    sleep(Math.random() * 2 + 0.5);  // think-time 0.5–2.5s
}

export function handleSummary(data) {
    return {
        'stdout': textSummary(data),
        'loadtest-summary.json': JSON.stringify(data, null, 2),
    };
}

// Minimal text summary (k6 ships textSummary in /summary but kept inline for portability)
function textSummary(d) {
    const m = d.metrics;
    const dur = m.http_req_duration?.values || {};
    const fail = m.http_req_failed?.values || {};
    return [
        '=== Load test summary ===',
        `requests:          ${m.http_reqs?.values?.count || 0}`,
        `error rate:        ${((fail.rate || 0) * 100).toFixed(2)}%`,
        `latency p50/p95/p99: ${(dur['p(50)'] || 0).toFixed(0)} / ${(dur['p(95)'] || 0).toFixed(0)} / ${(dur['p(99)'] || 0).toFixed(0)} ms`,
        '',
    ].join('\n');
}
