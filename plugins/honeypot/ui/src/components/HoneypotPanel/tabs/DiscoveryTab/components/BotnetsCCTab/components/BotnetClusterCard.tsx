import { useState } from 'react';
import {
  Users,
  ChevronUp,
  ChevronDown,
  Activity,
  Globe,
  Clock,
  Target,
  MapPin,
  ExternalLink,
  BarChart2,
  Crosshair,
} from 'lucide-react';
import type { BotnetCluster, DiscoveryGraphNode } from '../../../../../../types/discovery';
import { getSeverityClass, formatDate, getFlagEmoji } from '../../../utils';

interface BotnetClusterCardProps {
  cluster: BotnetCluster;
  getNodeInfo: (ip: string) => DiscoveryGraphNode | null;
  onViewDetails: (cluster: BotnetCluster, e: React.MouseEvent) => void;
}

export function BotnetClusterCard({ cluster, getNodeInfo, onViewDetails }: BotnetClusterCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Get country breakdown for cluster
  const getCountryBreakdown = (memberIps: string[]): Record<string, number> => {
    const countries: Record<string, number> = {};
    memberIps.forEach((ip) => {
      const node = getNodeInfo(ip);
      const country = node?.country_code || 'Unknown';
      countries[country] = (countries[country] || 0) + 1;
    });
    return countries;
  };

  const countryBreakdown = getCountryBreakdown(cluster.member_ips);
  const topCountries = Object.entries(countryBreakdown)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div
      key={cluster.cluster_id}
      className={`botnets-cluster-card ${getSeverityClass(cluster.severity)}`}
    >
      <div className="botnets-cluster-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="botnets-cluster-title">
          <span className={`botnets-severity-badge ${getSeverityClass(cluster.severity)}`}>
            {cluster.severity.toUpperCase()}
          </span>
          <span className="botnets-cluster-name">Cluster {cluster.cluster_id}</span>
        </div>
        <div className="botnets-cluster-stats">
          <span className="botnets-cluster-size">{cluster.size} IPs</span>
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {isExpanded && (
        <div className="botnets-cluster-details">
          {/* Key Metrics Grid */}
          <div className="cluster-metrics-grid">
            <div className="cluster-metric">
              <Activity size={14} />
              <div className="metric-content">
                <span className="metric-value">
                  {(cluster.attack_coordination_score * 100).toFixed(0)}%
                </span>
                <span className="metric-label">Coordination</span>
              </div>
            </div>
            <div className="cluster-metric">
              <BarChart2 size={14} />
              <div className="metric-content">
                <span className="metric-value">
                  {(cluster.detection_confidence * 100).toFixed(0)}%
                </span>
                <span className="metric-label">Confidence</span>
              </div>
            </div>
            <div className="cluster-metric">
              <Globe size={14} />
              <div className="metric-content">
                <span className="metric-value">{cluster.common_protocols.join(', ') || 'N/A'}</span>
                <span className="metric-label">Protocols</span>
              </div>
            </div>
            <div className="cluster-metric">
              <Target size={14} />
              <div className="metric-content">
                <span className="metric-value">{cluster.common_targets?.length || 0}</span>
                <span className="metric-label">Targets</span>
              </div>
            </div>
          </div>

          {/* Associated C&C Infrastructure */}
          {(cluster.suspected_cc_ip ||
            (cluster.associated_cc_ips && cluster.associated_cc_ips.length > 0)) && (
            <div className="cluster-cc-section">
              <div className="cc-header">
                <Crosshair size={14} />
                <span>Associated C&C Infrastructure</span>
              </div>
              <div className="cc-ip-list">
                {(cluster.associated_cc_ips && cluster.associated_cc_ips.length > 0
                  ? cluster.associated_cc_ips
                  : [cluster.suspected_cc_ip!]
                ).map((ccIp) => {
                  const ccNode = getNodeInfo(ccIp);
                  const metadata = cluster.associated_cc_metadata?.[ccIp];
                  return (
                    <div key={ccIp} className="cc-ip-container">
                      <div className="cc-ip-row">
                        <code className="cc-ip">{ccIp}</code>
                        {ccNode?.country_code && (
                          <span className="cc-country">
                            {getFlagEmoji(ccNode.country_code)} {ccNode.country_code}
                          </span>
                        )}
                        {ccNode?.is_hub && <span className="cc-hub-badge">HUB</span>}
                      </div>
                      {metadata && (
                        <div className="cc-ip-meta">
                          <span className="cc-connection-strength">
                            Linked to {metadata.connection_count}/{cluster.size} bots
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Geographic Distribution */}
          {topCountries.length > 0 && (
            <div className="cluster-geo-section">
              <div className="geo-header">
                <MapPin size={14} />
                <span>Geographic Distribution</span>
              </div>
              <div className="geo-breakdown">
                {topCountries.map(([country, count]) => (
                  <div key={country} className="geo-item">
                    <span className="geo-country">
                      {getFlagEmoji(country)} {country}
                    </span>
                    <span className="geo-count">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Time Range */}
          <div className="cluster-time-section">
            <div className="time-row">
              <Clock size={12} />
              <span className="time-label">First Detected:</span>
              <span className="time-value">{formatDate(cluster.first_detected)}</span>
            </div>
            <div className="time-row">
              <Clock size={12} />
              <span className="time-label">Last Activity:</span>
              <span className="time-value">{formatDate(cluster.last_activity)}</span>
            </div>
          </div>

          {/* Member IPs with Country Info */}
          <div className="cluster-ips-section">
            <div className="ips-header">
              <Users size={14} />
              <span>Member IPs ({cluster.member_ips.length})</span>
            </div>
            <div className="botnets-ip-list enhanced">
              {cluster.member_ips.slice(0, 12).map((ip) => {
                const node = getNodeInfo(ip);
                return (
                  <div
                    key={ip}
                    className={`botnets-ip-item ${node?.is_hub ? 'is-hub' : ''}`}
                    title={
                      node ? `${node.country || 'Unknown'} - ${node.attack_count} attacks` : ip
                    }
                  >
                    <code>{ip}</code>
                    {node?.country_code && (
                      <span className="ip-country">
                        {getFlagEmoji(node.country_code)} {node.country_code}
                      </span>
                    )}
                    {node?.is_hub && <span className="ip-hub-badge">HUB</span>}
                  </div>
                );
              })}
              {cluster.member_ips.length > 12 && (
                <span className="botnets-more-ips">+{cluster.member_ips.length - 12} more</span>
              )}
            </div>
          </div>

          {/* View Full Details Button */}
          <button className="botnets-view-details-btn" onClick={(e) => onViewDetails(cluster, e)}>
            <ExternalLink size={14} />
            View Full Details
          </button>
        </div>
      )}
    </div>
  );
}
