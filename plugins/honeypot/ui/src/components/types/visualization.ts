/**
 * Graph visualization types
 */

export interface EdgeParticle {
  progress: number;
  speed: number;
}

export interface GraphNode {
  id: string;
  type: 'honeypot' | 'attacker';
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  fx?: number | null;
  fy?: number | null;
  ip?: string;
  country_code?: string;
  country?: string;
  protocol?: string;
  severity?: string;
  attackCount?: number;
  lastAttack?: Date;
  visible?: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  active: boolean;
  lastActivity: number;
  protocol: string;
  severity: string;
  particles: EdgeParticle[];
  visible?: boolean;
}

export interface HeatmapEntry {
  country_code: string;
  count: number;
  intensity: number;
}

export interface StreamAttackEvent {
  id: string;
  source_ip: string;
  country_code?: string;
  country?: string;
  city?: string;
  protocol: string;
  severity: string;
  timestamp: string;
  attackCount?: number;
  raw_data?: string;
  command?: string | null;
  http_body?: string | null;
  event_type?: string;
}
