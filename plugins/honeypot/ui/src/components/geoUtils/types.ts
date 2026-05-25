/**
 * GeoUtils Types
 */

/** Threat level (1-5 severity scale) */
export type ThreatLevel = 1 | 2 | 3 | 4 | 5;

/** Mesh connection between attack sources */
export interface MeshConnection {
  id: string;
  sourceA: { lat: number; lng: number };
  sourceB: { lat: number; lng: number };
  strength: number; // 0-1
  commonSubnet: string;
}

/** Geographic marker for map visualization */
export interface GeoMarker {
  lat: number;
  lng: number;
  count: number;
  severity: string;
  country_code?: string;
  subnet?: string;
}
