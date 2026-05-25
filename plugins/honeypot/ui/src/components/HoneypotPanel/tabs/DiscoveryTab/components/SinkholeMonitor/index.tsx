/**
 * SinkholeMonitor - Threat Intelligence & Sinkhole Analysis Module
 *
 * Professional UI/UX aligned with DiscoveryTab design system.
 * Displays JA4 fingerprints, DNS anomalies, botnet clusters, and IOC data.
 */

import { useState } from 'react';
import {
  Fingerprint,
  Globe,
  Users,
  Server,
  Activity,
  Shield,
  Target,
  ExternalLink,
  Download,
  Link,
  Hash,
  FileCode,
} from 'lucide-react';
import type {
  DiscoveryResult,
  NetworkAnomaly,
  BotnetCluster,
} from '../../../../../types/discovery';
import { IntelDetailModal } from '../IntelDetailModal';
import { useSinkholeData } from './hooks/useSinkholeData';
import { AnomalyDetailModal } from './modals/AnomalyDetailModal';
import { ClusterDetailModal } from './modals/ClusterDetailModal';
import { StatCard } from './cards/StatCard';
import { ClusterCard } from './cards/ClusterCard';
import { IOCCard } from './cards/IOCCard';
import { DNSTable } from './tables/DNSTable';
import { JA4Item } from './components/JA4Item';
import { ActivityItem } from './components/ActivityItem';
import { EmptyState } from './components/EmptyState';
import { SinkholeControl } from './components/SinkholeControl';
import { ClusterGraphV2 } from './components/ClusterGraphV2';
import './SinkholeMonitor.css';

type IOCCategory = 'ips' | 'domains' | 'hashes' | 'yara' | null;

interface SinkholeMonitorProps {
  result: DiscoveryResult;
}

// MITRE ATT&CK technique mappings
const MITRE_TECHNIQUES: Record<string, string> = {
  T1059: 'Command Interpreter',
  T1190: 'Exploit Public App',
  T1110: 'Brute Force',
  T1082: 'System Discovery',
  T1071: 'App Layer Protocol',
  T1021: 'Remote Services',
  T1078: 'Valid Accounts',
  T1105: 'Ingress Tool Transfer',
  T1018: 'Remote System Discovery',
  T1046: 'Network Service Discovery',
  T1595: 'Active Scanning',
  T1055: 'Process Injection',
};

