import { activityApi } from './activity';
import { engagementsApi } from './engagements';
import { findingsApi } from './findings';
import { fleetApi } from './fleet';
import { graphApi } from './graph';
import { scansApi } from './scans';
import { targetsApi } from './targets';

export const api = {
  getScan: scansApi.getScan,
  listScans: scansApi.listScans,
  listEngagements: engagementsApi.listEngagements,
  getEngagement: engagementsApi.getEngagement,
  createEngagement: engagementsApi.createEngagement,
  updateEngagement: engagementsApi.updateEngagement,
  archiveEngagement: engagementsApi.archiveEngagement,
  quickScan: scansApi.quickScan,
  listFindings: findingsApi.listFindings,
  getAttackSurface: graphApi.getAttackSurface,
  getFindingGraph: graphApi.getFindingGraph,
  exportSarif: findingsApi.exportSarif,
  exportOcsf: findingsApi.exportOcsf,
  scanSigmaBundleUrl: findingsApi.scanSigmaBundleUrl,
  engagementSigmaBundleUrl: findingsApi.engagementSigmaBundleUrl,
  findingSigmaUrlWithOverrides: findingsApi.findingSigmaUrlWithOverrides,
  exportCompliance: findingsApi.exportCompliance,
  autoRemediateFinding: findingsApi.autoRemediateFinding,
  getFindingEvidence: findingsApi.getFindingEvidence,
  findingSigmaUrl: findingsApi.findingSigmaUrl,
  governanceStats: activityApi.governanceStats,
  governanceTrend: activityApi.governanceTrend,
  listActivity: activityApi.listActivity,
  preflight: scansApi.preflight,
  createScan: scansApi.createScan,
  approveScan: scansApi.approveScan,
  rejectScan: scansApi.rejectScan,
  cancelScan: scansApi.cancelScan,
  deleteScan: scansApi.deleteScan,

  // ── Targets (project-as-entity) ────────────────────────────────────
  listTargets: targetsApi.listTargets,
  getTarget: targetsApi.getTarget,
  getTargetPosture: targetsApi.getTargetPosture,
  listTargetScans: targetsApi.listTargetScans,
  listTargetActivity: targetsApi.listTargetActivity,
  diffRuns: targetsApi.diffRuns,
  createTarget: targetsApi.createTarget,
  updateTarget: targetsApi.updateTarget,
  launchTargetScan: targetsApi.launchTargetScan,
  deleteTarget: targetsApi.deleteTarget,

  // ── Binary / file scans ───────────────────────────────────────────
  uploadFileForScan: targetsApi.uploadFileForScan,
  getSampleInfo: targetsApi.getSampleInfo,
  purgeSample: targetsApi.purgeSample,

  // ── Finding triage ────────────────────────────────────────────────
  updateFinding: findingsApi.updateFinding,

  // ── Fleet (endpoint daemons) ──────────────────────────────────────
  listFleet: fleetApi.listFleet,
  getAgent: fleetApi.getAgent,
  listAgentTelemetry: fleetApi.listAgentTelemetry,
  listFleetTelemetry: fleetApi.listFleetTelemetry,
  createEnrollmentToken: fleetApi.createEnrollmentToken,
};
