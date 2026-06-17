// Thin REST client for the BOP backend.
//
// The API base is derived from the current URL: the dashboard is served at
// `<prefix>/ui/`, so stripping the trailing `ui/` yields the API root. This keeps
// the bundle portable regardless of where the plugin router is mounted.

import type {
  Anomaly,
  AppliedChange,
  AuditEvent,
  AutomationRule,
  Bottleneck,
  BreachForecast,
  CasePrediction,
  ConformanceReport,
  CostReport,
  EventFilter,
  EventRecord,
  KpiSnapshot,
  MiningResult,
  OptimizationProposal,
  PerformanceReport,
  PredictorModel,
  ProcessGraph,
  ProcessVersion,
  Resource,
  RootCauseReport,
  RuleAction,
  RuleFiring,
  RuleTrigger,
  SimulationComparison,
  SimulationResult,
  SlaDefinition,
  SlaScope,
  VariantDiff,
  VariantReport,
} from './types';

/** Serialize a case filter to a query string (empty when no field is set). */
function filterQuery(filter?: EventFilter): string {
  if (!filter) return '';
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filter)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

function resolveApiBase(): string {
  const match = window.location.pathname.match(/^(.*)\/ui\/?/);
  return match ? match[1] : '/api/baselithoptimizeprocess';
}

export const API_BASE = resolveApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export interface ProcessPayload {
  id: string;
  name: string;
  description?: string;
  nodes: ProcessGraph['nodes'];
  edges: ProcessGraph['edges'];
  kpis: ProcessGraph['kpis'];
  currency?: string;
  annual_case_volume?: number | null;
}

