/**
 * FindingCorrelationsCard - Finding Correlations Card
 */

import { Eye } from 'lucide-react';
import type { FindingCorrelationResponse } from '../../../../api';
import { exportFindingCorrelationsCsv } from '../../../csvExport';

interface FindingCorrelationsCardProps {
  findingCorrelations: FindingCorrelationResponse | null;
  handleCorrelationFeedback: (
    kind: 'cve' | 'chain',
    id: string,
    outcome: 'confirmed' | 'false_positive'
  ) => void;
}

export const FindingCorrelationsCard = ({
  findingCorrelations,
  handleCorrelationFeedback,
}: FindingCorrelationsCardProps) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span className="glass-card-title">
          <Eye size={16} color="var(--cyber-neon-purple)" />
          Finding Correlations
        </span>
        <div className="card-actions">
          <button
            className="export-btn"
            onClick={() => exportFindingCorrelationsCsv(findingCorrelations)}
          >
            Export CSV
          </button>
        </div>
      </div>
      <div className="finding-summary">
        <div className="finding-summary-item">
          <span className="finding-summary-label">Findings</span>
          <span className="finding-summary-value">
            {findingCorrelations?.summary.total_findings ?? 0}
          </span>
        </div>
        <div className="finding-summary-item">
          <span className="finding-summary-label">CVE Links</span>
          <span className="finding-summary-value">
            {findingCorrelations?.summary.cve_correlations ?? 0}
          </span>
        </div>
        <div className="finding-summary-item">
          <span className="finding-summary-label">Chains</span>
          <span className="finding-summary-value">
            {findingCorrelations?.summary.attack_chain_candidates ?? 0}
          </span>
        </div>
      </div>
      <div className="finding-correlation-section">
        <div className="finding-section-title">CVE Matches</div>
        <div className="finding-correlation-list">
          {findingCorrelations?.cve_correlations?.length ? (
            findingCorrelations.cve_correlations.slice(0, 6).map((item) => (
              <div key={item.correlation_id} className="finding-correlation-item">
                <div className="finding-correlation-title">{item.cve_id}</div>
                <div className="finding-correlation-desc">{item.description}</div>
                <span className="finding-correlation-confidence">
                  {(item.confidence * 100).toFixed(0)}% confidence
                </span>
                {item.feedback && (
                  <span className={`finding-feedback ${item.feedback}`}>
                    {item.feedback === 'confirmed' ? 'CONFIRMED' : 'FALSE POSITIVE'}
                  </span>
                )}
                {!item.feedback && (
                  <div className="finding-actions">
                    <button
                      className="finding-action confirm"
                      onClick={() =>
                        handleCorrelationFeedback('cve', item.correlation_id, 'confirmed')
                      }
                    >
                      Confirm
                    </button>
                    <button
                      className="finding-action reject"
                      onClick={() =>
                        handleCorrelationFeedback('cve', item.correlation_id, 'false_positive')
                      }
                    >
                      False Positive
                    </button>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="empty-state-premium compact">
              <div className="empty-state-text">No CVE matches yet.</div>
            </div>
          )}
        </div>
      </div>
      <div className="finding-correlation-section">
        <div className="finding-section-title">Attack Chain Candidates</div>
        <div className="finding-correlation-list">
          {findingCorrelations?.attack_chain_candidates?.length ? (
            findingCorrelations.attack_chain_candidates.slice(0, 4).map((item) => (
              <div key={item.chain_id} className="finding-correlation-item">
                <div className="finding-correlation-title">{item.name}</div>
                <div className="finding-correlation-desc">{item.description}</div>
                <span className="finding-correlation-confidence">
                  {(item.confidence * 100).toFixed(0)}% confidence
                </span>
                {item.feedback && (
                  <span className={`finding-feedback ${item.feedback}`}>
                    {item.feedback === 'confirmed' ? 'CONFIRMED' : 'FALSE POSITIVE'}
                  </span>
                )}
                {!item.feedback && (
                  <div className="finding-actions">
                    <button
                      className="finding-action confirm"
                      onClick={() => handleCorrelationFeedback('chain', item.chain_id, 'confirmed')}
                    >
                      Confirm
                    </button>
                    <button
                      className="finding-action reject"
                      onClick={() =>
                        handleCorrelationFeedback('chain', item.chain_id, 'false_positive')
                      }
                    >
                      False Positive
                    </button>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="empty-state-premium compact">
              <div className="empty-state-text">No chain candidates yet.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
