import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { X, Shield, Calendar, Server, Activity, BarChart2, ExternalLink } from 'lucide-react';
import type { CVERecord } from './types';
import { analyzeCVE } from './api';
import { parseCVSSVector } from './utils';
import './HoneypotPanel.css'; // Reusing panel styles for consistency

interface CVEDetailModalProps {
  cve: CVERecord;
  onClose: () => void;
}

const CVEDetailModal: React.FC<CVEDetailModalProps> = ({ cve: initialCVE, onClose }) => {
  const [cve, setCve] = useState<CVERecord>(initialCVE);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Sync state with props when parent updates the CVE record (e.g. after loading)
  React.useEffect(() => {
    setCve(initialCVE);
  }, [initialCVE]);

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
    <div className="hp-modal-overlay" onClick={onClose} style={{ zIndex: 9999 }}>
      <div
        className="hp-modal-content premium-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '900px',
          maxWidth: '95vw',
          background: '#13131f',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <header
          className="hp-modal-header"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '20px',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
          }}
        >
          <div
            className="header-left"
            style={{ display: 'flex', gap: '16px', alignItems: 'center' }}
          >
            <div
              className={`chain-icon-badge ${cve.severity.toLowerCase()}`}
              style={{
                width: 48,
                height: 48,
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: `rgba(var(--severity-${cve.severity.toLowerCase()}-rgb), 0.1)`,
                color: `var(--severity-${cve.severity.toLowerCase()})`,
              }}
            >
              <Shield size={24} />
            </div>
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: '#8892b0',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Vulnerability Details
              </div>
              <h2 style={{ margin: 0, fontSize: '1.5rem' }}>{cve.cve_id}</h2>
            </div>
          </div>

          <div
            className="header-right"
            style={{ display: 'flex', alignItems: 'center', gap: '16px' }}
          >
            <div
              className={`severity-badge-large ${cve.severity.toLowerCase()}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '8px 16px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
              }}
            >
              <div
                className="cvss-score-circle"
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  border: `2px solid var(--severity-${cve.severity.toLowerCase()})`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                }}
              >
                {cve.cvss?.base_score ?? 'N/A'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.7rem', color: '#8892b0' }}>CVSS SCORE</span>
                <span
                  className="cvss-vector-preview"
                  style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}
                >
                  {cve.cvss?.version ?? 'v3.1'}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#8892b0',
                cursor: 'pointer',
                padding: 8,
              }}
            >
              <X size={24} />
            </button>
          </div>
        </header>

        <div
          className="cve-modal-body"
          style={{ padding: '24px', overflowY: 'auto', maxHeight: 'calc(80vh - 90px)' }}
        >
          <div
            className="modal-grid"
            style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}
          >
            {/* Left Column: Description */}
            <div className="modal-col-left">
              <section className="cve-section" style={{ marginBottom: '24px' }}>
                <h3
                  style={{
                    fontSize: '1rem',
                    color: '#fff',
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  Description
                </h3>
                <p className="description-text" style={{ lineHeight: 1.6, color: '#bdc3c7' }}>
                  {cve.description}
                </p>
              </section>

              <section className="cve-section">
                <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '12px' }}>
                  References
                </h3>
                <div
                  className="references-list"
                  style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}
                >
                  {cve.references?.slice(0, 3).map((ref, i) => (
                    <a
                      key={i}
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="reference-link"
                      style={{
                        color: '#3498db',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      <ExternalLink size={14} /> {ref.url}
                    </a>
                  ))}
                </div>
              </section>
            </div>

            {/* Right Column: Metadata */}
            <div className="modal-col-right">
              <section
                className="cve-section"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  padding: '16px',
                  borderRadius: '8px',
                }}
              >
                <h3
                  style={{
                    fontSize: '0.9rem',
                    color: '#8892b0',
                    marginBottom: '16px',
                    textTransform: 'uppercase',
                  }}
                >
                  Metadata
                </h3>
                <div
                  className="cve-meta-grid-vertical"
                  style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
                >
                  <div
                    className="cve-meta-item"
                    style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}
                  >
                    <Calendar size={16} color="#8892b0" />
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#8892b0' }}>
                        Published
                      </label>
                      <span style={{ color: '#fff' }}>
                        {cve.published_date
                          ? new Date(cve.published_date).toLocaleDateString()
                          : 'N/A'}
                      </span>
                    </div>
                  </div>
                  {cve.cwe_ids && cve.cwe_ids.length > 0 && (
                    <div
                      className="cve-meta-item"
                      style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}
                    >
                      <Activity size={16} color="#8892b0" />
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', color: '#8892b0' }}>
                          CWE IDs
                        </label>
                        <div
                          className="tags-list"
                          style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '4px',
                            marginTop: '4px',
                          }}
                        >
                          {cve.cwe_ids.map((id) => (
                            <span
                              key={id}
                              className="tech-tag"
                              style={{
                                fontSize: '0.75rem',
                                padding: '2px 6px',
                                background: 'rgba(255,255,255,0.1)',
                                borderRadius: '4px',
                              }}
                            >
                              {id}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  <div
                    className="cve-meta-item"
                    style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}
                  >
                    <Server size={16} color="#8892b0" />
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#8892b0' }}>
                        Affected Products
                      </label>
                      <div
                        className="tags-list"
                        style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}
                      >
                        {cve.affected_products?.slice(0, 5).map((prod, i) => (
                          <span
                            key={i}
                            className="tech-tag"
                            style={{
                              fontSize: '0.75rem',
                              padding: '2px 6px',
                              background: 'rgba(255,255,255,0.1)',
                              borderRadius: '4px',
                            }}
                          >
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
          <div
            className="modal-bottom-section"
            style={{
              marginTop: '32px',
              borderTop: '1px solid rgba(255,255,255,0.05)',
              paddingTop: '24px',
            }}
          >
            {/* CVSS Metrics Grid */}
            {cve.cvss?.vector_string && (
              <section
                className="cve-section full-width cvss-metrics-section"
                style={{ marginBottom: '24px' }}
              >
                <h3
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: '1rem',
                    marginBottom: '16px',
                  }}
                >
                  <BarChart2 size={16} /> CVSS v3.1 Metrics
                </h3>
                <div
                  className="cvss-metrics-grid"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: '12px',
                  }}
                >
                  {parseCVSSVector(cve.cvss.vector_string).map((metric, i) => (
                    <div
                      key={i}
                      className="cvss-metric-card"
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        padding: '10px',
                        borderRadius: '6px',
                      }}
                    >
                      <span
                        className="cvss-metric-label"
                        style={{
                          display: 'block',
                          fontSize: '0.7rem',
                          color: '#8892b0',
                          marginBottom: '4px',
                        }}
                      >
                        {metric.label}
                      </span>
                      <span
                        className="cvss-metric-value"
                        style={{ color: metric.color, fontWeight: 'bold', display: 'block' }}
                      >
                        {metric.value}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="cve-section ai-analysis-wrapper full-width">
              <div
                className="ai-header"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '16px',
                }}
              >
                <h3
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: '1rem',
                    color: '#a55eea',
                  }}
                >
                  <Activity size={16} /> AI Remediation & Analysis
                </h3>
                {(!cve.ai_summary || isAnalyzing) && !isAnalyzing && (
                  <button
                    className="mini-analyze-btn"
                    onClick={handleAnalyze}
                    style={{
                      background: '#a55eea',
                      color: '#fff',
                      border: 'none',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                    }}
                  >
                    Analyze with AI
                  </button>
                )}
              </div>

              <div
                className="ai-content-box full-height"
                style={{
                  background: 'rgba(165, 94, 234, 0.05)',
                  padding: '16px',
                  borderRadius: '8px',
                  border: '1px solid rgba(165, 94, 234, 0.15)',
                }}
              >
                {isAnalyzing ? (
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a55eea' }}
                  >
                    <span className="blink">Analyzing Vulnerability...</span>
                  </div>
                ) : cve.ai_summary ? (
                  <div
                    className="markdown-body premium-md"
                    style={{ color: '#e0e0e0', lineHeight: 1.6 }}
                  >
                    <ReactMarkdown>{cve.ai_summary}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="empty-analysis" style={{ color: '#8892b0', fontStyle: 'italic' }}>
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
