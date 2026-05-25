/**
 * GeoUtils Module - Re-export all utilities and data
 */

// Types
export type { ThreatLevel, MeshConnection, GeoMarker } from './types';

// Country data
export { COUNTRY_FLAGS, getCountryFlag } from './countryFlags';
export { COUNTRY_NAMES, getCountryName } from './countryNames';

// Map data
// export { CONTINENT_PATHS } from './continentPaths';

// Utility functions
export {
  getSubnetFromIp,
  calculateMeshConnections,
  getThreatLevel,
  getThreatLevelColor,
  getThreatLevelLabel,
  calculateAttackVelocity,
  formatAttackCount,
  getArcControlPoint,
  getProtocolColor,
  severityGradients,
  protocolColors,
} from './utils';
