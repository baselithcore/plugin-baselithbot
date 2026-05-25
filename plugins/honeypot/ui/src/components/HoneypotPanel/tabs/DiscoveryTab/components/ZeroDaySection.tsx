import { useState, useMemo } from 'react';
import {
  Bug,
  Shield,
  Skull,
  Zap,
  AlertTriangle,
  Target,
  Clock,
  TrendingUp,
  Eye,
  ChevronRight,
  Filter,
  Search,
} from 'lucide-react';
import type { NetworkAnomaly } from '../../../../types';
import { getSeverityClass, formatDate } from '../utils';
import { DiscoveryDetailModal } from './DiscoveryDetailModal';

import './ZeroDaySection.css';

interface ZeroDaySectionProps {
  zerodayAnomalies: NetworkAnomaly[];
  exploitAnomalies: NetworkAnomaly[];
  networkAnomalies: NetworkAnomaly[];
  zerodayCount: number;
  exploitCount: number;
}

type DetailCategory = 'zeroday' | 'exploit' | 'anomaly' | null;
type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low';

/** Risk score calculation based on multiple factors */
function calculateRiskScore(anomaly: NetworkAnomaly): number {
  let score = 0;
  const severityScores: Record<string, number> = {
    critical: 40,
    high: 30,
    medium: 20,
    low: 10,
  };
  score += severityScores[anomaly.severity] || 10;
  score += Math.min(anomaly.confidence * 30, 30);
  if (anomaly.metadata?.novelty_score) {
    score += anomaly.metadata.novelty_score * 20;
  }
  if (anomaly.metadata?.occurrence_count && anomaly.metadata.occurrence_count > 5) {
    score += 10;
  }
  return Math.min(Math.round(score), 100);
}

/** Get risk level label from score */
function getRiskLevel(score: number): { label: string; class: string } {
  if (score >= 80) return { label: 'Critical', class: 'risk-critical' };
  if (score >= 60) return { label: 'High', class: 'risk-high' };
  if (score >= 40) return { label: 'Medium', class: 'risk-medium' };
  return { label: 'Low', class: 'risk-low' };
}

/** Format attack vector for display */
function formatAttackVector(vector: string): string {
  const vectorMap: Record<string, string> = {
    command_injection: 'Command Injection',
    sql_injection: 'SQL Injection',
    path_traversal: 'Path Traversal',
    xss: 'Cross-Site Scripting',
    rce: 'Remote Code Execution',
    lfi: 'Local File Inclusion',
    rfi: 'Remote File Inclusion',
    ssrf: 'Server-Side Request Forgery',
    xxe: 'XML External Entity',
    deserialization: 'Insecure Deserialization',
  };
  return vectorMap[vector?.toLowerCase()] || vector?.replace(/_/g, ' ') || 'Unknown';
}

