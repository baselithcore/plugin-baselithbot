import { MapPin, Activity, Network } from 'lucide-react';
import type { DiscoveryGraphNode } from '../../../../../types';
import { getFlagEmoji } from '../../utils';
import { formatCentralityScore } from '../../utils/modalFormatters';
import type { ModalTab } from '../../discoveryTypes';
import { CopyButton } from './CopyButton';

interface AttackerContentProps {
  attacker: DiscoveryGraphNode;
  activeTab: ModalTab;
}

export function AttackerContent({ attacker, activeTab }: AttackerContentProps) {
  return (
    <>
      {activeTab === 'overview' && (
        <div className="tab-content">
          <div className="stats-grid">
            <div className="stat-card full-width">
              <span className="stat-card-label">IP Address</span>
              <div className="stat-card-ip">
                <code className="ip-large">{attacker.id}</code>
                <CopyButton text={attacker.id} />
              </div>
            </div>

            {attacker.threat_score !== undefined && (
              <div className="stat-card">
                <span className="stat-card-label">Threat Score</span>
                <span
                  className={`stat-card-value number ${attacker.threat_score > 0.7 ? 'critical' : 'medium'}`}
                >
                  {Math.round(attacker.threat_score * 100)}/100
                </span>
              </div>
            )}

            {attacker.ja4_fingerprint && (
              <div className="stat-card full-width">
                <span className="stat-card-label">JA4 Fingerprint</span>
                <div className="stat-card-ip">
                  <code className="ip-small">{attacker.ja4_fingerprint}</code>
                  <CopyButton text={attacker.ja4_fingerprint} />
                </div>
              </div>
            )}

            {attacker.country && (
              <div className="stat-card">
                <span className="stat-card-label">Location</span>
                <span className="stat-card-value location">
                  <MapPin size={14} />
                  {getFlagEmoji(attacker.country_code || '')} {attacker.country}
                  {attacker.country_code && ` (${attacker.country_code})`}
                </span>
              </div>
            )}
            <div className="stat-card highlight">
              <span className="stat-card-label">Attack Events</span>
              <span className="stat-card-value number large">
                {attacker.attack_count?.toLocaleString() || 0}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-card-label">Connectivity</span>
              <span className="stat-card-value number">{attacker.degree} Peers</span>
            </div>
          </div>

          {/* Protocols */}
          {attacker.protocols && attacker.protocols.length > 0 && (
            <section className="content-section">
              <h4 className="section-title">
                <Activity size={14} />
                Observed Protocols
              </h4>
              <div className="tags-list">
                {attacker.protocols.map((proto) => (
                  <span key={proto} className="tag protocol">
                    {proto.toUpperCase()}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Centrality Stats */}
          <section className="content-section">
            <h4 className="section-title">
              <Network size={14} />
              Network Position
            </h4>
            <div className="centrality-grid">
              <div className="centrality-item">
                <span className="centrality-label">Degree Centrality</span>
                <div className="centrality-value-group">
                  <span
                    className={`centrality-badge ${formatCentralityScore(attacker.centrality, 'degree').level}`}
                  >
                    {formatCentralityScore(attacker.centrality, 'degree').value}
                  </span>
                  <span className="centrality-desc">
                    {formatCentralityScore(attacker.centrality, 'degree').label}
                  </span>
                </div>
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
