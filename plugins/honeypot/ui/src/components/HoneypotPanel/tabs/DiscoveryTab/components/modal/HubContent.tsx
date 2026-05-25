import { MapPin, Activity, Target, Network, Clock } from 'lucide-react';
import type { HubNode } from '../../../../../types';
import { formatDate, getFlagEmoji } from '../../utils';
import { getThreatLevel, formatCentralityScore } from '../../utils/modalFormatters';
import type { ModalTab } from '../../discoveryTypes';
import { CopyButton } from './CopyButton';

interface HubContentProps {
  hub: HubNode;
  activeTab: ModalTab;
}

export function HubContent({ hub, activeTab }: HubContentProps) {
  return (
    <>
      {activeTab === 'overview' && (
        <div className="tab-content">
          <div className="stats-grid">
            <div className="stat-card full-width">
              <span className="stat-card-label">IP Address</span>
              <div className="stat-card-ip">
                <code className="ip-large">{hub.ip}</code>
                <CopyButton text={hub.ip} />
              </div>
            </div>
            {hub.country && (
              <div className="stat-card">
                <span className="stat-card-label">Location</span>
                <span className="stat-card-value location">
                  <MapPin size={14} />
                  {getFlagEmoji(hub.country_code || '')} {hub.country}
                  {hub.country_code && ` (${hub.country_code})`}
                </span>
              </div>
            )}
            <div className="stat-card highlight">
              <span className="stat-card-label">Connected Bots</span>
              <span className="stat-card-value number large">{hub.connected_bots}</span>
            </div>
          </div>

          {/* Protocols */}
          <section className="content-section">
            <h4 className="section-title">
              <Activity size={14} />
              Protocols Observed
            </h4>
            <div className="tags-list">
              {hub.protocols.map((proto) => (
                <span key={proto} className="tag protocol">
                  {proto.toUpperCase()}
                </span>
              ))}
            </div>
          </section>
        </div>
      )}

      {activeTab === 'technical' && (
        <div className="tab-content">
          <section className="content-section">
            <h4 className="section-title">
              <Target size={14} />
              Threat Assessment
            </h4>
            <div className="threat-display">
              <div className="threat-score-main">
                <div className="threat-bar">
                  <div
                    className={`threat-bar-fill ${getThreatLevel(hub.threat_score).class}`}
                    style={{ width: `${hub.threat_score}%` }}
                  />
                </div>
                <div className="threat-info">
                  <span className="threat-value">{hub.threat_score.toFixed(0)}/100</span>
                  <span className={`threat-label ${getThreatLevel(hub.threat_score).class}`}>
                    {getThreatLevel(hub.threat_score).label}
                  </span>
                </div>
              </div>
            </div>
          </section>

          <section className="content-section">
            <h4 className="section-title">
              <Network size={14} />
              Network Centrality
            </h4>
            <div className="centrality-grid">
              <div className="centrality-item">
                <span className="centrality-label">Degree Centrality</span>
                <div className="centrality-value-group">
                  <span
                    className={`centrality-badge ${formatCentralityScore(hub.degree_centrality, 'degree').level}`}
                  >
                    {formatCentralityScore(hub.degree_centrality, 'degree').value}
                  </span>
                  <span className="centrality-desc">
                    {formatCentralityScore(hub.degree_centrality, 'degree').label}
                  </span>
                </div>
              </div>
              <div className="centrality-item">
                <span className="centrality-label">Betweenness Centrality</span>
                <div className="centrality-value-group">
                  <span
                    className={`centrality-badge ${formatCentralityScore(hub.betweenness_centrality, 'betweenness').level}`}
                  >
                    {formatCentralityScore(hub.betweenness_centrality, 'betweenness').value}
                  </span>
                  <span className="centrality-desc">
                    {formatCentralityScore(hub.betweenness_centrality, 'betweenness').label}
                  </span>
                </div>
              </div>
            </div>
          </section>
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="tab-content">
          <section className="content-section">
            <h4 className="section-title">
              <Clock size={14} />
              Activity Timeline
            </h4>
            <div className="timeline-display">
              <div className="timeline-item">
                <span className="timeline-label">First Seen</span>
                <span className="timeline-value">{formatDate(hub.first_seen)}</span>
              </div>
              <div className="timeline-item">
                <span className="timeline-label">Last Seen</span>
                <span className="timeline-value">{formatDate(hub.last_seen)}</span>
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
