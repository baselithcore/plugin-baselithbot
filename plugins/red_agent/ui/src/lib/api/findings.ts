import { call, qsLoose } from './client';
import type {
  AutoRemediationResult,
  ComplianceCoverage,
  ComplianceFramework,
  Finding,
  FindingEvidence,
  FindingFilters,
  FindingTriageUpdate,
} from './types';

export const findingsApi = {
  listFindings: (filters: FindingFilters = {}) =>
    call<Finding[]>(`/red-agent/findings${qsLoose(filters as Record<string, unknown>)}`),
  exportSarif: (scanId: string) => call<unknown>(`/red-agent/reports/${scanId}/sarif`),
  exportOcsf: (scanId: string) => call<unknown>(`/red-agent/reports/${scanId}/ocsf`),
  scanSigmaBundleUrl: (scanId: string) => `/red-agent/reports/${scanId}/sigma.zip`,
  engagementSigmaBundleUrl: (engagementId: string) =>
    `/red-agent/engagements/${engagementId}/sigma.zip`,
  findingSigmaUrlWithOverrides: (
    id: string,
    opts: { keywords?: string[]; tags?: string[] } = {}
  ) => {
    const usp = new URLSearchParams();
    for (const k of opts.keywords ?? []) {
      const t = k.trim();
      if (t) usp.append('keyword', t);
    }
    for (const t of opts.tags ?? []) {
      const tt = t.trim();
      if (tt) usp.append('tag', tt);
    }
    const q = usp.toString();
    return `/red-agent/findings/${id}/sigma${q ? `?${q}` : ''}`;
  },
  exportCompliance: (scanId: string, framework?: ComplianceFramework) =>
    call<ComplianceCoverage>(
      `/red-agent/reports/${scanId}/compliance${framework ? `?framework=${framework}` : ''}`
    ),
  autoRemediateFinding: (id: string) =>
    call<AutoRemediationResult>(`/red-agent/findings/${id}/auto-remediate`, { method: 'POST' }),
  getFindingEvidence: (id: string, chainLimit = 500) =>
    call<FindingEvidence>(`/red-agent/findings/${id}/evidence?chain_limit=${chainLimit}`),
  findingSigmaUrl: (id: string) => `/red-agent/findings/${id}/sigma`,
  updateFinding: (id: string, body: FindingTriageUpdate) =>
    call<{ finding_id: string; status: string }>(`/red-agent/findings/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
};
