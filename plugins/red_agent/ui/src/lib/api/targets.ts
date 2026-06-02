import { call, getToken, qs, qsLoose } from './client';
import type {
  ActivityEvent,
  RunDiff,
  ScanIntensity,
  ScanRow,
  TargetCreate,
  TargetListFilters,
  TargetPosture,
  TargetRecord,
  TargetUpdate,
} from './types';

export const targetsApi = {
  // ── Targets (project-as-entity) ────────────────────────────────────
  listTargets: (filters: TargetListFilters = {}) =>
    call<TargetRecord[]>(`/red-agent/targets${qsLoose(filters as Record<string, unknown>)}`),
  getTarget: (id: string) => call<TargetRecord>(`/red-agent/targets/${id}`),
  getTargetPosture: (id: string) => call<TargetPosture>(`/red-agent/targets/${id}/posture`),
  listTargetScans: (id: string, opts: { limit?: number; offset?: number } = {}) =>
    call<ScanRow[]>(`/red-agent/targets/${id}/scans${qsLoose(opts as Record<string, unknown>)}`),
  listTargetActivity: (id: string, limit = 100) =>
    call<ActivityEvent[]>(`/red-agent/targets/${id}/activity?limit=${limit}`),
  diffRuns: (targetId: string, baseline: string, latest: string) =>
    call<RunDiff>(
      `/red-agent/targets/${targetId}/diff?baseline=${encodeURIComponent(baseline)}&latest=${encodeURIComponent(latest)}`
    ),
  createTarget: (body: TargetCreate) =>
    call<TargetRecord>('/red-agent/targets', { method: 'POST', body: JSON.stringify(body) }),
  updateTarget: (id: string, body: TargetUpdate) =>
    call<TargetRecord>(`/red-agent/targets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  launchTargetScan: (
    id: string,
    body: {
      scanners?: string[];
      engagement_id?: string | null;
      intensity?: ScanIntensity;
      notes?: string;
    } = {}
  ) =>
    call<{ scan_id: string; target_id: string }>(`/red-agent/targets/${id}/scans`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteTarget: (id: string, opts: { hard?: boolean; purgeRuns?: boolean } = {}) => {
    const q = qs({
      hard: opts.hard ? 'true' : undefined,
      purge_runs: opts.purgeRuns ? 'true' : undefined,
    });
    return call<void>(`/red-agent/targets/${id}${q}`, { method: 'DELETE' });
  },

  // ── Binary / file scans ───────────────────────────────────────────
  uploadFileForScan: async (
    file: File,
    opts: { engagementId?: string; notes?: string } = {}
  ): Promise<{ scan_id: string; sha256: string; size: number; filename: string }> => {
    const form = new FormData();
    form.append('file', file);
    if (opts.engagementId) form.append('engagement_id', opts.engagementId);
    if (opts.notes) form.append('notes', opts.notes);
    const res = await fetch('/red-agent/file-scans', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return res.json();
  },
  getSampleInfo: (sha256: string) =>
    call<{ sha256: string; available: boolean; files?: string[] }>(
      `/red-agent/file-scans/${sha256}/info`
    ),
  purgeSample: (sha256: string) =>
    call<void>(`/red-agent/file-scans/${sha256}`, { method: 'DELETE' }),
};
