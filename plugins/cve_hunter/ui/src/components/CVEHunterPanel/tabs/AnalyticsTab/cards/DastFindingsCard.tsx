/**
 * DastFindingsCard - DAST Findings Card
 */

import { Terminal } from 'lucide-react';
import type { DastFinding } from '../../../../api';
import { getSeverityClass, truncateText } from '../../../utils';
import { exportDastFindingsCsv } from '../../../csvExport';

interface DastFindingsCardProps {
  dastFindings: DastFinding[];
  topDastFindings: DastFinding[];
  handleDastFeedback: (findingId: string, outcome: 'confirmed' | 'false_positive') => void;
  onFindingClick: (finding: DastFinding) => void;
}

export const DastFindingsCard = ({
  dastFindings,
  topDastFindings,
  handleDastFeedback,
  onFindingClick,
}: DastFindingsCardProps) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span className="glass-card-title">
          <Terminal size={16} color="var(--cyber-neon-cyan)" />
          DAST Findings
        </span>
        <div className="card-actions">
          <button className="export-btn" onClick={() => exportDastFindingsCsv(dastFindings)}>
            Export CSV
          </button>
          <span className="glass-card-badge">LIVE</span>
        </div>
      </div>
      <div style={{ padding: '0 15px 10px 15px', color: '#888', fontSize: '11px' }}>
        Dynamic scan signals from crawler and ZAP integrations.
      </div>
      <div className="finding-list">
        {topDastFindings.length > 0 ? (
          topDastFindings.map((finding) => (
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
                <span className="finding-location">{truncateText(finding.url, 64)}</span>
                <span className="finding-score">
                  {(finding.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <div className="finding-tags">
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
                      handleDastFeedback(finding.finding_id, 'confirmed');
                    }}
                  >
                    Confirm
                  </button>
                  <button
                    className="finding-action reject"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDastFeedback(finding.finding_id, 'false_positive');
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
            <div className="empty-state-icon">📡</div>
            <div className="empty-state-text">No DAST findings yet.</div>
          </div>
        )}
      </div>
    </div>
  );
};
