/**
 * Report Generation APIs
 * Security report generation, preview, and export (PDF, Markdown)
 */

import { honeypotApiFetch } from './core';
import { getAuthHeaders } from './auth';
import type {
  ReportType,
  ReportGenerationRequest,
  SecurityReport,
  ReportTypesResponse,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchReportTypes(): Promise<ReportTypesResponse> {
  return honeypotApiFetch<ReportTypesResponse>('/reports/types');
}

export async function generateReportPreview(
  reportType: ReportType,
  timeRangeHours: number = 168,
  honeypotId?: string,
  sections?: string[]
): Promise<SecurityReport> {
  const params = new URLSearchParams({
    report_type: reportType,
    time_range_hours: timeRangeHours.toString(),
  });
  if (honeypotId) params.set('honeypot_id', honeypotId);
  if (sections) {
    sections.forEach((section) => params.append('sections', section));
  }
  return honeypotApiFetch<SecurityReport>(`/reports/preview?${params.toString()}`);
}

export async function generateReport(request: ReportGenerationRequest): Promise<SecurityReport> {
  return honeypotApiFetch<SecurityReport>('/reports/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function downloadMarkdownReport(request: ReportGenerationRequest): Promise<Blob> {
  const response = await fetch(`${API_BASE}/honeypot/reports/generate/markdown`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to generate markdown report');
  }

  return response.blob();
}

export async function downloadPdfReport(request: ReportGenerationRequest): Promise<Blob> {
  const response = await fetch(`${API_BASE}/honeypot/reports/generate/pdf`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error('Failed to generate PDF report');
  }

  return response.blob();
}
