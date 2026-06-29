// Thin client for the compliance API (mounted at /api/compliance). The access
// token is shared across plugins via the @auth context (localStorage key
// 'auth_access_token'); requests also send cookies for the refresh session.

import type {
  Arrangement,
  Concentration,
  ICTFunction,
  IncidentList,
  Overview,
  Provider,
  SubjectExport,
  ErasureReport,
  TransparencyStatus,
} from '../types';

const API = '/api/compliance';

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = localStorage.getItem('auth_access_token');
  return {
    'Content-Type': 'application/json',
    ...(extra ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: 'include',
    headers: authHeaders(),
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* keep status */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

const get = <T>(path: string) => request<T>(path);
const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });

export const api = {
  // Dashboard
  overview: () => get<Overview>('/overview'),
  // NIS2 incidents
  listIncidents: () => get<IncidentList>('/incidents'),
  openIncident: (body: Record<string, unknown>) => post('/incidents', body),
  advanceIncident: (id: string, milestone: string) => post(`/incidents/${id}/${milestone}`),
  // DORA incidents
  listDora: () => get<IncidentList>('/dora'),
  openDora: (body: Record<string, unknown>) => post('/dora', body),
  classifyDora: (id: string, body: Record<string, unknown>) => post(`/dora/${id}/classify`, body),
  advanceDora: (id: string, milestone: string) => post(`/dora/${id}/${milestone}`),
  // GDPR DSR
  dsrProviders: () => get<{ providers: string[] }>('/dsr/providers'),
  dsrExport: (subject_id: string) => post<SubjectExport>('/dsr/export', { subject_id }),
  dsrErase: (subject_id: string) => post<ErasureReport>('/dsr/erase', { subject_id }),
  // DORA third-party register
  tpProviders: () => get<{ providers: Provider[] }>('/thirdparty/providers'),
  tpFunctions: () => get<{ functions: ICTFunction[] }>('/thirdparty/functions'),
  tpArrangements: () => get<{ arrangements: Arrangement[] }>('/thirdparty/arrangements'),
  tpConcentration: () => get<Concentration>('/thirdparty/concentration'),
  tpExport: () => get<Record<string, unknown>>('/thirdparty/export'),
  addProvider: (body: Record<string, unknown>) => post('/thirdparty/providers', body),
  // AI Act transparency
  transparencyStatus: () => get<TransparencyStatus>('/transparency/status'),
  mark: (body: Record<string, unknown>) => post('/transparency/mark', body),
};
