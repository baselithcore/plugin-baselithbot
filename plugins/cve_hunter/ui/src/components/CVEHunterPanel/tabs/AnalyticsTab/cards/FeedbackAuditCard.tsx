/**
 * FeedbackAuditCard - Feedback Audit Card
 */

import { Activity } from 'lucide-react';
import type { FeedbackAuditItem } from '../../../../api';
import { exportFeedbackCsv } from '../../../csvExport';

interface FeedbackAuditCardProps {
  feedbackAudit: FeedbackAuditItem[];
  filteredFeedback: FeedbackAuditItem[];
  recentFeedback: FeedbackAuditItem[];
  feedbackFilter: 'all' | 'confirmed' | 'false_positive';
  setFeedbackFilter: (value: 'all' | 'confirmed' | 'false_positive') => void;
  feedbackQuery: string;
  setFeedbackQuery: (value: string) => void;
}

export const FeedbackAuditCard = ({
  feedbackAudit,
  filteredFeedback,
  recentFeedback,
  feedbackFilter,
  setFeedbackFilter,
  feedbackQuery,
  setFeedbackQuery,
}: FeedbackAuditCardProps) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span className="glass-card-title">
          <Activity size={16} color="var(--cyber-neon-green)" />
          Feedback Audit
        </span>
        <div className="feedback-actions">
          <select
            className="feedback-filter"
            value={feedbackFilter}
            onChange={(e) =>
              setFeedbackFilter(e.target.value as 'all' | 'confirmed' | 'false_positive')
            }
          >
            <option value="all">All</option>
            <option value="confirmed">Confirmed</option>
            <option value="false_positive">False Positive</option>
          </select>
          <button className="export-btn" onClick={() => exportFeedbackCsv(feedbackAudit)}>
            Export CSV
          </button>
        </div>
      </div>
      <div style={{ padding: '0 15px 10px 15px', color: '#888', fontSize: '11px' }}>
        Recent confirmations and false positives across all signals.
      </div>
      <div className="feedback-search">
        <input
          value={feedbackQuery}
          onChange={(e) => setFeedbackQuery(e.target.value)}
          placeholder="Filter by label, id, or detail..."
        />
        <span className="feedback-count">
          {filteredFeedback.length} / {feedbackAudit.length}
        </span>
      </div>
      <div className="feedback-list">
        {recentFeedback.length > 0 ? (
          recentFeedback.map((item) => (
            <div key={`${item.type}-${item.id}`} className="feedback-item">
              <div className="feedback-main">
                <span className="feedback-label">{item.label || item.type}</span>
                <span className={`finding-feedback ${item.outcome}`}>
                  {item.outcome === 'confirmed' ? 'CONFIRMED' : 'FALSE POSITIVE'}
                </span>
              </div>
              <div className="feedback-meta">
                <span className="feedback-detail">{item.detail || item.id}</span>
                <span className="feedback-time">
                  {item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state-premium compact">
            <div className="empty-state-text">No feedback recorded yet.</div>
          </div>
        )}
      </div>
    </div>
  );
};
