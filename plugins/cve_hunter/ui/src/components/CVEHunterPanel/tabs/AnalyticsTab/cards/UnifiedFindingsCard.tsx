/**
 * UnifiedFindingsCard - Unified SAST/DAST Findings Card
 */

import { Search } from 'lucide-react';
import type { UnifiedFinding } from '../../../../api';
import { getSeverityClass, truncateText } from '../../../utils';
import { exportUnifiedFindingsCsv } from '../../../csvExport';

interface UnifiedFindingsCardProps {
  unifiedFindings: UnifiedFinding[];
  topUnifiedFindings: UnifiedFinding[];
  handleUnifiedFeedback: (findingId: string, outcome: 'confirmed' | 'false_positive') => void;
  onFindingClick: (finding: UnifiedFinding) => void;
}

export const UnifiedFindingsCard = ({
  unifiedFindings,
  topUnifiedFindings,
  handleUnifiedFeedback,
  onFindingClick,
}: UnifiedFindingsCardProps) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span className="glass-card-title">
          <Search size={16} color="var(--cyber-neon-cyan)" />
          Unified Findings
        </span>
        <div className="card-actions">
          <button className="export-btn" onClick={() => exportUnifiedFindingsCsv(unifiedFindings)}>
            Export CSV
          </button>
          <span className="glass-card-badge">SAST/DAST</span>
        </div>
      </div>
      <div style={{ padding: '0 15px 10px 15px', color: '#888', fontSize: '11px' }}>
        Deduplicated findings across static, dynamic, and discovery signals.
      </div>
      <div className="finding-list">
        {topUnifiedFindings.length > 0 ? (
          topUnifiedFindings.map((finding) => (
            <div
              key={finding.finding_id}
              className="finding-item"
              onClick={() => onFindingClick(finding)}
            >
              <div className="finding-header">
                <span className="finding-pattern">{finding.pattern}</span>
                <span className={`severity-badge ${getSeverityClass(finding.severity)}`}>
                  {finding.severity.toUpperCase()}
                </span>
              </div>
              <div className="finding-meta">
                <span className="finding-location">{truncateText(finding.location)}</span>
                <span className="finding-score">Score {finding.score.toFixed(1)}</span>
              </div>
              <div className="finding-tags">
                {finding.cwe_ids.slice(0, 3).map((cwe) => (
                  <span key={cwe} className="cwe-tag">
                    {cwe}
                  </span>
                ))}
                {finding.engine && <span className="finding-engine">{finding.engine}</span>}
                {finding.feedback && (
                  <span className={`finding-feedback ${finding.feedback}`}>
                    {finding.feedback === 'confirmed' ? 'CONFIRMED' : 'FALSE POSITIVE'}
                  </span>
                )}
              </div>
              {!finding.feedback && (
                <div className="finding-actions">
                  <button
                    className="finding-action confirm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUnifiedFeedback(finding.finding_id, 'confirmed');
                    }}
                  >
                    Confirm
                  </button>
                  <button
                    className="finding-action reject"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUnifiedFeedback(finding.finding_id, 'false_positive');
                    }}
                  >
                    False Positive
                  </button>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="empty-state-premium">
            <div className="empty-state-icon">🧭</div>
            <div className="empty-state-text">No unified findings yet.</div>
          </div>
        )}
      </div>
    </div>
  );
};