export function ZeroDaySection({
  zerodayAnomalies,
  exploitAnomalies,
  networkAnomalies,
  zerodayCount,
  exploitCount,
}: ZeroDaySectionProps) {
  const [selectedAnomaly, setSelectedAnomaly] = useState<NetworkAnomaly | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<DetailCategory>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const handleCardClick = (anomaly: NetworkAnomaly, category: DetailCategory) => {
    setSelectedAnomaly(anomaly);
    setSelectedCategory(category);
  };

  const handleCloseModal = () => {
    setSelectedAnomaly(null);
    setSelectedCategory(null);
  };

  // Filter and sort anomalies
  const filteredZerodays = useMemo(() => {
    let filtered = zerodayAnomalies;
    if (severityFilter !== 'all') {
      filtered = filtered.filter((a) => a.severity === severityFilter);
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (a) =>
          a.description.toLowerCase().includes(query) ||
          a.metadata?.attack_vector?.toLowerCase().includes(query) ||
          a.involved_ips.some((ip) => ip.includes(query))
      );
    }
    // Sort by risk score
    return filtered.sort((a, b) => calculateRiskScore(b) - calculateRiskScore(a));
  }, [zerodayAnomalies, severityFilter, searchQuery]);

  const filteredExploits = useMemo(() => {
    let filtered = exploitAnomalies;
    if (severityFilter !== 'all') {
      filtered = filtered.filter((a) => a.severity === severityFilter);
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (a) =>
          a.description.toLowerCase().includes(query) ||
          a.metadata?.pattern_type?.toLowerCase().includes(query)
      );
    }
    return filtered.sort((a, b) => calculateRiskScore(b) - calculateRiskScore(a));
  }, [exploitAnomalies, severityFilter, searchQuery]);

  // Statistics for header
  const criticalCount = zerodayAnomalies.filter((a) => a.severity === 'critical').length;
  const highCount = zerodayAnomalies.filter((a) => a.severity === 'high').length;

  return (
    <div className="zeroday-section">
      {/* Section Header with Stats */}
      <div className="zeroday-section-header">
        <div className="zeroday-section-title">
          <Bug className="section-icon" size={20} />
          <h3>Zero-Day & Exploit Analysis</h3>
        </div>
        <div className="zeroday-quick-stats">
          <div className="quick-stat critical">
            <span className="stat-number">{criticalCount}</span>
            <span className="stat-label">Critical</span>
          </div>
          <div className="quick-stat high">
            <span className="stat-number">{highCount}</span>
            <span className="stat-label">High</span>
          </div>
          <div className="quick-stat total">
            <span className="stat-number">{zerodayCount + exploitCount}</span>
            <span className="stat-label">Total</span>
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="zeroday-filters">
        <div className="filter-search">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search by description, vector, or IP..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="filter-severity">
          <Filter size={14} />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Zero-Day Candidates Panel */}
      <div className="discovery-panel discovery-zeroday">
        <div className="discovery-panel-header">
          <div className="panel-header-left">
            <Skull size={18} className="panel-icon zeroday" />
            <h4>Zero-Day Candidates</h4>
          </div>
          <div className="panel-header-right">
            <span className="discovery-panel-count zeroday">{filteredZerodays.length}</span>
          </div>
        </div>

        <div className="discovery-panel-content">
          {filteredZerodays.length === 0 ? (
            <div className="discovery-empty">
              <Shield size={32} className="empty-icon" />
              <span className="empty-title">No zero-day candidates detected</span>
              <p className="empty-description">
                Zero-days are identified when attack payloads don't match known CVE patterns.
                Continue monitoring for novel attack vectors.
              </p>
            </div>
          ) : (
            <div className="zeroday-cards-grid">
              {filteredZerodays.map((anomaly) => {
                const riskScore = calculateRiskScore(anomaly);
                const risk = getRiskLevel(riskScore);
                return (
                  <article
                    key={anomaly.anomaly_id}
                    className={`zeroday-card ${getSeverityClass(anomaly.severity)}`}
                    onClick={() => handleCardClick(anomaly, 'zeroday')}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && handleCardClick(anomaly, 'zeroday')}
                  >
                    {/* Card Header */}
                    <header className="zeroday-card-header">
                      <div className="card-vector">
                        <Target size={14} />
                        <span>{formatAttackVector(anomaly.metadata?.attack_vector)}</span>
                      </div>
                      <div className="card-badges">
                        <span className={`severity-pill ${getSeverityClass(anomaly.severity)}`}>
                          {anomaly.severity}
                        </span>
                        <span className={`risk-pill ${risk.class}`}>{risk.label}</span>
                      </div>
                    </header>

                    {/* Card Body */}
                    <div className="zeroday-card-body">
                      <p className="card-description">{anomaly.description}</p>

                      {/* Key Metrics Row */}
                      <div className="card-metrics">
                        {anomaly.metadata?.novelty_score !== undefined && (
                          <div className="metric">
                            <div className="metric-header">
                              <TrendingUp size={12} />
                              <span>Novelty</span>
                            </div>
                            <div className="metric-bar">
                              <div
                                className="metric-fill novelty"
                                style={{ width: `${anomaly.metadata.novelty_score * 100}%` }}
                              />
                            </div>
                            <span className="metric-value">
                              {(anomaly.metadata.novelty_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}

                        {anomaly.metadata?.occurrence_count !== undefined && (
                          <div className="metric text-only">
                            <div className="metric-header">
                              <Eye size={12} />
                              <span>Observed</span>
                            </div>
                            <span className="metric-value large">
                              {anomaly.metadata.occurrence_count}x
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Targets */}
                      {anomaly.metadata?.target_services &&
                        anomaly.metadata.target_services.length > 0 && (
                          <div className="card-targets">
                            <span className="targets-label">Targets:</span>
                            <div className="targets-list">
                              {anomaly.metadata.target_services
                                .slice(0, 3)
                                .map((svc: string, i: number) => (
                                  <span key={i} className="target-tag">
                                    {svc}
                                  </span>
                                ))}
                              {anomaly.metadata.target_services.length > 3 && (
                                <span className="target-more">
                                  +{anomaly.metadata.target_services.length - 3}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                    </div>

                    {/* Card Footer */}
                    <footer className="zeroday-card-footer">
                      <div className="footer-ips">
                        <span className="ip-label">Sources:</span>
                        <div className="ip-list">
                          {anomaly.involved_ips.slice(0, 3).map((ip) => (
                            <code key={ip} className="ip-tag">
                              {ip}
                            </code>
                          ))}
                          {anomaly.involved_ips.length > 3 && (
                            <span className="ip-more">+{anomaly.involved_ips.length - 3}</span>
                          )}
                        </div>
                      </div>
                      <div className="footer-action">
                        <span>View Details</span>
                        <ChevronRight size={14} />
                      </div>
                    </footer>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Exploit Patterns Panel */}
      <div className="discovery-panel discovery-exploits">
        <div className="discovery-panel-header">
          <div className="panel-header-left">
            <Zap size={18} className="panel-icon exploit" />
            <h4>Exploit Patterns</h4>
          </div>
          <div className="panel-header-right">
            <span className="discovery-panel-count exploit">{filteredExploits.length}</span>
          </div>
        </div>

        <div className="discovery-panel-content">
          {filteredExploits.length === 0 ? (
            <div className="discovery-empty">
              <Shield size={32} className="empty-icon" />
              <span className="empty-title">No exploit patterns detected</span>
              <p className="empty-description">
                Exploit patterns match known attack techniques and MITRE ATT&CK tactics.
              </p>
            </div>
          ) : (
            <div className="exploit-cards-grid">
              {filteredExploits.map((anomaly) => {
                return (
                  <article
                    key={anomaly.anomaly_id}
                    className={`exploit-card ${getSeverityClass(anomaly.severity)}`}
                    onClick={() => handleCardClick(anomaly, 'exploit')}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && handleCardClick(anomaly, 'exploit')}
                  >
                    <header className="exploit-card-header">
                      <div className="exploit-type">
                        <span className="type-name">
                          {anomaly.metadata?.pattern_type || anomaly.anomaly_type}
                        </span>
                        {anomaly.metadata?.mitre_id && (
                          <span className="mitre-badge">{anomaly.metadata.mitre_id}</span>
                        )}
                      </div>
                      <span className={`severity-pill ${getSeverityClass(anomaly.severity)}`}>
                        {anomaly.severity}
                      </span>
                    </header>

                    <div className="exploit-card-body">
                      <p className="exploit-description">{anomaly.description}</p>

                      {anomaly.metadata?.sophistication_score !== undefined && (
                        <div className="sophistication-meter">
                          <div className="meter-header">
                            <span>Sophistication Level</span>
                            <span className="meter-value">
                              {anomaly.metadata.sophistication_score >= 0.7
                                ? 'Advanced'
                                : anomaly.metadata.sophistication_score >= 0.4
                                  ? 'Intermediate'
                                  : 'Basic'}
                            </span>
                          </div>
                          <div className="meter-bar">
                            <div
                              className="meter-fill"
                              style={{ width: `${anomaly.metadata.sophistication_score * 100}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {anomaly.metadata?.stages && anomaly.metadata.stages.length > 0 && (
                        <div className="attack-stages">
                          <span className="stages-label">Attack Chain:</span>
                          <div className="stages-list">
                            {anomaly.metadata.stages.slice(0, 4).map((stage: string, i: number) => (
                              <span key={i} className="stage-tag">
                                {i + 1}. {stage.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <footer className="exploit-card-footer">
                      {anomaly.metadata?.first_seen && (
                        <div className="footer-time">
                          <Clock size={12} />
                          <span>{formatDate(anomaly.metadata.first_seen)}</span>
                        </div>
                      )}
                      <div className="footer-action">
                        <span>Analyze</span>
                        <ChevronRight size={14} />
                      </div>
                    </footer>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Network Anomalies Panel (collapsed by default if many) */}
      {networkAnomalies.length > 0 && (
        <div className="discovery-panel discovery-anomalies">
          <div className="discovery-panel-header">
            <div className="panel-header-left">
              <AlertTriangle size={18} className="panel-icon anomaly" />
              <h4>Network Anomalies</h4>
            </div>
            <div className="panel-header-right">
              <span className="discovery-panel-count">{networkAnomalies.length}</span>
            </div>
          </div>

          <div className="discovery-panel-content">
            <div className="anomaly-list">
              {networkAnomalies.slice(0, 10).map((anomaly) => (
                <div
                  key={anomaly.anomaly_id}
                  className={`anomaly-item ${getSeverityClass(anomaly.severity)}`}
                  onClick={() => handleCardClick(anomaly, 'anomaly')}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && handleCardClick(anomaly, 'anomaly')}
                >
                  <div className="anomaly-item-main">
                    <span className="anomaly-type">{anomaly.anomaly_type.replace(/_/g, ' ')}</span>
                    <span className={`severity-dot ${getSeverityClass(anomaly.severity)}`} />
                  </div>
                  <p className="anomaly-desc">{anomaly.description}</p>
                  <div className="anomaly-meta">
                    <span className="confidence">
                      {(anomaly.confidence * 100).toFixed(0)}% confidence
                    </span>
                    <ChevronRight size={12} />
                  </div>
                </div>
              ))}
              {networkAnomalies.length > 10 && (
                <div className="anomaly-more">
                  Showing 10 of {networkAnomalies.length} anomalies
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedAnomaly && selectedCategory && (
        <DiscoveryDetailModal
          item={selectedAnomaly}
          category={selectedCategory}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}
