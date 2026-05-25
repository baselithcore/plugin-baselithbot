// =========================================================================
// k6 — chat stream profile (tirando il LLM)
//
// SCOPE: misura concorrenza chat NDJSON streaming. Richiede LLM upstream
// (Ollama) reachable + caricato. Concorrenza realistica = 4-8 VU; oltre,
// Ollama coda internamente e p99 esplode.
//
// Run:
//   k6 run -e BASE_URL=... -e BEARER=... -e VUS=4 \
//          tests/loadtest/k6_chat_stream.js
//
// Output: tempo al primo token (TTFT) + tempo totale risposta + token rate.
// =========================================================================
import http from 'k6/http';
import { check } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const BEARER = __ENV.BEARER || '';
const VUS = parseInt(__ENV.VUS || '4', 10);

const ttft = new Trend('chat_ttft_ms');           // time to first token
const totalLatency = new Trend('chat_total_ms');
const tokensTotal = new Counter('chat_tokens_total');

const QUESTIONS = [
    'Riassumi le clausole principali di una polizza RC professionale.',
    'Quali sono i requisiti di copertura per un infortunio sul lavoro?',
    'Spiega la differenza tra franchigia assoluta e relativa.',
    'Quali documenti servono per aprire un sinistro auto?',
];

export const options = {
    scenarios: {
        chat: {
            executor: 'constant-vus',
            vus: VUS,
            duration: '3m',
        },
    },
    thresholds: {
        'chat_ttft_ms':  ['p(95)<5000'],   // primo token entro 5s p95
        'chat_total_ms': ['p(95)<60000'],  // risposta completa entro 60s p95
        'http_req_failed': ['rate<0.02'],
    },
};

export default function () {
    const q = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
    const t0 = Date.now();
    let firstTokenAt = null;
    let tokens = 0;

    const res = http.post(
        `${BASE_URL}/api/chat/stream`,
        JSON.stringify({ message: q, limit: 5 }),
        {
            headers: {
                'Content-Type': 'application/json',
                ...(BEARER ? { 'Authorization': `Bearer ${BEARER}` } : {}),
            },
            timeout: '120s',
            // k6 non ha vero streaming; legge response in chunk via body.
            // Approssimazione: se il primo chunk arriva prima del completamento,
            // possiamo decode-line e contare token.
        },
    );

    const tEnd = Date.now();
    if (res.status === 200 && res.body) {
        const lines = res.body.split('\n').filter(Boolean);
        for (const line of lines) {
            try {
                const evt = JSON.parse(line);
                if (evt.type === 'token') {
                    if (firstTokenAt === null) firstTokenAt = tEnd;  // approx
                    tokens++;
                }
            } catch (_) { /* ignore non-JSON lines */ }
        }
    }

    if (firstTokenAt !== null) ttft.add(firstTokenAt - t0);
    totalLatency.add(tEnd - t0);
    tokensTotal.add(tokens);

    check(res, {
        'stream 200': r => r.status === 200,
        'tokens > 0': () => tokens > 0,
    });
}
