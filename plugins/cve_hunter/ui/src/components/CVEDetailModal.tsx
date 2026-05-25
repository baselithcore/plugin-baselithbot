import { X, Shield, Calendar, Server, Activity, BarChart2 } from 'lucide-react';
import { CVERecord } from './types';
import ReactMarkdown from 'react-markdown';
import { useState } from 'react';
import { analyzeCVE } from './api';
import './CVEHunterPanel/CVEHunterPanel.css';
import { parseCVSSVector } from './CVEHunterPanel/utils';

interface CVEDetailModalProps {
  cve: CVERecord;
  onClose: () => void;
}

const CVEDetailModal = ({ cve: initialCVE, onClose }: CVEDetailModalProps) => {
  const [cve, setCve] = useState<CVERecord>(initialCVE);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      const updatedCVE = await analyzeCVE(cve.cve_id);
      setCve(updatedCVE);
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="cve-modal-backdrop" onClick={onClose}>
      <div className="cve-modal-content premium-modal" onClick={(e) => e.stopPropagation()}>
        <header className="cve-modal-header glass-header">
          <div className="header-left">
            <div className="chain-icon-badge">
              <Shield size={20} className={cve.severity.toLowerCase()} />
            </div>
            <div>
              <div className="overline">Vulnerability Details</div>
              <h2>{cve.cve_id}</h2>
            </div>
          </div>

          <div className="header-right">
            <div className={`severity-badge-large ${cve.severity.toLowerCase()}`}>
              <div className="cvss-score-circle">
                <span className="value">{cve.cvss?.base_score ?? 'N/A'}</span>
              </div>
              <div className="cvss-label-group">
                <span className="label">CVSS SCORE</span>
                <span className="cvss-vector-preview">{cve.cvss?.version ?? 'v3.1'}</span>
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
                <p className="description-text">{cve.description}</p>
              </section>

              <section className="cve-section">
                <h3>References</h3>
                <div className="references-list">
                  {cve.references?.slice(0, 3).map((ref, i) => (
                    <a
                      key={i}
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="reference-link"
                    >
                      {ref.url}
                    </a>
                  ))}
                </div>
              </section>
            </div>

            {/* Right Column: Metadata */}
            <div className="modal-col-right">
              <section className="cve-section">
                <h3>Metadata</h3>
                <div className="cve-meta-grid-vertical">
                  <div className="cve-meta-item">
                    <Calendar size={16} />
                    <div>
                      <label>Published</label>
                      <span>
                        {cve.published_date
                          ? new Date(cve.published_date).toLocaleDateString()
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                  {cve.cwe_ids && cve.cwe_ids.length > 0 && (
                    <div className="cve-meta-item">
                      <Activity size={16} />
                      <div>
                        <label>CWE IDs</label>
                        <div className="tags-list">
                          {cve.cwe_ids.map((id) => (
                            <span key={id} className="tech-tag">
                              {id}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  <div className="cve-meta-item">
                    <Server size={16} />
                    <div>
                      <label>Affected Products</label>
                      <div className="tags-list">
                        {cve.affected_products?.slice(0, 5).map((prod, i) => (
                          <span key={i} className="tech-tag">
                            {prod.product}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>

          {/* Bottom Section: AI Analysis & CVSS Metrics */}
          <div className="modal-bottom-section">
            {/* CVSS Metrics Grid */}
            {cve.cvss?.vector_string && (
              <section className="cve-section full-width cvss-metrics-section">
                <h3>
                  <BarChart2 size={16} /> CVSS v3.1 Metrics
                </h3>
                <div className="cvss-metrics-grid">
                  {parseCVSSVector(cve.cvss.vector_string).map((metric, i) => (
                    <div key={i} className="cvss-metric-card">
                      <span className="cvss-metric-label">{metric.label}</span>
                      <span className="cvss-metric-value" style={{ color: metric.color }}>
                        {metric.value}
                      </span>
                      <div className="cvss-metric-bar">
                        <div
                          className="cvss-metric-fill"
                          style={{
                            width: '100%',
                            backgroundColor: metric.color,
                            opacity: 0.3,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="cve-section ai-analysis-wrapper full-width">
              <div className="ai-header">
                <h3>
                  <Activity size={16} /> AI Remediation & Analysis
                </h3>
                {(!cve.ai_summary || isAnalyzing) && !isAnalyzing && (
                  <button className="mini-analyze-btn" onClick={handleAnalyze}>
                    Analyze with AI
                  </button>
                )}
              </div>

              <div className="ai-content-box full-height">
                {isAnalyzing ? (
                  <div className="loader-container">
                    <div className="loader-spin" />
                    <span className="blink">Analyzing Vulnerability...</span>
                  </div>
                ) : cve.ai_summary ? (
                  <div className="markdown-body premium-md">
                    <ReactMarkdown>{cve.ai_summary}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="empty-analysis">
                    <p>Run AI analysis to get a remediation plan and impact assessment.</p>
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CVEDetailModal;
