/**
 * FeedTab - CVE Feed Panel
 */

import { AlertTriangle, Eye } from 'lucide-react';
import type { CVERecord, CVEStats } from '../../types';
import { getSeverityClass } from '../utils';

interface FeedTabProps {
  stats: CVEStats | null;
  cves: CVERecord[];
  isLoading: boolean;
  error: string | null;
  onCVESelect: (cve: CVERecord) => void;
}

export const FeedTab = ({ stats, cves, isLoading, error, onCVESelect }: FeedTabProps) => {
  return (
    <main className="cve-content" style={{ maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
      {/* Analytics Cards */}
      <div className="analytics-grid">
        <div className="analytics-card critical">
          <div className="analytics-value">{stats?.critical_count ?? 0}</div>
          <div className="analytics-label">Critical</div>
        </div>
        <div className="analytics-card high">
          <div className="analytics-value">{stats?.high_count ?? 0}</div>
          <div className="analytics-label">High</div>
        </div>
        <div className="analytics-card medium">
          <div className="analytics-value">{stats?.medium_count ?? 0}</div>
          <div className="analytics-label">Medium</div>
        </div>
        <div className="analytics-card low">
          <div className="analytics-value">{stats?.low_count ?? 0}</div>
          <div className="analytics-label">Low</div>
        </div>
      </div>

      {/* CVE Feed */}
      <div className="cyber-card cve-feed-card">
        <div className="cve-feed-header">
          <h2>
            <Eye size={14} /> REAL-TIME CVE FEED
            <span className="live-badge">LIVE</span>
          </h2>
          <span style={{ fontSize: '12px', color: 'var(--cyber-text-muted)' }}>
            Total: {stats?.total_cves ?? 0} CVEs
          </span>
        </div>

        <div className="cve-feed-list" style={{ maxHeight: '600px' }}>
          {isLoading ? (
            <div className="empty-state">
              <div
                className="skeleton"
                style={{ width: '100%', height: '60px', marginBottom: '8px' }}
              />
              <div
                className="skeleton"
                style={{ width: '100%', height: '60px', marginBottom: '8px' }}
              />
              <div className="skeleton" style={{ width: '100%', height: '60px' }} />
            </div>
          ) : cves.length > 0 ? (
            cves.map((cve) => (
              <div key={cve.cve_id} className="cve-item" onClick={() => onCVESelect(cve)}>
                <span className={`severity-badge ${getSeverityClass(cve.severity)}`}>
                  {cve.severity}
                </span>
                <div className="cve-info">
                  <div className="cve-id">{cve.cve_id}</div>
                  <div className="cve-desc">
                    {cve.description?.substring(0, 80) || 'No description'}...
                  </div>
                </div>
                <span className={`cve-score ${getSeverityClass(cve.severity)}`}>
                  {cve.cvss?.base_score?.toFixed(1) ?? '—'}
                </span>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p>No CVEs discovered yet.</p>
              <p style={{ fontSize: '12px' }}>
                Click "INITIATE SCAN" in the Monitor tab to begin hunting.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="cyber-card" style={{ borderColor: 'var(--cyber-critical)' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              color: 'var(--cyber-critical)',
            }}
          >
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        </div>
      )}
    </main>
  );
};
