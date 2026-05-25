// Barrel — splits per CLAUDE.md §1.2 LOC budget. Domain modules under lib/api/.

export * from './api/types';
export * from './api/documents';
export type { AnalyzeOptions } from './api/documents';
export * from './api/policies';
export * from './api/workspace';
export * from './api/findings';
export * from './api/health';

export type {
  AuditEntry,
  AuditEntryDetail,
  ChainStatus,
  AuditUserOption,
  AuditFilters,
  ListAuditParams,
  ListAuditResult,
} from './api/audit';
export {
  listAudit,
  listAuditPage,
  verifyAuditChain,
  listAuditActions,
  listAuditUsers,
  getAuditEntry,
  exportAuditCsv,
  exportAuditJson,
} from './api/audit';
