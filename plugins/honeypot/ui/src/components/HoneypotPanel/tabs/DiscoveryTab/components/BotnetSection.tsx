import { useState } from 'react';
import {
  Users,
  Server,
  Shield,
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
import type {
  DiscoveryResult,
  BotnetCluster,
  HubNode,
  DiscoveryGraphNode,
} from '../../../../types';
import { getSeverityClass, formatDate, getFlagEmoji } from '../utils';

import { DiscoveryDetailModal } from './DiscoveryDetailModal';

import './BotnetSection.css';

interface BotnetSectionProps {
  result: DiscoveryResult;
}

type DetailCategory = 'botnet' | 'hub' | null;
type DetailItem = BotnetCluster | HubNode | null;

export function BotnetSection({ result }: BotnetSectionProps) {
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<DetailItem>(null);
  const [selectedCategory, setSelectedCategory] = useState<DetailCategory>(null);

  // Build IP to node map for geo lookup
  const ipToNodeMap: Record<string, DiscoveryGraphNode> = {};
  if (result.graph_data?.nodes) {
    result.graph_data.nodes.forEach((node) => {
      if (node.type === 'attacker') {
        ipToNodeMap[node.id] = node;
      }
    });
  }

  const getNodeInfo = (ip: string): DiscoveryGraphNode | null => {
    return ipToNodeMap[ip] || null;
  };

  const handleBotnetClick = (cluster: BotnetCluster, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedItem(cluster);
    setSelectedCategory('botnet');
  };

  const handleHubClick = (hub: HubNode) => {
    setSelectedItem(hub);
    setSelectedCategory('hub');
  };

  const handleCloseModal = () => {
    setSelectedItem(null);
    setSelectedCategory(null);
  };

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

  return (
    <>
      {/* Botnet Clusters Panel */}
      <div className="discovery-panel discovery-clusters">
        <div className="discovery-panel-header">
          <Users size={16} />
          <h3>Botnet Clusters</h3>
          <span className="discovery-panel-count">{result.botnets.length}</span>
        </div>
        <div className="discovery-panel-content">
          {result.botnets.length === 0 ? (
            <div className="discovery-empty">
              <Shield size={24} />
              <span>No botnet clusters detected</span>
            </div>
          ) : (
            result.botnets.map((cluster) => {
              const countryBreakdown = getCountryBreakdown(cluster.member_ips);
              const topCountries = Object.entries(countryBreakdown)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);

              return (
                <div
                  key={cluster.cluster_id}
                  className={`discovery-cluster-card ${getSeverityClass(cluster.severity)}`}
                >
                  <div
                    className="discovery-cluster-header"
                    onClick={() =>
                      setExpandedCluster(
                        expandedCluster === cluster.cluster_id ? null : cluster.cluster_id
                      )
                    }
                  >
                    <div className="discovery-cluster-title">
                      <span
                        className={`discovery-severity-badge ${getSeverityClass(cluster.severity)}`}
                      >
                        {cluster.severity.toUpperCase()}
                      </span>
                      <span className="discovery-cluster-name">Cluster {cluster.cluster_id}</span>
                    </div>
                    <div className="discovery-cluster-stats">
                      <span className="discovery-cluster-size">{cluster.size} IPs</span>
                      {expandedCluster === cluster.cluster_id ? (
                        <ChevronUp size={14} />
                      ) : (
                        <ChevronDown size={14} />
                      )}
                    </div>
                  </div>

                  {expandedCluster === cluster.cluster_id && (
                    <div className="discovery-cluster-details">
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
                            <span className="metric-value">
                              {cluster.common_protocols.join(', ') || 'N/A'}
                            </span>
                            <span className="metric-label">Protocols</span>
                          </div>
                        </div>
                        <div className="cluster-metric">
                          <Target size={14} />
                          <div className="metric-content">
                            <span className="metric-value">
                              {cluster.common_targets?.length || 0}
                            </span>
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
                        <div className="discovery-ip-list enhanced">
                          {cluster.member_ips.slice(0, 12).map((ip) => {
                            const node = getNodeInfo(ip);
                            return (
                              <div
                                key={ip}
                                className={`discovery-ip-item ${node?.is_hub ? 'is-hub' : ''}`}
                                title={
                                  node
                                    ? `${node.country || 'Unknown'} - ${node.attack_count} attacks`
                                    : ip
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
                            <span className="discovery-more-ips">
                              +{cluster.member_ips.length - 12} more
                            </span>
                          )}
                        </div>
                      </div>

                      {/* View Full Details Button */}
                      <button
                        className="discovery-view-details-btn"
                        onClick={(e) => handleBotnetClick(cluster, e)}
                      >
                        <ExternalLink size={14} />
                        View Full Details
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Hub Nodes (C&C Servers) Panel */}
      <div className="discovery-panel discovery-hubs">
        <div className="discovery-panel-header">
          <Server size={16} />
          <h3>Potential C&C Servers</h3>
          <span className="discovery-panel-count">{result.hub_nodes.length}</span>
        </div>
        <div className="discovery-panel-content">
          {result.hub_nodes.length === 0 ? (
            <div className="discovery-empty">
              <Shield size={24} />
              <span>No hub nodes detected</span>
            </div>
          ) : (
            <table className="discovery-hub-table">
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th>Threat Score</th>
                  <th>Connected</th>
                  <th>Centrality</th>
                </tr>
              </thead>
              <tbody>
                {result.hub_nodes.slice(0, 15).map((hub) => (
                  <tr
                    key={hub.ip}
                    className={hub.is_confirmed_cc ? 'hub-confirmed' : ''}
                    onClick={() => handleHubClick(hub)}
                  >
                    <td>
                      <div className="hub-ip-cell">
                        {hub.is_confirmed_cc && <Target size={12} className="hub-cc-icon" />}
                        <code>{hub.ip}</code>
                        {hub.country_code && (
                          <span className="hub-country">
                            {getFlagEmoji(hub.country_code)} {hub.country_code}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="hub-threat-score">
                        <div className="hub-threat-bar-container">
                          <div
                            className={`hub-threat-bar ${
                              hub.threat_score > 70
                                ? 'high'
                                : hub.threat_score > 30
                                  ? 'medium'
                                  : 'low'
                            }`}
                            style={{ width: `${Math.min(hub.threat_score, 100)}%` }}
                          />
                        </div>
                        <span className="hub-threat-value">{hub.threat_score.toFixed(0)}</span>
                      </div>
                    </td>
                    <td>{hub.connected_bots}</td>
                    <td>{hub.degree_centrality.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {selectedItem && selectedCategory && (
        <DiscoveryDetailModal
          item={selectedItem}
          category={selectedCategory}
          onClose={handleCloseModal}
        />
      )}
    </>
  );
}
