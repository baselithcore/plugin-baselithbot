/**
 * CVE Correlations Panel
 * Displays enriched CVE correlation data from Honeypot + CVE Hunter integration
 */

import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, TrendingUp, ExternalLink, X } from 'lucide-react';
import './CVECorrelationsPanel.css';

interface CVEDetail {
  cve_id: string;
  title: string;
  description: string;
  severity: string;
  cvss: number | null;
  source: string;
  published_date: string | null;
  affected_products: string[];
  references: string[];
  cwe_ids: string[];
  exploit_available: boolean;
  patch_available: boolean;
  ai_summary: string | null;
}

interface EnrichedCorrelation {
  cve_id: string;
  cve_detail: CVEDetail;
  attack_count: number;
  related_attacks: Array<{
    event_id: string;
    category: string;
    confidence: number;
    timestamp: string;
    source_ip: string;
  }>;
}

interface CVECorrelationsPanelProps {
  onClose: () => void;
}

const CVECorrelationsPanel: React.FC<CVECorrelationsPanelProps> = ({ onClose }) => {
  const [correlations, setCorrelations] = useState<EnrichedCorrelation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCVE, setSelectedCVE] = useState<EnrichedCorrelation | null>(null);

  useEffect(() => {
    fetchEnrichedCorrelations();
  }, []);

  const fetchEnrichedCorrelations = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/honeypot/cve-correlations/enriched?limit=50');
      const data = await response.json();
      setCorrelations(data.items || []);
    } catch (err) {
      setError('Failed to load CVE correlations');
      console.error('Error fetching CVE correlations:', err);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: '#ff3366',
      high: '#ff6b35',
      medium: '#ffbe0b',
      low: '#00b4d8',
      info: '#45aaf2',
    };
    return colors[severity.toLowerCase()] || '#8892b0';
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="cve-correlations-panel">
        <div className="panel-header">
          <h2>
            <Shield size={24} /> CVE Correlations
          </h2>
          <button onClick={onClose} className="close-btn">
            <X size={20} />
          </button>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading CVE correlations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cve-correlations-panel">
        <div className="panel-header">
          <h2>
            <Shield size={24} /> CVE Correlations
          </h2>
          <button onClick={onClose} className="close-btn">
            <X size={20} />
          </button>
        </div>
        <div className="error-state">
          <AlertTriangle size={48} color="#ff4757" />
          <p>{error}</p>
          <button onClick={fetchEnrichedCorrelations} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="cve-correlations-panel">
      <div className="panel-header">
        <div>
          <h2>
            <Shield size={24} /> CVE Correlations
          </h2>
          <p className="panel-subtitle">
            ATLAS attacks matched with known vulnerabilities from CVE Hunter
          </p>
        </div>
        <button onClick={onClose} className="close-btn">
          <X size={20} />
        </button>
      </div>

      {correlations.length === 0 ? (
        <div className="empty-state">
          <Shield size={64} color="#8892b0" />
          <h3>No CVE Correlations Found</h3>
          <p>Start capturing attacks to see CVE correlations appear here</p>
        </div>
      ) : (
        <div className="correlations-grid">
          {correlations.map((corr) => (
            <div
              key={corr.cve_id}
              className="correlation-card"
              onClick={() => setSelectedCVE(corr)}
            >
              <div className="card-header">
                <div className="cve-badge">
                  <span className="cve-id">{corr.cve_id}</span>
                  <span
                    className="severity-badge"
                    style={{
                      background: getSeverityColor(corr.cve_detail.severity),
                    }}
                  >
                    {corr.cve_detail.severity.toUpperCase()}
                  </span>
                </div>
                {corr.cve_detail.cvss && (
                  <div className="cvss-score">CVSS: {corr.cve_detail.cvss.toFixed(1)}</div>
                )}
              </div>

              <h3 className="cve-title">{corr.cve_detail.title}</h3>
              <p className="cve-description">{corr.cve_detail.description.substring(0, 120)}...</p>

              <div className="card-stats">
                <div className="stat">
                  <TrendingUp size={16} />
                  <span>{corr.attack_count} attacks</span>
                </div>
                {corr.cve_detail.exploit_available && (
                  <div className="stat exploit">
                    <AlertTriangle size={16} />
                    <span>Exploit Available</span>
                  </div>
                )}
              </div>

              {corr.cve_detail.affected_products.length > 0 && (
                <div className="affected-products">
                  <strong>Affects:</strong>{' '}
                  {corr.cve_detail.affected_products.slice(0, 2).join(', ')}
                  {corr.cve_detail.affected_products.length > 2 && '...'}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedCVE && (
        <div className="cve-detail-modal-overlay" onClick={() => setSelectedCVE(null)}>
          <div className="cve-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>{selectedCVE.cve_id}</h2>
                <span
                  className="severity-badge"
                  style={{
                    background: getSeverityColor(selectedCVE.cve_detail.severity),
                  }}
                >
                  {selectedCVE.cve_detail.severity.toUpperCase()}
                </span>
              </div>
              <button onClick={() => setSelectedCVE(null)} className="close-btn">
                <X size={20} />
              </button>
            </div>

            <div className="modal-content">
              <section>
                <h3>Description</h3>
                <p>{selectedCVE.cve_detail.description}</p>
              </section>

              {selectedCVE.cve_detail.ai_summary && (
                <section>
                  <h3>AI Analysis</h3>
                  <p className="ai-summary">{selectedCVE.cve_detail.ai_summary}</p>
                </section>
              )}

              <section>
                <h3>Attack Correlation</h3>
                <div className="attack-stats">
                  <div className="stat-box">
                    <span className="stat-value">{selectedCVE.attack_count}</span>
                    <span className="stat-label">Total Attacks</span>
                  </div>
                  <div className="stat-box">
                    <span className="stat-value">
                      {new Set(selectedCVE.related_attacks.map((a) => a.source_ip)).size}
                    </span>
                    <span className="stat-label">Unique IPs</span>
                  </div>
                </div>
              </section>

              <section>
                <h3>Recent Related Attacks</h3>
                <div className="attacks-list">
                  {selectedCVE.related_attacks.map((attack) => (
                    <div key={attack.event_id} className="attack-item">
                      <div className="attack-header">
                        <span className="attack-category">{attack.category}</span>
                        <span className="attack-confidence">
                          {(attack.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <div className="attack-details">
                        <span>IP: {attack.source_ip}</span>
                        <span>{formatDate(attack.timestamp)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {selectedCVE.cve_detail.references.length > 0 && (
                <section>
                  <h3>References</h3>
                  <div className="references-list">
                    {selectedCVE.cve_detail.references.slice(0, 5).map((ref, idx) => (
                      <a
                        key={idx}
                        href={ref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="reference-link"
                      >
                        <ExternalLink size={14} />
                        {new URL(ref).hostname}
                      </a>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CVECorrelationsPanel;
