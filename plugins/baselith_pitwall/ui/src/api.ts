import type {
  AckStatus,
  AuditRecord,
  BattleForecast,
  IndicatorSet,
  RaceControlStatus,
  RaceSession,
  Recommendation,
  RecommendationAck,
  Scenario,
  SourceKind,
  Status,
  Stint,
  StrategyOutcome,
} from './types';

const BASE = '/api/baselith_pitwall';

// The dashboard targets one race session at a time. The id is sent on every
// request via X-Session-ID (and as a query param for the SSE stream, which
// cannot set headers). Defaults to the bundled demo session.
let activeSession = 'demo';

export function setActiveSession(id: string): void {
  activeSession = id;
}

export function getActiveSession(): string {
  return activeSession;
}

function headers(extra?: Record<string, string>): Record<string, string> {
  return {
    'Accept-Language': navigator.language || 'en',
    'X-Session-ID': activeSession,
    ...extra,
  };
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: headers() });
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as T;
}

async function postJSON<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  status: () => getJSON<Status>('/status'),
  cars: () => getJSON<string[]>('/cars'),
  stint: (carId: string) => getJSON<Stint>(`/stint/${carId}`),
  recommendations: (carId?: string) =>
    getJSON<Recommendation[]>(
      `/recommendations${carId ? `?car_id=${encodeURIComponent(carId)}` : ''}`
    ),
  simulate: (carId: string) => postJSON<Scenario>(`/simulate/${carId}`),
  battle: (carId: string) => getJSON<BattleForecast>(`/battle/${carId}`),
  outcome: (carId: string) => getJSON<StrategyOutcome>(`/outcome/${carId}`),
  indicators: (carId: string) => getJSON<IndicatorSet>(`/indicators/${carId}`),
  intel: (carId: string) => getJSON<{ car_id: string; brief: string }>(`/intel/${carId}`),
  setRaceControl: (status: RaceControlStatus) =>
    postJSON<unknown>('/race-control', { status, lap: 0 }),
  setWeather: (trackWetness: number, rainIntensity: number) =>
    postJSON<unknown>('/weather', {
      track_wetness: trackWetness,
      rain_intensity: rainIntensity,
    }),

  // -- sessions --------------------------------------------------------
  listSessions: () => getJSON<RaceSession[]>('/sessions'),
  createSession: (body: {
    name: string;
    circuit?: string;
    total_laps?: number;
    source_kind?: SourceKind;
  }) => postJSON<RaceSession>('/sessions', body),
  startSession: (id: string) => postJSON<RaceSession>(`/sessions/${id}/start`),
  pauseSession: (id: string) => postJSON<RaceSession>(`/sessions/${id}/pause`),
  endSession: (id: string) => postJSON<RaceSession>(`/sessions/${id}/end`),

  // -- governance ------------------------------------------------------
  audit: (limit = 50) => getJSON<AuditRecord[]>(`/audit?limit=${limit}`),
  acks: () => getJSON<RecommendationAck[]>('/acks'),
  acknowledge: (recId: string, status: AckStatus, note = '') =>
    postJSON<RecommendationAck>(`/recommendations/${recId}/ack`, { status, note }),
};

// Subscribe to the SSE recommendation stream for the active session. Returns an
// unsubscribe function.
export function subscribeRecommendations(onRec: (rec: Recommendation) => void): () => void {
  const source = new EventSource(`${BASE}/stream?session_id=${encodeURIComponent(activeSession)}`);
  source.addEventListener('recommendation', (ev) => {
    try {
      onRec(JSON.parse((ev as MessageEvent).data) as Recommendation);
    } catch {
      /* ignore malformed frame */
    }
  });
  return () => source.close();
}
