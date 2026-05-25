/**
 * CorrelationsCard - CVE Correlations Card
 */

import { Bug } from 'lucide-react';
import type { CVECorrelation } from '../../../../api';
import { exportCorrelationsCsv } from '../../../csvExport';

interface CorrelationsCardProps {
  correlations: CVECorrelation[];
  handleClassicCorrelationFeedback: (
    correlationId: string,
    outcome: 'confirmed' | 'false_positive'
  ) => void;
}

export const CorrelationsCard = ({
  correlations,
  handleClassicCorrelationFeedback,
}: CorrelationsCardProps) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span className="glass-card-title">
          <Bug size={16} color="var(--cyber-neon-green)" />
          CVE Correlations
        </span>
        <div className="card-actions">
          <button className="export-btn" onClick={() => exportCorrelationsCsv(correlations)}>
            Export CSV
          </button>
        </div>
      </div>
      <div style={{ padding: '0 15px 10px 15px', color: '#888', fontSize: '11px' }}>
        Relationships discovered through semantic analysis and CWE matching.
      </div>
      <div className="correlation-list">
        {correlations.length > 0 ? (
          correlations.map((correlation) => (
            <div key={correlation.correlation_id} className="correlation-item">
              <div className="correlation-type">
                {correlation.correlation_type.replace('_', ' ').toUpperCase()}
              </div>
              <div className="correlation-desc">
                {correlation.cve_ids.length} CVEs: {correlation.description}
              </div>
              <span className="correlation-confidence">
                {(correlation.confidence * 100).toFixed(0)}% confidence
              </span>
              {correlation.feedback && (
                <span className={`finding-feedback ${correlation.feedback}`}>
                  {correlation.feedback === 'confirmed' ? 'CONFIRMED' : 'FALSE POSITIVE'}
                </span>
              )}
              {!correlation.feedback && (
                <div className="finding-actions">
                  <button
                    className="finding-action confirm"
                    onClick={() =>
                      handleClassicCorrelationFeedback(correlation.correlation_id, 'confirmed')
                    }
                  >
                    Confirm
                  </button>
                  <button
                    className="finding-action reject"
                    onClick={() =>
                      handleClassicCorrelationFeedback(correlation.correlation_id, 'false_positive')
                    }
                  >
                    False Positive
                  </button>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="empty-state-premium">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-text">No correlations found yet.</div>
          </div>
        )}
      </div>
    </div>
  );
};
