import { Activity, Server, BarChart3, Users, Clock } from 'lucide-react';
import type { BotnetCluster } from '../../../../../types';
import { formatDate } from '../../utils';
import type { ModalTab } from '../../discoveryTypes';
import { IPBadge } from './IPBadge';

interface BotnetContentProps {
  botnet: BotnetCluster;
  activeTab: ModalTab;
}

export function BotnetContent({ botnet, activeTab }: BotnetContentProps) {
  return (
    <>
      {activeTab === 'overview' && (
        <div className="tab-content">
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-card-label">Cluster ID</span>
              <span className="stat-card-value">#{botnet.cluster_id}</span>
            </div>
            <div className="stat-card highlight">
              <span className="stat-card-label">Network Size</span>
              <span className="stat-card-value number large">
                {botnet.size}
                <span className="stat-card-unit">hosts</span>
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-card-label">Detection Confidence</span>
              <div className="stat-card-bar">
                <div
                  className="stat-card-bar-fill confidence"
                  style={{ width: `${botnet.detection_confidence * 100}%` }}
                />
                <span className="stat-card-bar-value">
                  {(botnet.detection_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div className="stat-card">
              <span className="stat-card-label">Coordination Score</span>
              <div className="stat-card-bar">
                <div
                  className="stat-card-bar-fill coordination"
                  style={{ width: `${botnet.attack_coordination_score * 100}%` }}
                />
                <span className="stat-card-bar-value highlight">
                  {(botnet.attack_coordination_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {/* Protocols */}
          <section className="content-section">
            <h4 className="section-title">
              <Activity size={14} />
              Communication Protocols
            </h4>
            <div className="tags-list">
              {botnet.common_protocols.map((proto) => (
                <span key={proto} className="tag protocol">
                  {proto.toUpperCase()}
                </span>
              ))}
            </div>
          </section>

          {/* C&C Infrastructure */}
          {(botnet.suspected_cc_ip ||
            (botnet.associated_cc_ips && botnet.associated_cc_ips.length > 0)) && (
            <section className="content-section">
              <h4 className="section-title">
                <Server size={14} />
                Associated C&C Infrastructure
              </h4>
              <div className="cc-list">
                {(botnet.associated_cc_ips && botnet.associated_cc_ips.length > 0
                  ? botnet.associated_cc_ips
                  : [botnet.suspected_cc_ip!]
                ).map((ccIp) => {
                  const metadata = botnet.associated_cc_metadata?.[ccIp];
                  return (
                    <div key={ccIp} className="cc-item">
                      <IPBadge ip={ccIp} />
                      {metadata && (
                        <span className="cc-meta">{metadata.connection_count} connections</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </div>
      )}

      {activeTab === 'technical' && (
        <div className="tab-content">
          <section className="content-section">
            <h4 className="section-title">
              <BarChart3 size={14} />
              Cluster Analysis Metrics
            </h4>
            <div className="metrics-detail">
              <div className="metric-row">
                <span className="metric-label">Modularity Score</span>
                <span className="metric-value">{(botnet.modularity_score * 100).toFixed(1)}%</span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Attack Coordination</span>
                <span className="metric-value highlight">
                  {(botnet.attack_coordination_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </section>
        </div>
      )}

      {activeTab === 'network' && (
        <div className="tab-content">
          <section className="content-section">
            <h4 className="section-title">
              <Users size={14} />
              Cluster Members ({botnet.member_ips.length})
            </h4>
            <div className="ip-grid">
              {botnet.member_ips.map((ip) => (
                <IPBadge key={ip} ip={ip} />
              ))}
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
                <span className="timeline-label">First Detected</span>
                <span className="timeline-value">{formatDate(botnet.first_detected)}</span>
              </div>
              <div className="timeline-item">
                <span className="timeline-label">Last Activity</span>
                <span className="timeline-value">{formatDate(botnet.last_activity)}</span>
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