export const api = {
  listProcesses: () => request<ProcessGraph[]>('/processes'),

  getProcess: (id: string) => request<ProcessGraph>(`/processes/${id}`),

  registerProcess: (payload: ProcessPayload) =>
    request<ProcessGraph>('/processes', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  importProcess: (id: string, xml: string, kpis: ProcessGraph['kpis']) =>
    request<ProcessGraph>('/processes/import', {
      method: 'POST',
      body: JSON.stringify({ id, xml, kpis }),
    }),

  deleteProcess: (id: string) =>
    request<{ deleted: string }>(`/processes/${id}`, { method: 'DELETE' }),

  ingestMetrics: (
    id: string,
    samples: { process_id: string; kpi_id: string; value: number; node_id?: string }[]
  ) =>
    request<{ accepted: number }>(`/processes/${id}/metrics`, {
      method: 'POST',
      body: JSON.stringify({ samples }),
    }),

  snapshots: (id: string) => request<KpiSnapshot[]>(`/processes/${id}/snapshots`),

  bottlenecks: (id: string) => request<Bottleneck[]>(`/processes/${id}/bottlenecks`),

  optimize: (id: string, context: string, maxProposals: number) =>
    request<OptimizationProposal[]>(`/processes/${id}/optimize`, {
      method: 'POST',
      body: JSON.stringify({ context, max_proposals: maxProposals }),
    }),

  listProposals: (id?: string) =>
    request<OptimizationProposal[]>(
      id ? `/proposals?process_id=${encodeURIComponent(id)}` : '/proposals'
    ),

  decideProposal: (proposalId: string, approve: boolean) =>
    request<OptimizationProposal>(`/proposals/${proposalId}/${approve ? 'approve' : 'reject'}`, {
      method: 'POST',
      body: JSON.stringify({ note: '' }),
    }),

  // -- DataOps: mining, conformance, automation ---------------------------

  mineEventLog: (id: string, name: string, events: EventRecord[], minFrequency = 0) =>
    request<MiningResult>('/processes/mine', {
      method: 'POST',
      body: JSON.stringify({ id, name, events, min_frequency: minFrequency }),
    }),

  getMining: (id: string) => request<MiningResult>(`/processes/${id}/mining`),

  pullSource: (
    id: string,
    url: string,
    kind: 'events' | 'metrics' = 'events',
    name = '',
    minFrequency = 0
  ) =>
    request<{ kind: string; mining?: MiningResult; accepted?: number }>(`/processes/${id}/pull`, {
      method: 'POST',
      body: JSON.stringify({ url, kind, name, min_frequency: minFrequency }),
    }),

  checkConformance: (id: string, events: EventRecord[]) =>
    request<ConformanceReport>(`/processes/${id}/conformance`, {
      method: 'POST',
      body: JSON.stringify({ events }),
    }),

  listRules: (id: string) => request<AutomationRule[]>(`/processes/${id}/rules`),

  createRule: (id: string, name: string, trigger: RuleTrigger, action: RuleAction) =>
    request<AutomationRule>(`/processes/${id}/rules`, {
      method: 'POST',
      body: JSON.stringify({ name, trigger, action, enabled: true }),
    }),

  deleteRule: (ruleId: string) =>
    request<{ deleted: string }>(`/rules/${ruleId}`, { method: 'DELETE' }),

  listFirings: (id: string) => request<RuleFiring[]>(`/processes/${id}/firings`),

  // -- Governance: versioning + audit trail -------------------------------

  listVersions: (id: string) => request<ProcessVersion[]>(`/processes/${id}/versions`),

  processAudit: (id: string, limit = 100) =>
    request<AuditEvent[]>(`/processes/${id}/audit?limit=${limit}`),

  costReport: (id: string) => request<CostReport>(`/processes/${id}/cost`),

  // -- What-if simulation -------------------------------------------------

  simulate: (id: string) => request<SimulationResult>(`/processes/${id}/simulate`),

  simulateVariant: (id: string, payload: ProcessPayload) =>
    request<SimulationComparison>(`/processes/${id}/simulate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // -- Governed apply + rollback ------------------------------------------

  applyChange: (id: string, payload: ProcessPayload, proposalId = '') =>
    request<AppliedChange>(`/processes/${id}/apply`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, proposal_id: proposalId }),
    }),

  listChanges: (id: string) => request<AppliedChange[]>(`/processes/${id}/changes`),

  rollbackChange: (changeId: string) =>
    request<AppliedChange>(`/changes/${changeId}/rollback`, { method: 'POST' }),

  rollbackToVersion: (id: string, version: number) =>
    request<ProcessGraph>(`/processes/${id}/rollback/${version}`, { method: 'POST' }),

  // -- Predictive: anomalies + breach forecasts ---------------------------

  anomalies: (id: string) => request<Anomaly[]>(`/processes/${id}/anomalies`),

  forecast: (id: string) => request<BreachForecast[]>(`/processes/${id}/forecast`),

  // -- Insights: variants, performance/SLA, root cause, prediction --------

  variants: (id: string, filter?: EventFilter) =>
    request<VariantReport>(`/processes/${id}/variants${filterQuery(filter)}`),

  variantDiff: (id: string, a: string, b: string, filter?: EventFilter) => {
    const params = new URLSearchParams({ a, b });
    if (filter) {
      for (const [k, v] of Object.entries(filter)) {
        if (v !== undefined && v !== null && v !== '') params.set(k, String(v));
      }
    }
    return request<VariantDiff>(`/processes/${id}/variants/diff?${params.toString()}`);
  },

  performance: (id: string, filter?: EventFilter) =>
    request<PerformanceReport>(`/processes/${id}/performance${filterQuery(filter)}`),

  rootCause: (id: string, thresholdSeconds?: number, filter?: EventFilter) => {
    const params = new URLSearchParams(filterQuery(filter).replace(/^\?/, ''));
    if (thresholdSeconds) params.set('threshold_seconds', String(thresholdSeconds));
    const query = params.toString();
    return request<RootCauseReport>(`/processes/${id}/rootcause${query ? `?${query}` : ''}`);
  },

  predictor: (id: string) => request<PredictorModel>(`/processes/${id}/predictor`),

  predictCase: (id: string, events: EventRecord[]) =>
    request<CasePrediction>(`/processes/${id}/predict`, {
      method: 'POST',
      body: JSON.stringify({ events }),
    }),

  listSlas: (id: string) => request<SlaDefinition[]>(`/processes/${id}/slas`),

  createSla: (
    id: string,
    payload: { name: string; scope: SlaScope; activity: string; threshold_seconds: number }
  ) =>
    request<SlaDefinition>(`/processes/${id}/slas`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deleteSla: (slaId: string) =>
    request<{ deleted: string }>(`/slas/${slaId}`, { method: 'DELETE' }),

  // -- Resources: assignable pool + step assignment -----------------------

  listResources: () => request<Resource[]>('/resources'),

  createResource: (payload: Partial<Resource> & { name: string }) =>
    request<Resource>('/resources', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateResource: (resourceId: string, patch: Partial<Resource>) =>
    request<Resource>(`/resources/${resourceId}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),

  deleteResource: (resourceId: string) =>
    request<{ deleted: string }>(`/resources/${resourceId}`, { method: 'DELETE' }),

  assignResource: (processId: string, nodeId: string, resourceId: string | null) =>
    request<ProcessGraph>(`/processes/${processId}/nodes/${nodeId}/resource`, {
      method: 'POST',
      body: JSON.stringify({ resource_id: resourceId }),
    }),

  report: async (id: string, format: 'markdown' | 'csv' = 'markdown') => {
    const res = await fetch(`${API_BASE}/processes/${id}/report?format=${format}`);
    if (!res.ok) throw new Error(`Report failed (${res.status})`);
    return res.text();
  },

  streamUrl: (id: string) => `${API_BASE}/processes/${id}/stream`,
};
