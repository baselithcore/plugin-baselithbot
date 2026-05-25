/**
 * AttackGeoMap Visual Constants
 *
 * Centralized configuration for colors, animations, and visual parameters.
 */

/** Severity level color mapping */
export const severityColors: Record<string, string> = {
  critical: '#ff4757',
  high: '#ff9f43',
  medium: '#f9ca24',
  low: '#26de81',
  info: '#45aaf2',
};

/** Animation timing constants */
export const ANIMATION = {
  /** Grid scroll speed (pixels per second) */
  GRID_SPEED: 15,
  /** Grid cell size in pixels */
  GRID_SIZE: 50,
  /** Radar sweep angular velocity (radians per second) */
  RADAR_SPEED: 0.5,
  /** Edge pulse frequency */
  EDGE_PULSE_FREQ: 3,
  /** Honeypot breath animation speed */
  HONEYPOT_BREATH_SPEED: 0.8,
  /** Honeypot pulse speed */
  HONEYPOT_PULSE_SPEED: 2,
  /** Honeypot rotation speed */
  HONEYPOT_ROTATE_SPEED: 0.2,
  /** Attacker beacon beat speed */
  ATTACKER_BEAT_SPEED: 3,
  /** Edge fade duration in ms - keep connections visible for 60 seconds */
  EDGE_FADE_DURATION: 60000,
  /** Particle spawn probability per frame - higher for more visible data flow */
  PARTICLE_SPAWN_RATE: 0.12,
} as const;

/** Node visual dimensions */
export const NODE_DIMENSIONS = {
  /** Honeypot node radius */
  HONEYPOT_RADIUS: 25,
  /** Attacker base radius */
  ATTACKER_BASE_RADIUS: 28,
  /** Hover radius increase */
  HOVER_RADIUS_INCREASE: 10,
  /** Selected radius increase */
  SELECTED_RADIUS_INCREASE: 5,
  /** Hit detection padding for attackers */
  ATTACKER_HIT_PADDING: 15,
} as const;

/** Canvas layer colors */
export const CANVAS_COLORS = {
  /** Grid line color */
  GRID: 'rgba(0, 212, 255, 0.1)',
  /** World map stroke */
  MAP_STROKE: 'rgba(0, 212, 255, 0.2)',
  /** World map fill */
  MAP_FILL: 'rgba(0, 212, 255, 0.05)',
  /** Radar sweep start color */
  RADAR_SWEEP: 'rgba(0, 212, 255, 0.12)',
  /** Radar line color */
  RADAR_LINE: 'rgba(0, 212, 255, 0.2)',
  /** Honeypot primary color */
  HONEYPOT_PRIMARY: '#00ff88',
  /** Node background */
  NODE_BG_INNER: '#151a25',
  /** Node background outer */
  NODE_BG_OUTER: '#0a0f15',
  /** Honeypot background */
  HONEYPOT_BG: '#0a1520',
} as const;
