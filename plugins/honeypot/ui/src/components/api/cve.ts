/**
 * CVE Integration APIs (from cve_hunter)
 * CVE detail fetching and analysis
 */

import { getAuthHeaders } from './auth';
import type { CVERecord } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchCVEDetail(cveId: string): Promise<CVERecord> {
  const response = await fetch(`${API_BASE}/cve_hunter/cves/${encodeURIComponent(cveId)}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });
  if (!response.ok) throw new Error('Failed to fetch CVE details');
  return response.json();
}

export async function analyzeCVE(cveId: string): Promise<CVERecord> {
  const response = await fetch(`${API_BASE}/cve_hunter/cves/${cveId}/analyze`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });
  if (!response.ok) throw new Error('Failed to analyze CVE');
  return response.json();
}
