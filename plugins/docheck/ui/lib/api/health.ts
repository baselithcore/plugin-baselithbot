import { authHeaders } from '../auth';
import { BASE } from './_base';
import type { CacheMetrics, HealthInfo } from './types';

export async function getHealth(): Promise<HealthInfo> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`health failed: ${res.status}`);
  return res.json();
}

export async function getCacheMetrics(): Promise<CacheMetrics> {
  const res = await fetch(`${BASE}/metrics/cache`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`metrics failed: ${res.status}`);
  return res.json();
}