export function SinkholeMonitor({ result }: SinkholeMonitorProps) {
  const [showModal, setShowModal] = useState(false);
  const [modalCategory, setModalCategory] = useState<IOCCategory>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<NetworkAnomaly | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<BotnetCluster | null>(null);

  const {
    ja4Fingerprints,
    dnsAnomalies,
    clusters,
    iocCount,
    yaraCount,
    confidence,
    severity,
    attackTypes,
    mitreTechniques,
    iocs,
    yaraRules,
    recentEvents,
    hasIntelData,
  } = useSinkholeData(result);

  const openModal = (category: IOCCategory) => {
    setModalCategory(category);
    setShowModal(true);
  };

  return (
    <div className="sinkhole-monitor">
      {/* Stats Overview */}
      <div className="sinkhole-grid sinkhole-grid-4">
        <StatCard
          icon={<Users />}
          value={result.botnets.length}
          label="Bot Clusters"
          variant="danger"
        />
        <StatCard
          icon={<Globe />}
          value={dnsAnomalies.length}
          label="DNS Anomalies"
          variant="purple"
        />
        <StatCard
          icon={<Fingerprint />}
          value={ja4Fingerprints.length}
          label="JA4 Fingerprints"
          variant="default"
        />
        <StatCard
          icon={<Server />}
          value={result.hub_nodes.length}
          label="C&C Servers"
          variant="warning"
        />
      </div>

      {/* Main Content Grid */}
      <div className="sinkhole-grid sinkhole-grid-2">
        {/* JA4 Fingerprints Panel */}
        <div className="sinkhole-panel">
          <div className="sinkhole-panel-header">
            <Fingerprint />
            <h3>JA4+ TLS Fingerprints</h3>
            {ja4Fingerprints.length > 0 && (
              <span className="sinkhole-panel-badge">{ja4Fingerprints.length}</span>
            )}
          </div>
          <div className="sinkhole-panel-content">
            {ja4Fingerprints.length > 0 ? (
              <div className="ja4-list">
                {ja4Fingerprints.map((fp: { fingerprint: string; count: number }, i: number) => (
                  <JA4Item key={i} fingerprint={fp.fingerprint} count={fp.count} />
                ))}
              </div>
            ) : (
              <EmptyState icon={<Fingerprint />} message="No JA4 fingerprints detected" />
            )}
          </div>
        </div>

        {/* DNS Anomalies Panel */}
        <div className="sinkhole-panel">
          <div className="sinkhole-panel-header">
            <Globe />
            <h3>DNS Anomaly Detection</h3>
            {dnsAnomalies.length > 0 && (
              <span className="sinkhole-panel-badge">{dnsAnomalies.length}</span>
            )}
          </div>
          <div className="sinkhole-panel-content">
            {dnsAnomalies.length > 0 ? (
              <DNSTable anomalies={dnsAnomalies} onAnomalyClick={setSelectedAnomaly} />
            ) : (
              <EmptyState icon={<Globe />} message="No DNS anomalies detected" />
            )}
          </div>
        </div>
      </div>

      {/* Botnet Clusters */}
      <div className="sinkhole-panel">
        <div className="sinkhole-panel-header">
          <Users />
          <h3>Active Botnet Clusters</h3>
          {clusters.length > 0 && (
            <span className="sinkhole-panel-badge">{result.botnets.length}</span>
          )}
        </div>
        <div className="sinkhole-panel-content">
          {clusters.length > 0 ? (
            <div className="cluster-list">
              {clusters.map((cluster: BotnetCluster) => (
                <ClusterCard
                  key={cluster.cluster_id}
                  cluster={cluster}
                  onClick={() => setSelectedCluster(cluster)}
                />
              ))}
            </div>
          ) : (
            <EmptyState icon={<Shield />} message="No botnet clusters detected" />
          )}
        </div>
      </div>

      {/* Threat Intel & Activity */}
      <div className="sinkhole-grid sinkhole-grid-2">
        {/* Threat Intelligence */}
        <div className="sinkhole-panel">
          <div className="sinkhole-panel-header">
            <Target />
            <h3>Threat Intelligence</h3>
          </div>
          <div className="sinkhole-panel-content">
            {hasIntelData ? (
              <>
                <div className="threat-overview">
                  <div className="threat-overview-row">
                    <div className="threat-confidence">
                      <div className="threat-confidence-label">
                        <span>Confidence</span>
                        <span>{(confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="threat-confidence-bar">
                        <div
                          className="threat-confidence-fill"
                          style={{ width: `${confidence * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="threat-severity">
                      <span className={`threat-severity-badge ${severity}`}>{severity}</span>
                    </div>
                  </div>
                  {attackTypes.length > 0 && (
                    <div className="threat-attack-types">
                      {attackTypes.slice(0, 5).map((type: string, i: number) => (
                        <span key={i} className="threat-attack-tag">
                          {type.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* IOC Cards */}
                <div className="ioc-grid" style={{ marginTop: '1rem' }}>
                  <IOCCard
                    icon={<Globe />}
                    value={iocCount.ips}
                    label="Malicious IPs"
                    variant="ips"
                    onClick={() => iocCount.ips > 0 && openModal('ips')}
                    disabled={iocCount.ips === 0}
                  />
                  <IOCCard
                    icon={<Link />}
                    value={iocCount.domains}
                    label="Domains"
                    variant="domains"
                    onClick={() => iocCount.domains > 0 && openModal('domains')}
                    disabled={iocCount.domains === 0}
                  />
                  <IOCCard
                    icon={<Hash />}
                    value={iocCount.hashes}
                    label="Hashes"
                    variant="hashes"
                    onClick={() => iocCount.hashes > 0 && openModal('hashes')}
                    disabled={iocCount.hashes === 0}
                  />
                  <IOCCard
                    icon={<FileCode />}
                    value={yaraCount}
                    label="YARA Rules"
                    variant="yara"
                    onClick={() => yaraCount > 0 && openModal('yara')}
                    disabled={yaraCount === 0}
                  />
                </div>

                {/* Export Button */}
                <button
                  className="export-btn"
                  onClick={() => openModal(null)}
                  style={{ marginTop: '1rem', width: '100%' }}
                >
                  <Download />
                  Export Threat Intel
                </button>
              </>
            ) : (
              <EmptyState icon={<Target />} message="No threat intelligence data available" />
            )}
          </div>
        </div>

        {/* Activity Feed & MITRE */}
        <div className="sinkhole-panel">
          <div className="sinkhole-panel-header">
            <Activity />
            <h3>Recent Activity</h3>
          </div>
          <div className="sinkhole-panel-content">
            {recentEvents.length > 0 ? (
              <div className="activity-feed">
                {recentEvents.map((event: NetworkAnomaly, i: number) => (
                  <ActivityItem key={i} event={event} />
                ))}
              </div>
            ) : (
              <EmptyState icon={<Activity />} message="No recent activity" />
            )}

            {/* MITRE Techniques */}
            {mitreTechniques.length > 0 && (
              <div style={{ marginTop: '1.5rem' }}>
                <h4
                  style={{
                    fontSize: '0.75rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.75rem',
                    textTransform: 'uppercase',
                  }}
                >
                  MITRE ATT&CK Techniques
                </h4>
                <div className="mitre-list">
                  {mitreTechniques.slice(0, 6).map((tech: string) => (
                    <a
                      key={tech}
                      href={`https://attack.mitre.org/techniques/${tech}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mitre-tag"
                    >
                      {tech}
                      {MITRE_TECHNIQUES[tech] && ` - ${MITRE_TECHNIQUES[tech]}`}
                      <ExternalLink />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cluster Graph Visualization */}
      <div className="sinkhole-panel">
        <div className="sinkhole-panel-header">
          <Activity />
          <h3>Botnet Network Graph - C2 Hub Detection</h3>
        </div>
        <div className="sinkhole-panel-content" style={{ padding: 0 }}>
          {clusters.length > 0 || result.hub_nodes.length > 0 ? (
            <ClusterGraphV2 clusters={clusters} hubNodes={result.hub_nodes} />
          ) : (
            <div
              style={{ padding: '3rem 1rem', textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}
            >
              <Activity size={40} opacity={0.3} />
              <p style={{ margin: '1rem 0 0.5rem 0', fontSize: '0.9rem', fontWeight: 600 }}>
                No network data available
              </p>
              <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>
                Botnet clusters and C2 hubs will be visualized here
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Sinkhole Control Panel */}
      <div className="sinkhole-panel">
        <div className="sinkhole-panel-header">
          <Shield />
          <h3>Sinkhole Control - Domain Redirection</h3>
        </div>
        <div className="sinkhole-panel-content">
          <SinkholeControl anomalies={result.anomalies} clusters={clusters} />
        </div>
      </div>

      {/* IOC Detail Modal */}
      {showModal && (
        <IntelDetailModal
          category={modalCategory}
          iocs={iocs}
          iocCount={iocCount}
          yaraRules={yaraRules}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* Anomaly Detail Modal */}
      {selectedAnomaly && (
        <AnomalyDetailModal anomaly={selectedAnomaly} onClose={() => setSelectedAnomaly(null)} />
      )}

      {/* Cluster Detail Modal */}
      {selectedCluster && (
        <ClusterDetailModal cluster={selectedCluster} onClose={() => setSelectedCluster(null)} />
      )}
    </div>
  );
}
