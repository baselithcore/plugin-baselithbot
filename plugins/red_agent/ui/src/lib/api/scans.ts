import { call, qsLoose } from './client';
import type { CreateScanBody, PreflightBody, PreflightResp, ScanResult, ScanRow } from './types';

export const scansApi = {
  getScan: (id: string) => call<ScanResult>(`/red-agent/scans/${id}`),
  listScans: (
    filters: {
      status_filter?: string;
      target_id?: string;
      engagement_id?: string;
      limit?: number;
      offset?: number;
    } = {}
  ) => call<ScanRow[]>(`/red-agent/scans${qsLoose(filters)}`),
  quickScan: (target: string) =>
    call<{ scan_id: string }>(`/red-agent/scans/quick?target_value=${encodeURIComponent(target)}`, {
      method: 'POST',
    }),
  preflight: (body: PreflightBody) =>
    call<PreflightResp>('/red-agent/guardrails/preflight', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  createScan: (body: CreateScanBody) =>
    call<{ scan_id: string }>('/red-agent/scans', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  approveScan: (id: string) =>
    call<{ status: string }>(`/red-agent/scans/${id}/approve`, { method: 'POST' }),
  rejectScan: (id: string) =>
    call<{ status: string }>(`/red-agent/scans/${id}/reject`, { method: 'POST' }),
  cancelScan: (id: string) =>
    call<{ status: string }>(`/red-agent/scans/${id}/cancel`, { method: 'POST' }),
  deleteScan: (id: string) => call<void>(`/red-agent/scans/${id}`, { method: 'DELETE' }),
};
