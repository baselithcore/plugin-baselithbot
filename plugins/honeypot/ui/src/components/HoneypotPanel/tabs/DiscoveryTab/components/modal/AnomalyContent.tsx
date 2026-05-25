import {
  AlertTriangle,
  Target,
  Server,
  Link2,
  ExternalLink,
  BarChart3,
  Activity,
  Shield,
  FileText,
  Clock,
  Network,
} from 'lucide-react';
import type { NetworkAnomaly } from '../../../../../types';
import { formatDate } from '../../utils';
import { formatAnomalyType } from '../../utils/modalFormatters';
import type { ModalTab } from '../../discoveryTypes';
import { CopyButton } from './CopyButton';
import { IPBadge } from './IPBadge';

interface AnomalyContentProps {
  anomaly: NetworkAnomaly;
  category: 'zeroday' | 'exploit' | 'anomaly';
  activeTab: ModalTab;
}

export function AnomalyContent({ anomaly, category, activeTab }: AnomalyContentProps) {
  return (
    <>
      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="tab-content">
          {/* Quick Stats Grid */}
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-card-label">Type</span>
              <span className="stat-card-value type">
                {formatAnomalyType(anomaly.anomaly_type)}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-card-label">Confidence</span>
              <div className="stat-card-bar">
                <div
                  className="stat-card-bar-fill confidence"
                  style={{ width: `${anomaly.confidence * 100}%` }}
                />
                <span className="stat-card-bar-value">
                  {(anomaly.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            {category === 'zeroday' && anomaly.metadata?.novelty_score !== undefined && (
              <div className="stat-card">
                <span className="stat-card-label">Novelty Score</span>
                <div className="stat-card-bar">
                  <div
                    className="stat-card-bar-fill novelty"
                    style={{ width: `${anomaly.metadata.novelty_score * 100}%` }}
                  />
                  <span className="stat-card-bar-value highlight">
                    {(anomaly.metadata.novelty_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
            {anomaly.metadata?.occurrence_count && (
              <div className="stat-card">
                <span className="stat-card-label">Times Observed</span>
                <span className="stat-card-value number">{anomaly.metadata.occurrence_count}</span>
              </div>
            )}
          </div>

          {/* Description Section */}
          <section className="content-section">
            <h4 className="section-title">
              <AlertTriangle size={14} />
              Description
            </h4>
            <p className="description-text">{anomaly.description}</p>
          </section>

          {/* Attack Vector (for Zero-Day) */}
          {category === 'zeroday' && anomaly.metadata?.attack_vector && (
            <section className="content-section">
              <h4 className="section-title">
                <Target size={14} />
                Attack Vector
              </h4>
              <div className="attack-vector-display">
                <span className="vector-name">
                  {formatAnomalyType(anomaly.metadata.attack_vector)}
                </span>
              </div>
            </section>
          )}

          {/* Target Services */}
          {anomaly.metadata?.target_services && anomaly.metadata.target_services.length > 0 && (
            <section className="content-section">
              <h4 className="section-title">
                <Server size={14} />
                Target Services
              </h4>
              <div className="tags-list">
                {anomaly.metadata.target_services.map((svc: string, i: number) => (
                  <span key={i} className="tag service">
                    {svc}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Technical Tab */}
      {activeTab === 'technical' && anomaly.metadata && (
        <div className="tab-content">
          {/* MITRE ATT&CK */}
          {anomaly.metadata.mitre_id && (
            <section className="content-section">
              <h4 className="section-title">
                <Link2 size={14} />
                MITRE ATT&CK Reference
              </h4>
              <a
                href={`https://attack.mitre.org/techniques/${anomaly.metadata.mitre_id.replace('.', '/')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mitre-link"
              >
                <span>{anomaly.metadata.mitre_id}</span>
                <ExternalLink size={12} />
              </a>
            </section>
          )}

          {/* Sophistication Score (for Exploit) */}
          {category === 'exploit' && anomaly.metadata.sophistication_score !== undefined && (
            <section className="content-section">
              <h4 className="section-title">
                <BarChart3 size={14} />
                Sophistication Analysis
              </h4>
              <div className="sophistication-display">
                <div className="soph-bar">
                  <div
                    className="soph-bar-fill"
                    style={{ width: `${anomaly.metadata.sophistication_score * 100}%` }}
                  />
                </div>
                <div className="soph-labels">
                  <span className="soph-level">
                    {anomaly.metadata.sophistication_score >= 0.7
                      ? 'Advanced'
                      : anomaly.metadata.sophistication_score >= 0.4
                        ? 'Intermediate'
                        : 'Basic'}
                  </span>
                  <span className="soph-percent">
                    {(anomaly.metadata.sophistication_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </section>
          )}

          {/* Attack Stages */}
          {anomaly.metadata.stages && anomaly.metadata.stages.length > 0 && (
            <section className="content-section">
              <h4 className="section-title">
                <Activity size={14} />
                Attack Chain Stages
              </h4>
              <div className="stages-timeline">
                {anomaly.metadata.stages.map((stage: string, i: number) => (
                  <div key={i} className="stage-item">
                    <div className="stage-number">{i + 1}</div>
                    <div className="stage-name">{formatAnomalyType(stage)}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Related CVEs */}
          {anomaly.metadata.matched_cves && anomaly.metadata.matched_cves.length > 0 && (
            <section className="content-section">
              <h4 className="section-title">
                <Shield size={14} />
                Related CVEs
              </h4>
              <div className="cve-list">
                {anomaly.metadata.matched_cves.map((cve: string) => (
                  <a
                    key={cve}
                    href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="cve-badge"
                  >
                    {cve}
                    <ExternalLink size={10} />
                  </a>
                ))}
              </div>
            </section>
          )}

          {/* Payload Preview */}
          {anomaly.metadata.payload_preview && (
            <section className="content-section">
              <h4 className="section-title">
                <FileText size={14} />
                Captured Payload
              </h4>
              <div className="payload-container">
                <pre className="payload-code">
                  <span className="payload-prompt">$</span>
                  {anomaly.metadata.payload_preview.slice(0, 500)}
                  {anomaly.metadata.payload_preview.length > 500 && '...'}
                </pre>
                <CopyButton text={anomaly.metadata.payload_preview} label="Copy payload" />
              </div>
            </section>
          )}

          {/* Activity Window */}
          {(anomaly.metadata.first_seen || anomaly.metadata.last_seen) && (
            <section className="content-section">
              <h4 className="section-title">
                <Clock size={14} />
                Activity Window
              </h4>
              <div className="timeline-display">
                {anomaly.metadata.first_seen && (
                  <div className="timeline-item">
                    <span className="timeline-label">First Seen</span>
                    <span className="timeline-value">
                      {formatDate(anomaly.metadata.first_seen)}
                    </span>
                  </div>
                )}
                {anomaly.metadata.last_seen && (
                  <div className="timeline-item">
                    <span className="timeline-label">Last Seen</span>
                    <span className="timeline-value">{formatDate(anomaly.metadata.last_seen)}</span>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Network Tab */}
      {activeTab === 'network' && anomaly.involved_ips && (
        <div className="tab-content">
          <section className="content-section">
            <h4 className="section-title">
              <Network size={14} />
              Involved IP Addresses ({anomaly.involved_ips.length})
            </h4>
            <div className="ip-grid">
              {anomaly.involved_ips.map((ip) => (
                <IPBadge key={ip} ip={ip} />
              ))}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
