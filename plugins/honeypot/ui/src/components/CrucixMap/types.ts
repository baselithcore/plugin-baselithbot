/**
 * CrucixMap Type Definitions
 *
 * Types for the Crucix-inspired dual-mode map visualization.
 */

import type { AttackEvent, HoneypotAttacker, HoneypotInfo } from '../types';
import type { GraphNode } from '../types';

export type ViewMode = 'flat' | 'globe';

/** A point on the map representing an attacker */
export interface MapPoint {
  id: string;
  lat: number;
  lng: number;
  size: number;
  altitude: number;
  color: string;
  ip: string;
  country: string;
  country_code: string;
  severity: string;
  protocol: string;
  attackCount: number;
  priority: number;
  isRecent: boolean;
  popHead: string;
  popMeta: string;
  popText: string;
}

/** An arc connecting an attacker to the honeypot */
export interface MapArc {
  id: string;
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  color: [string, string];
  stroke: number;
  severity: string;
  protocol: string;
  attackCount: number;
}

/** A pulsing ring for critical/active attackers */
export interface MapRing {
  lat: number;
  lng: number;
  maxR: number;
  propagationSpeed: number;
  repeatPeriod: number;
}

/** Aggregated map statistics */
export interface MapStats {
  total: number;
  countries: number;
  attackers: number;
}

/** Full map data output from useMapData */
export interface MapData {
  points: MapPoint[];
  arcs: MapArc[];
  rings: MapRing[];
  honeypot: { lat: number; lng: number };
  stats: MapStats;
  attackVelocity: number;
}

/** Props for the main CrucixMapView component (drop-in replacement for AttackGeoMap) */
export interface CrucixMapProps {
  events: AttackEvent[];
  attackers?: HoneypotAttacker[];
  activeProtocols?: string[];
  honeypotContext?: HoneypotInfo | null;
  onSelectNode?: (node: GraphNode) => void;
  isActive?: boolean;
}

/** Currently selected/hovered map marker */
export interface SelectedMarker {
  point: MapPoint;
  screenX: number;
  screenY: number;
}

/** Hovered point with cursor position for tooltip */
export interface HoveredPoint {
  point: MapPoint;
  cursorX: number;
  cursorY: number;
}
