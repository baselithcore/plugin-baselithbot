// Typed fetch client for the platform API. One module, no dependencies — every
// call funnels through `request` so error handling and JSON parsing stay in one
// place.

import type {
  AgentBlueprint,
  AgentCapability,
  AgentRunResult,
  DocCitation,
  ModelInfo,
  ScheduleSpec,
} from './types';

const BASE = '/api/baselithcore_agents_platform';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listBlueprints: () => request<AgentBlueprint[]>('/blueprints'),

  createBlueprint: (description: string) =>
    request<AgentBlueprint>('/blueprints', {
      method: 'POST',
      body: JSON.stringify({ description }),
    }),

  deleteBlueprint: (id: string) =>
    request<{ deleted: string }>(`/blueprints/${id}`, { method: 'DELETE' }),

  runAgent: (id: string, capability: AgentCapability, task: string, code = '') =>
    request<AgentRunResult>(`/blueprints/${id}/runs`, {
      method: 'POST',
      body: JSON.stringify({ capability, task, code }),
    }),

  listRuns: (blueprintId?: string) =>
    request<AgentRunResult[]>(
      blueprintId ? `/runs?blueprint_id=${encodeURIComponent(blueprintId)}` : '/runs'
    ),

  searchDocs: (q: string, prefix = '', topK = 6) => {
    const params = new URLSearchParams({ q, top_k: String(topK) });
    if (prefix) params.set('prefix', prefix);
    return request<DocCitation[]>(`/docs/search?${params.toString()}`);
  },

  docNamespaces: () => request<string[]>('/docs/namespaces'),

  models: () => request<ModelInfo[]>('/models'),

  tools: () => request<string[]>('/tools'),

  listSchedules: () => request<ScheduleSpec[]>('/schedules'),

  createSchedule: (
    blueprintId: string,
    capability: AgentCapability,
    task: string,
    intervalSeconds: number
  ) =>
    request<ScheduleSpec>(`/blueprints/${blueprintId}/schedules`, {
      method: 'POST',
      body: JSON.stringify({
        capability,
        task,
        interval_seconds: intervalSeconds,
      }),
    }),

  deleteSchedule: (id: string) =>
    request<{ deleted: string }>(`/schedules/${id}`, { method: 'DELETE' }),
};
