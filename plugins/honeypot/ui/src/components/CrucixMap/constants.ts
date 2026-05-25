/**
 * CrucixMap Constants
 *
 * Colors, config, and visual parameters inspired by the Crucix dashboard.
 */

/** Severity → point color (rgba for Globe.gl compatibility) */
export const SEVERITY_COLORS: Record<string, string> = {
  critical: 'rgba(255, 71, 87, 0.9)',
  high: 'rgba(255, 159, 67, 0.85)',
  medium: 'rgba(249, 202, 36, 0.8)',
  low: 'rgba(38, 222, 129, 0.8)',
  info: 'rgba(69, 170, 242, 0.7)',
};

/** Severity → arc gradient [main, fade] */
export const SEVERITY_ARC_COLORS: Record<string, [string, string]> = {
  critical: ['rgba(255, 71, 87, 0.8)', 'rgba(255, 71, 87, 0.15)'],
  high: ['rgba(255, 159, 67, 0.7)', 'rgba(255, 159, 67, 0.12)'],
  medium: ['rgba(249, 202, 36, 0.5)', 'rgba(249, 202, 36, 0.1)'],
  low: ['rgba(38, 222, 129, 0.4)', 'rgba(38, 222, 129, 0.08)'],
  info: ['rgba(69, 170, 242, 0.4)', 'rgba(69, 170, 242, 0.08)'],
};

/** Severity → zoom priority (1 = always visible, 3 = close-zoom only) */
export const SEVERITY_PRIORITY: Record<string, number> = {
  critical: 1,
  high: 1,
  medium: 2,
  low: 3,
  info: 3,
};

/** Default honeypot target position (Rome, Italy) */
export const HONEYPOT_DEFAULT_POSITION = {
  lat: 41.9028,
  lng: 12.4964,
};

/** Globe region camera presets */
export const REGION_POV: Record<string, { lat: number; lng: number; altitude: number }> = {
  world: { lat: 20, lng: 20, altitude: 2.0 },
  europe: { lat: 50, lng: 15, altitude: 1.0 },
  americas: { lat: 35, lng: -95, altitude: 1.0 },
  middleEast: { lat: 28, lng: 45, altitude: 1.1 },
  asiaPacific: { lat: 25, lng: 110, altitude: 1.2 },
  africa: { lat: 5, lng: 20, altitude: 1.2 },
};

/** Globe.gl configuration values */
export const GLOBE_CONFIG = {
  ATMOSPHERE_COLOR: '#64f0c8',
  ATMOSPHERE_ALTITUDE: 0.18,
  AUTO_ROTATE_SPEED: 0.2,
  DAMPING_FACTOR: 0.12,
  GRATICULE_COLOR: 0x2a4a3a,
  GRATICULE_OPACITY: 0.3,
  STARFIELD_COUNT: 1500,
  ARC_DASH_LENGTH: 0.3,
  ARC_DASH_GAP: 0.15,
  ARC_DASH_ANIMATE_TIME: 2500,
  ARC_ALT_AUTO_SCALE: 0.35,
  EARTH_IMG: '//unpkg.com/three-globe@2.33.0/example/img/earth-blue-marble.jpg',
  BUMP_IMG: '//unpkg.com/three-globe@2.33.0/example/img/earth-topology.png',
};

/** Flat map configuration */
export const FLAT_MAP_CONFIG = {
  COUNTRIES_URL: 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json',
  ZOOM_EXTENT: [1, 12] as [number, number],
  LAND_FILL: 'rgba(100,240,200,0.18)',
  LAND_STROKE: 'rgba(100,240,200,0.35)',
  LAND_HOVER_FILL: 'rgba(100,240,200,0.28)',
  BORDER_STROKE: 'rgba(100,240,200,0.2)',
  GRATICULE_STROKE: 'rgba(100,240,200,0.12)',
  BG_COLOR: '#0a1218',
};

/** Crucix-inspired design tokens */
export const THEME = {
  bg: '#020408',
  panel: 'rgba(6,14,22,0.82)',
  glass: 'rgba(10,20,32,0.55)',
  border: 'rgba(100,240,200,0.12)',
  borderBright: 'rgba(100,240,200,0.3)',
  text: '#e8f4f0',
  dim: '#6a8a82',
  accent: '#64f0c8',
  accent2: '#44ccff',
  warn: '#ffb84c',
  danger: '#ff5f63',
};
