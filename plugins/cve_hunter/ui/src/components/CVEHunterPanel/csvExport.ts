/**
 * CVEHunterPanel - CSV Export Utilities
 */

import type {
  UnifiedFinding,
  DastFinding,
  CVECorrelation,
  FindingCorrelationResponse,
  FeedbackAuditItem,
} from '../api';

/**
 * Escape CSV field values
 */
export const csvEscape = (value: string): string => `"${value.replace(/"/g, '""')}"`;

/**
 * Export data as CSV file
 */
export const exportCsv = (
  filename: string,
  headers: string[],
  rows: Array<Array<string>>
): void => {
  if (!rows.length) return;
  const csv = [headers.join(','), ...rows.map((r) => r.map(csvEscape).join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
};

/**
 * Get current date formatted for CSV filename
 */
export const csvDate = (): string => new Date().toISOString().slice(0, 10);

/**
 * Export feedback audit to CSV
 */
export const exportFeedbackCsv = (feedbackAudit: FeedbackAuditItem[]): void => {
  const header = ['timestamp', 'type', 'label', 'outcome', 'detail', 'id'];
  const rows = feedbackAudit.map((item) => [
    item.timestamp || '',
    item.type || '',
    item.label || '',
    item.outcome || '',
    item.detail || '',
    item.id || '',
  ]);
  exportCsv(`cve_hunter_feedback_${csvDate()}.csv`, header, rows);
};

/**
 * Export unified findings to CSV
 */
export const exportUnifiedFindingsCsv = (unifiedFindings: UnifiedFinding[]): void => {
  const header = [
    'finding_id',
    'source_type',
    'engine',
    'location',
    'pattern',
    'severity',
    'confidence',
    'score',
    'cwe_ids',
    'rule_id',
    'feedback',
  ];
  const rows = unifiedFindings.map((item) => [
    item.finding_id,
    item.source_type,
    item.engine || '',
    item.location,
    item.pattern,
    item.severity,
    item.confidence.toString(),
    item.score.toString(),
    item.cwe_ids.join('|'),
    item.rule_id || '',
    item.feedback || '',
  ]);
  exportCsv(`cve_hunter_unified_findings_${csvDate()}.csv`, header, rows);
};

/**
 * Export DAST findings to CSV
 */
export const exportDastFindingsCsv = (dastFindings: DastFinding[]): void => {
  const header = [
    'finding_id',
    'url',
    'pattern',
    'severity',
    'confidence',
    'engine',
    'rule_id',
    'feedback',
  ];
  const rows = dastFindings.map((item) => [
    item.finding_id,
    item.url,
    item.pattern,
    item.severity,
    item.confidence.toString(),
    item.engine || '',
    item.rule_id || '',
    item.feedback || '',
  ]);
  exportCsv(`cve_hunter_dast_findings_${csvDate()}.csv`, header, rows);
};

/**
 * Export CVE correlations to CSV
 */
export const exportCorrelationsCsv = (correlations: CVECorrelation[]): void => {
  const header = [
    'correlation_id',
    'correlation_type',
    'cve_ids',
    'confidence',
    'description',
    'severity',
    'feedback',
  ];
  const rows = correlations.map((item) => [
    item.correlation_id,
    item.correlation_type,
    item.cve_ids.join('|'),
    item.confidence.toString(),
    item.description,
    item.severity,
    item.feedback || '',
  ]);
  exportCsv(`cve_hunter_cve_correlations_${csvDate()}.csv`, header, rows);
};

/**
 * Export finding correlations to CSV
 */
export const exportFindingCorrelationsCsv = (
  findingCorrelations: FindingCorrelationResponse | null
): void => {
  const header = [
    'type',
    'id',
    'name',
    'cve_id',
    'cwe_id',
    'confidence',
    'description',
    'finding_ids',
    'matched_stages',
    'feedback',
  ];
  const rows: Array<Array<string>> = [];
  const cveItems = findingCorrelations?.cve_correlations ?? [];
  const chainItems = findingCorrelations?.attack_chain_candidates ?? [];

  cveItems.forEach((item) => {
    rows.push([
      'cve_match',
      item.correlation_id,
      '',
      item.cve_id,
      item.cwe_id,
      item.confidence.toString(),
      item.description,
      item.finding_ids.join('|'),
      '',
      item.feedback || '',
    ]);
  });

  chainItems.forEach((item) => {
    rows.push([
      'attack_chain_candidate',
      item.chain_id,
      item.name,
      '',
      '',
      item.confidence.toString(),
      item.description,
      '',
      JSON.stringify(item.matched_stages),
      item.feedback || '',
    ]);
  });

  exportCsv(`cve_hunter_finding_correlations_${csvDate()}.csv`, header, rows);
};
