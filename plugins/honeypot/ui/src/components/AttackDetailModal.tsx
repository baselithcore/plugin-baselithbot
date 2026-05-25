import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  X,
  Globe,
  Terminal,
  Code,
  Shield,
  Activity,
  Clock,
  MapPin,
  Hash,
  Server,
  AlertTriangle,
  User,
  Key,
  FileText,
  Network,
  Sparkles,
  Play,
  Brain,
  ExternalLink,
} from 'lucide-react';
import type { AttackEvent, CVERecord } from './types';
import { normalizeIpDisplay, analyzeEvent, fetchCVEDetail } from './api';
import CVEDetailModal from './CVEDetailModal';
import CopyButton from './common/CopyButton';
import ExpandableSection from './common/ExpandableSection';
import BotIndicator from './common/BotIndicator';
import { getGeoDisplay, getPayloadContent } from '../utils/detailHelpers';
import './HoneypotPanel.css';

interface AttackDetailModalProps {
  event: AttackEvent;
  onClose: () => void;
}

const AttackDetailModal: React.FC<AttackDetailModalProps> = ({ event, onClose }) => {
  const geoInfo = getGeoDisplay(event);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [localAnalysis, setLocalAnalysis] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [selectedCVE, setSelectedCVE] = useState<CVERecord | null>(null);
  const [loadingCVE, setLoadingCVE] = useState<string | null>(null);

  const payload = getPayloadContent(event);

  const handleAnalyze = async () => {
    try {
      setIsAnalyzing(true);
      setAnalysisError(null);
      const result = await analyzeEvent(event.event_id);
      setLocalAnalysis(result.analysis);
    } catch (err) {
      console.error('Failed to analyze event:', err);
      const errorMessage =
        err instanceof Error ? err.message : 'Analysis failed. Please try again.';
      setAnalysisError(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCVEClick = async (cveId: string) => {
    try {
      setLoadingCVE(cveId);
      const cveData = await fetchCVEDetail(cveId);
      setSelectedCVE(cveData);
    } catch (err) {
      console.error('Failed to fetch CVE details:', err);
    } finally {
      setLoadingCVE(null);
    }
  };

  const aiContent = localAnalysis || event.ai_classification;

  return (
    <div className="hp-modal-overlay" onClick={onClose}>
      <div
        className="hp-premium-modal hp-premium-modal--enhanced"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Glass Header */}
        <header className="hp-glass-header">
          <div className="hp-header-left">
            <div className="hp-icon-badge">
              <Shield size={24} />
            </div>
            <div className="hp-header-info">
              <div className="hp-overline">Attack Detected</div>
              <h2>{event.category.toUpperCase().replace('_', ' ')}</h2>
            </div>
          </div>

          <div className="hp-header-right">
            <div className="hp-severity-badge-large">
              <span className="label">Severity</span>
              <span
                className="value"
                style={{ color: `var(--cyber-${event.severity.toLowerCase()})` }}
              >
                {event.severity.toUpperCase()}
              </span>
            </div>
            <BotIndicator
              isBot={event.is_bot}
              confidence={event.bot_confidence}
              signals={event.bot_signals}
              size="medium"
              showLabel={true}
            />
            <button className="hp-close-btn" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="hp-modal-body">
          <div className="hp-modal-grid">
            {/* Left Column: Source Intelligence */}
            <div className="hp-column-left">
              <ExpandableSection title="Source Intelligence" icon={<Globe size={16} />}>
                <div className="hp-detail-card hp-geo-card">
                  <div className="hp-geo-main">
                    <span className="hp-geo-flag">{geoInfo.flag}</span>
                    <div className="hp-geo-info">
                      <div className="hp-detail-value hp-detail-value--large">
                        {normalizeIpDisplay(event.source_ip)}
                        <CopyButton text={event.source_ip} label="Copy IP" />
                      </div>
                      <div className="hp-detail-label">{geoInfo.location}</div>
                    </div>
                  </div>

                  <div className="hp-geo-tags">
                    <span className="hp-tag">
                      <MapPin size={10} /> {event.geo?.country_code || '??'}
                    </span>
                    {event.geo?.city && (
                      <span className="hp-tag">
                        <MapPin size={10} /> {event.geo.city}
                      </span>
                    )}
                    {geoInfo.isLocal && (
                      <span className="hp-tag hp-tag--local">
                        <Network size={10} /> LAN
                      </span>
                    )}
                  </div>
                </div>
              </ExpandableSection>

              {/* Credentials Section (if applicable) */}
              {(event.username || event.password) && (
                <ExpandableSection title="Captured Credentials" icon={<Key size={16} />}>
                  <div className="hp-credentials-box">
                    {event.username && (
                      <div className="hp-credential-item">
                        <User size={14} />
                        <span className="hp-credential-label">Username</span>
                        <code className="hp-credential-value">{event.username}</code>
                        <CopyButton text={event.username} />
                      </div>
                    )}
                    {event.password && (
                      <div className="hp-credential-item">
                        <Key size={14} />
                        <span className="hp-credential-label">Password</span>
                        <code className="hp-credential-value">{event.password}</code>
                        <CopyButton text={event.password} />
                      </div>
                    )}
                  </div>
                </ExpandableSection>
              )}

              {/* Technical Evidence Section */}
              <ExpandableSection title="Technical Evidence" icon={<Code size={16} />}>
                <div className="hp-payload-box">
                  <div className="hp-payload-header">
                    <span className="hp-overline">
                      {payload.type === 'command' && 'Captured Command'}
                      {payload.type === 'http' && 'HTTP Request'}
                      {payload.type === 'raw' && 'Raw Payload'}
                      {payload.type === 'none' && 'Payload'}
                    </span>
                    {payload.content && payload.type !== 'none' && (
                      <CopyButton text={payload.content} label="Copy payload" />
                    )}
                  </div>
                  <div className="hp-payload-content hp-payload-content--full">
                    {payload.type === 'command' && <span className="hp-prompt">$ </span>}
                    {payload.type === 'http' && (
                      <span className="hp-http-method">{event.http_method || 'GET'} </span>
                    )}
                    {payload.type === 'http' ? event.http_path : payload.content}
                  </div>

                  {/* HTTP Body if present */}
                  {payload.type === 'http' && event.http_body && (
                    <div className="hp-http-body">
                      <div className="hp-overline">Request Body</div>
                      <pre className="hp-payload-content hp-payload-content--full">
                        {event.http_body}
                      </pre>
                    </div>
                  )}

                  {/* HTTP Headers if present */}
                  {event.http_headers && Object.keys(event.http_headers).length > 0 && (
                    <div className="hp-http-headers">
                      <div className="hp-overline">HTTP Headers</div>
                      <div className="hp-headers-list">
                        {Object.entries(event.http_headers).map(([key, value]) => (
                          <div key={key} className="hp-header-item">
                            <span className="hp-header-key">{key}:</span>
                            <span className="hp-header-value">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Raw Data Section (if different from main payload) */}
                {event.raw_data && payload.type !== 'raw' && (
                  <div className="hp-raw-data-section">
                    <div className="hp-payload-header">
                      <span className="hp-overline">Raw Data</span>
                      <CopyButton text={event.raw_data} label="Copy raw data" />
                    </div>
                    <pre className="hp-payload-content hp-payload-content--full hp-payload-content--raw">
                      {event.raw_data}
                    </pre>
                  </div>
                )}
              </ExpandableSection>
            </div>

            {/* Right Column: Metadata */}
            <div className="hp-column-right">
              <ExpandableSection title="Event Metadata" icon={<Activity size={16} />}>
                <div className="hp-meta-list">
                  <div className="hp-meta-item">
                    <Clock size={16} />
                    <div className="hp-meta-content">
                      <label>Timestamp</label>
                      <span>{new Date(event.timestamp).toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="hp-meta-item">
                    <Hash size={16} />
                    <div className="hp-meta-content">
                      <label>Event ID</label>
                      <span className="hp-meta-value--mono">
                        {event.event_id}
                        <CopyButton text={event.event_id} />
                      </span>
                    </div>
                  </div>

                  <div className="hp-meta-item">
                    <FileText size={16} />
                    <div className="hp-meta-content">
                      <label>Session ID</label>
                      <span className="hp-meta-value--mono">
                        {event.session_id.substring(0, 20)}...
                        <CopyButton text={event.session_id} />
                      </span>
                    </div>
                  </div>

                  <div className="hp-meta-item">
                    <Server size={16} />
                    <div className="hp-meta-content">
                      <label>ATLAS</label>
                      <span>{event.honeypot_id}</span>
                    </div>
                  </div>

                  <div className="hp-meta-item">
                    <Terminal size={16} />
                    <div className="hp-meta-content">
                      <label>Protocol</label>
                      <span>{event.protocol.toUpperCase()}</span>
                    </div>
                  </div>

                  <div className="hp-meta-item">
                    <Network size={16} />
                    <div className="hp-meta-content">
                      <label>Source Port</label>
                      <span>{event.source_port}</span>
                    </div>
                  </div>

                  {event.matched_cwes && event.matched_cwes.length > 0 && (
                    <div className="hp-meta-item hp-meta-item--full">
                      <AlertTriangle size={16} />
                      <div className="hp-meta-content">
                        <label>Correlated Vulnerabilities</label>
                        <div className="hp-tag-list">
                          {event.matched_cwes.map((cwe) => (
                            <span key={cwe} className="hp-tag cve">
                              {cwe}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {event.matched_cves && event.matched_cves.length > 0 && (
                    <div className="hp-meta-item hp-meta-item--full">
                      <Shield size={16} />
                      <div className="hp-meta-content">
                        <label>Matched CVEs</label>
                        <div className="hp-tag-list">
                          {event.matched_cves.map((cve) => (
                            <div key={cve} className="hp-tag-group">
                              <span
                                className={`hp-tag cve ${loadingCVE === cve ? 'loading' : ''}`}
                                onClick={() => handleCVEClick(cve)}
                                title="View details"
                                style={{ cursor: 'pointer' }}
                              >
                                {loadingCVE === cve ? '...' : cve}
                              </span>
                              <a
                                href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hp-icon-link"
                                title="View on NVD"
                              >
                                <ExternalLink size={12} />
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {event.detected_patterns && event.detected_patterns.length > 0 && (
                    <div className="hp-meta-item hp-meta-item--full">
                      <Shield size={16} />
                      <div className="hp-meta-content">
                        <label>Attack Patterns</label>
                        <div className="hp-tag-list">
                          {event.detected_patterns.map((p, i) => (
                            <span key={i} className="hp-tag pattern" title={p}>
                              {p
                                .split(/[-_]/)
                                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                                .join(' ')}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </ExpandableSection>
            </div>
          </div>

          {/* AI Analysis (Full Width Bottom) */}
          <div className="hp-ai-section">
            <div className="hp-ai-header">
              <div className="hp-ai-label">
                <Brain size={16} /> AI Threat Analysis
              </div>
              {/* Re-run Analysis Button - Always visible if analysis exists or explicitly wanted */}
              {(aiContent || localAnalysis) && (
                <button
                  className="hp-analyze-btn-small"
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  title="Re-run Analysis"
                >
                  {isAnalyzing ? <Sparkles className="spinning" size={12} /> : <Play size={12} />}
                  <span style={{ marginLeft: '4px' }}>Re-analyze</span>
                </button>
              )}
            </div>

            <div className={`hp-ai-card ${localAnalysis ? 'analyzed' : ''}`}>
              {aiContent ? (
                <div className="hp-ai-content">
                  <div className="hp-ai-result">
                    <Sparkles className="hp-ai-sparkle" size={16} />
                    <div className="hp-ai-markdown">
                      <ReactMarkdown>{aiContent}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="hp-ai-empty-state">
                  <div className="hp-ai-icon-large">
                    <Brain size={48} />
                  </div>
                  {analysisError ? (
                    <>
                      <p className="hp-ai-error-text">
                        <AlertTriangle
                          size={16}
                          style={{ marginRight: '6px', color: 'var(--cyber-high)' }}
                        />
                        {analysisError}
                      </p>
                      <button
                        className="hp-analyze-btn-large"
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                      >
                        {isAnalyzing ? (
                          <>
                            <Sparkles className="spinning" size={16} /> Retrying...
                          </>
                        ) : (
                          <>
                            <Play size={16} /> Retry Analysis
                          </>
                        )}
                      </button>
                    </>
                  ) : (
                    <>
                      <p>No analysis generated for this threat yet.</p>
                      <button
                        className="hp-analyze-btn-large"
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                      >
                        {isAnalyzing ? (
                          <>
                            <Sparkles className="spinning" size={16} /> Analyzing Threat...
                          </>
                        ) : (
                          <>
                            <Play size={16} /> Run AI Analysis
                          </>
                        )}
                      </button>
                      {isAnalyzing && (
                        <span className="hp-ai-status-text">Connecting to Neural Engine...</span>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Nested CVE Detail Modal */}
      {selectedCVE && (
        <div style={{ position: 'fixed', zIndex: 1060 }}>
          <CVEDetailModal cve={selectedCVE} onClose={() => setSelectedCVE(null)} />
        </div>
      )}
    </div>
  );
};

export default AttackDetailModal;
