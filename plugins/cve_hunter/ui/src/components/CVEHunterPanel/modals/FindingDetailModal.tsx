import { X, Calendar, Server, Activity, Search } from 'lucide-react';
import { UnifiedFinding, DastFinding } from '../../api';
import '../CVEHunterPanel.css';

interface FindingDetailModalProps {
  finding: UnifiedFinding | DastFinding;
  onClose: () => void;
}

const FindingDetailModal = ({ finding, onClose }: FindingDetailModalProps) => {
  // Use 'score' as discriminator since DastFinding doesn't have it
  const isUnified = (f: UnifiedFinding | DastFinding): f is UnifiedFinding => {
    return (f as UnifiedFinding).score !== undefined;
  };

  const getTitle = () => {
    return finding.pattern || 'Finding Details';
  };

  const getLocation = () => {
    if (isUnified(finding)) return finding.location;
    return (finding as DastFinding).url || 'N/A';
  };

  const getScore = () => {
    if (isUnified(finding)) return finding.score.toFixed(1);
    return ((finding as DastFinding).confidence * 100).toFixed(0) + '%';
  };

  return (
    <div className="cve-modal-backdrop" onClick={onClose}>
      <div className="cve-modal-content premium-modal" onClick={(e) => e.stopPropagation()}>
        <header className="cve-modal-header glass-header">
          <div className="header-left">
            <div className="chain-icon-badge">
              {isUnified(finding) ? (
                <Search size={20} className={finding.severity.toLowerCase()} />
              ) : (
                <Activity size={20} className={finding.severity.toLowerCase()} />
              )}
            </div>
            <div>
              <div className="overline">
                {isUnified(finding) ? 'Unified Finding' : 'DAST Finding'}
              </div>
              <h2>{getTitle()}</h2>
            </div>
          </div>

          <div className="header-right">
            <div className={`severity-badge-large ${finding.severity.toLowerCase()}`}>
              <div className="cvss-score-circle">
                <span className="value">{getScore()}</span>
              </div>
              <div className="cvss-label-group">
                <span className="label">{isUnified(finding) ? 'SCORE' : 'CONFIDENCE'}</span>
                <span className="cvss-vector-preview">{finding.engine}</span>
              </div>
            </div>
            <button className="cve-modal-close-premium" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="cve-modal-body">
          <div className="modal-grid">
            {/* Left Column: Description */}
            <div className="modal-col-left">
              <section className="cve-section">
                <h3>Description</h3>
                <p className="description-text">
                  {/* UnifiedFinding/DastFinding doesn't have a direct description field in the snippet I saw,
                      but likely has one or we construct it. Using pattern/location as fallback */}
                  Finding detected by <strong>{finding.engine || 'Unknown Engine'}</strong>.
                  <br />
                  Pattern: {getTitle()}
                  {finding.context && (
                    <>
                      <br />
                      <br />
                      <strong>Context:</strong>
                      <pre
                        className="code-block"
                        style={{
                          marginTop: '8px',
                          padding: '8px',
                          background: 'rgba(0,0,0,0.3)',
                          borderRadius: '4px',
                          overflowX: 'auto',
                        }}
                      >
                        {finding.context}
                      </pre>
                    </>
                  )}
                </p>
              </section>

              {/* Render AI Summary if available (UnifiedFinding/DastFinding might not have it yet, but keeping structure) */}
              {/*
              <section className="cve-section">
                <h3>Analysis</h3>
                 ...
              </section>
              */}
            </div>

            {/* Right Column: Metadata */}
            <div className="modal-col-right">
              <section className="cve-section">
                <h3>Metadata</h3>
                <div className="cve-meta-grid-vertical">
                  <div className="cve-meta-item">
                    <Calendar size={16} />
                    <div>
                      <label>Detected At</label>
                      <span>
                        {/* Assuming there might be a date field or using current date if missing from interface view */}
                        N/A
                      </span>
                    </div>
                  </div>

                  <div className="cve-meta-item">
                    <Server size={16} />
                    <div>
                      <label>Location</label>
                      <span style={{ wordBreak: 'break-all', fontSize: '12px' }}>
                        {getLocation()}
                      </span>
                    </div>
                  </div>

                  {isUnified(finding) && finding.cwe_ids && finding.cwe_ids.length > 0 && (
                    <div className="cve-meta-item">
                      <Activity size={16} />
                      <div>
                        <label>CWE IDs</label>
                        <div className="tags-list">
                          {finding.cwe_ids.map((id: string) => (
                            <span key={id} className="tech-tag">
                              {id}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="cve-meta-item">
                    <Activity size={16} />
                    <div>
                      <label>Engine</label>
                      <span className="tech-tag">{finding.engine}</span>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FindingDetailModal;
