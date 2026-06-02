import type { InterviewTurnResult, TriageReport } from './types';

const BASE = '/api/baselithmed';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return (await res.json()) as T;
}

export interface BackendInfo {
  plugin: string;
  version: string;
  model_id: string | null;
  host: string | null;
  context_window: number | null;
}

export async function fetchInfo(): Promise<BackendInfo> {
  return request<BackendInfo>('/info');
}

export async function createSession(pseudonym?: string) {
  return request<{ session_id: string; patient_pseudonym: string }>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ patient_pseudonym: pseudonym ?? null }),
  });
}

export async function postInterviewTurn(
  session_id: string,
  utterance: string
): Promise<InterviewTurnResult> {
  return request<InterviewTurnResult>('/interview', {
    method: 'POST',
    body: JSON.stringify({ session_id, utterance }),
  });
}

export async function finalizeTriage(
  session_id: string,
  patient_pseudonym?: string
): Promise<{ success: boolean; data: TriageReport; metadata?: unknown }> {
  return request('/triage/finalize', {
    method: 'POST',
    body: JSON.stringify({
      session_id,
      patient_pseudonym: patient_pseudonym ?? null,
    }),
  });
}

export async function validateReport(
  session_id: string,
  approved: boolean,
  clinician_id: string,
  notes?: string
) {
  return request<{ session_id: string; validated: boolean }>(
    `/triage/${encodeURIComponent(session_id)}/validate`,
    {
      method: 'POST',
      body: JSON.stringify({ approved, clinician_id, notes: notes ?? null }),
    }
  );
}
