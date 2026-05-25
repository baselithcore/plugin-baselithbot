/**
 * Geo Visualization APIs
 * Geographic attack data for globe and map visualizations
 */

import { honeypotApiFetch } from './core';

export interface GeoAttack {
  id: string;
  source: {
    lat: number;
    lng: number;
    country?: string;
    country_code?: string;
    city?: string;
  } | null;
  target: { lat: number; lng: number };
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  protocol: 'ssh' | 'http' | 'tcp';
  timestamp: string;
}

export interface GeoMarker {
  lat: number;
  lng: number;
  count: number;
  severity: string;
  country_code?: string;
}

export interface GeoAttacksResponse {
  flows: GeoAttack[];
  markers: GeoMarker[];
  heatmap: Array<{ country_code: string; count: number; intensity: number }>;
  target: { lat: number; lng: number };
  total_attacks: number;
  unique_countries: number;
}

export async function fetchGeoAttacks(
  limit: number = 50,
  severity?: string
): Promise<GeoAttacksResponse> {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (severity) params.set('severity', severity);
  return honeypotApiFetch<GeoAttacksResponse>(`/geo/attacks?${params.toString()}`);
}
