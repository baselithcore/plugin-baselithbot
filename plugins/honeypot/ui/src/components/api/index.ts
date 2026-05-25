/**
 * Honeypot API Client - Barrel Export
 * Centralized export for all API modules
 */

// Core utilities (exported for advanced use cases)
export { honeypotApiFetch, normalizeIpDisplay } from './core';
export { getAuthHeaders, refreshAccessToken } from './auth';

// Honeypot registry & management
export {
  fetchStatus,
  fetchStats,
  startHoneypot,
  stopHoneypot,
  fetchHoneypots,
  fetchHoneypot,
  fetchHoneypotEvents,
  fetchHoneypotAttackers,
} from './honeypots';

// Events & sessions
export {
  fetchEvents,
  fetchEventDetail,
  fetchSessions,
  fetchSessionDetail,
  fetchLogs,
  analyzeEvent,
  analyzeSession,
  fetchCVECorrelations,
  fetchTopAttackers,
  fetchAllAttackers,
  fetchAttackPatterns,
} from './events';

// Geo visualization
export { fetchGeoAttacks } from './geo';
export type { GeoAttack, GeoMarker, GeoAttacksResponse } from './geo';

// Swarm status
export { fetchSwarmStatus } from './swarm';
export type { SwarmHandler, SwarmStatusResponse } from './swarm';

// Streaming
export { fetchStreamStatus, createAttackStream } from './streaming';
export type { StreamStatus } from './streaming';

// Discovery (botnet detection)
export {
  runDiscoveryAnalysis,
  fetchDiscoveryResult,
  fetchDiscoverySummary,
  fetchBotnets,
  fetchHubNodes,
  fetchDiscoveryGraph,
  fetchAnomalies,
} from './discovery';

// Pentesting
export {
  fetchPlaybooks,
  fetchPentestTargets,
  discoverTargets,
  generatePlaybook,
  deletePlaybook,
  fetchPentests,
  fetchPentestDetail,
  triggerPentest,
  updateFindingVerification,
  updateFindingsVerificationBulk,
} from './pentesting';
export type { PlaybookGenerateRequest, PentestTriggerRequest, PentestTarget } from './pentesting';

// Reports
export {
  fetchReportTypes,
  generateReportPreview,
  generateReport,
  downloadMarkdownReport,
  downloadPdfReport,
} from './reports';

// CVE integration
export { fetchCVEDetail, analyzeCVE } from './cve';
