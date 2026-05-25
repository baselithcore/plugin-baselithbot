/**
 * BotnetsCCTab - Unified Botnets & C&C Analysis Module
 *
 * Combines BotnetSection and SinkholeMonitor functionalities into a single,
 * comprehensive view for botnet detection, C&C infrastructure analysis,
 * and sinkhole management.
 *
 * Layout:
 * - Hero Stats (Overview)
 * - Botnet Clusters + C&C Servers (Side by side)
 * - JA4 Fingerprints + DNS Anomalies (Side by side)
 * - Threat Intelligence + Activity & MITRE (Side by side)
 * - Network Graph Visualization
 * - Sinkhole Control Panel
 */

import { useState } from 'react';
import { Users, Server, Shield, Globe, Fingerprint, Target, Activity } from 'lucide-react';
import type {
  DiscoveryResult,
  BotnetCluster,
  HubNode,
  DiscoveryGraphNode,
  NetworkAnomaly,
} from '../../../../../types/discovery';
import { useSinkholeData } from '../SinkholeMonitor/hooks/useSinkholeData';

// Reuse existing components from SinkholeMonitor
import { StatCard } from '../SinkholeMonitor/cards/StatCard';
import { DNSTable } from '../SinkholeMonitor/tables/DNSTable';
import { JA4Item } from '../SinkholeMonitor/components/JA4Item';
import { EmptyState as SinkholeEmptyState } from '../SinkholeMonitor/components/EmptyState';
import { SinkholeControl } from '../SinkholeMonitor/components/SinkholeControl';

import { AnomalyDetailModal } from '../SinkholeMonitor/modals/AnomalyDetailModal';
import { ClusterDetailModal } from '../SinkholeMonitor/modals/ClusterDetailModal';
import { IntelDetailModal } from '../IntelDetailModal';
import { DiscoveryDetailModal } from '../DiscoveryDetailModal';

// Modularized components
import { BotnetClusterCard } from './components/BotnetClusterCard';
import { CCServersTable } from './components/CCServersTable';
import { ThreatIntelPanel } from './components/ThreatIntelPanel';
import { ActivityFeedPanel } from './components/ActivityFeedPanel';

import './BotnetsCCTab.css';

// Import existing BotnetSection CSS for cluster cards
import '../BotnetSection.css';
import '../SinkholeMonitor/SinkholeMonitor.css';

interface BotnetsCCTabProps {
  result: DiscoveryResult;
}

type DetailCategory = 'botnet' | 'hub' | null;
type DetailItem = BotnetCluster | HubNode | null;
type IOCCategory = 'ips' | 'domains' | 'hashes' | 'yara' | null;

export function BotnetsCCTab({ result }: BotnetsCCTabProps) {
  // State for BotnetSection functionality
  const [selectedItem, setSelectedItem] = useState<DetailItem>(null);
  const [selectedCategory, setSelectedCategory] = useState<DetailCategory>(null);

  // State for SinkholeMonitor functionality
  const [showIOCModal, setShowIOCModal] = useState(false);
  const [modalCategory, setModalCategory] = useState<IOCCategory>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<NetworkAnomaly | null>(null);
  const [selectedClusterDetail, setSelectedClusterDetail] = useState<BotnetCluster | null>(null);

  // Get sinkhole data using existing hook
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

  // Handlers for BotnetSection
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

  // Handler for IOC Modal
  const openIOCModal = (category: IOCCategory) => {
    setModalCategory(category);
    setShowIOCModal(true);
  };

  return (
    <div className="botnets-cc-tab">
      {/* Hero Stats Section */}
      <div className="botnets-hero-stats">
        <StatCard
          icon={<Users />}
          value={result.botnets.length}
          label="Botnet Clusters"
          variant="danger"
        />
        <StatCard
          icon={<Server />}
          value={result.hub_nodes.length}
          label="C&C Servers"
          variant="warning"
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
      </div>

      {/* Main Grid: Botnet Clusters + C&C Servers */}
      <div className="botnets-main-grid">
        {/* Botnet Clusters Panel */}
        <div className="botnets-panel">
          <div className="botnets-panel-header">
            <Users size={16} />
            <h3>Botnet Clusters</h3>
            <span className="botnets-panel-badge">{result.botnets.length}</span>
          </div>
          <div className="botnets-panel-content">
            {result.botnets.length === 0 ? (
              <div className="botnets-empty">
                <Shield size={24} />
                <span>No botnet clusters detected</span>
              </div>
            ) : (
              result.botnets.map((cluster) => (
                <BotnetClusterCard
                  key={cluster.cluster_id}
                  cluster={cluster}
                  getNodeInfo={getNodeInfo}
                  onViewDetails={handleBotnetClick}
                />
              ))
            )}
          </div>
        </div>

        {/* Hub Nodes (C&C Servers) Panel */}
        <div className="botnets-panel">
          <div className="botnets-panel-header">
            <Server size={16} />
            <h3>Potential C&C Servers</h3>
            <span className="botnets-panel-badge">{result.hub_nodes.length}</span>
          </div>
          <div className="botnets-panel-content">
            {result.hub_nodes.length === 0 ? (
              <div className="botnets-empty">
                <Shield size={24} />
                <span>No hub nodes detected</span>
              </div>
            ) : (
              <CCServersTable hubNodes={result.hub_nodes} onHubClick={handleHubClick} />
            )}
          </div>
        </div>
      </div>

      {/* Intel Grid: JA4 Fingerprints + DNS Anomalies */}
      <div className="botnets-intel-grid">
        {/* JA4 Fingerprints Panel */}
        <div className="botnets-panel">
          <div className="botnets-panel-header">
            <Fingerprint size={16} />
            <h3>JA4+ TLS Fingerprints</h3>
            {ja4Fingerprints.length > 0 && (
              <span className="botnets-panel-badge">{ja4Fingerprints.length}</span>
            )}
          </div>
          <div className="botnets-panel-content">
            {ja4Fingerprints.length > 0 ? (
              <div className="ja4-list">
                {ja4Fingerprints.map((fp: { fingerprint: string; count: number }, i: number) => (
                  <JA4Item key={i} fingerprint={fp.fingerprint} count={fp.count} />
                ))}
              </div>
            ) : (
              <SinkholeEmptyState icon={<Fingerprint />} message="No JA4 fingerprints detected" />
            )}
          </div>
        </div>

        {/* DNS Anomalies Panel */}
        <div className="botnets-panel">
          <div className="botnets-panel-header">
            <Globe size={16} />
            <h3>DNS Anomaly Detection</h3>
            {dnsAnomalies.length > 0 && (
              <span className="botnets-panel-badge">{dnsAnomalies.length}</span>
            )}
          </div>
          <div className="botnets-panel-content">
            {dnsAnomalies.length > 0 ? (
              <DNSTable anomalies={dnsAnomalies} onAnomalyClick={setSelectedAnomaly} />
            ) : (
              <SinkholeEmptyState icon={<Globe />} message="No DNS anomalies detected" />
            )}
          </div>
        </div>
      </div>

      {/* Threat Intelligence + Activity Section */}
      <div className="botnets-intel-grid">
        {/* Threat Intelligence Panel */}
        <div className="botnets-panel">
          <div className="botnets-panel-header">
            <Target size={16} />
            <h3>Threat Intelligence</h3>
          </div>
          <div className="botnets-panel-content">
            <ThreatIntelPanel
              hasIntelData={hasIntelData}
              confidence={confidence}
              severity={severity}
              attackTypes={attackTypes}
              iocCount={iocCount}
              yaraCount={yaraCount}
              onOpenIOCModal={openIOCModal}
            />
          </div>
        </div>

        {/* Activity Feed & MITRE Panel */}
        <div className="botnets-panel">
          <div className="botnets-panel-header">
            <Activity size={16} />
            <h3>Recent Activity</h3>
          </div>
          <div className="botnets-panel-content">
            <ActivityFeedPanel recentEvents={recentEvents} mitreTechniques={mitreTechniques} />
          </div>
        </div>
      </div>

      {/* Sinkhole Control Panel */}
      <div className="botnets-panel">
        <div className="botnets-panel-header">
          <Shield size={16} />
          <h3>Sinkhole Control - Domain Redirection</h3>
        </div>
        <div className="botnets-panel-content">
          <SinkholeControl anomalies={result.anomalies} clusters={clusters} />
        </div>
      </div>

      {/* Modals */}
      {selectedItem && selectedCategory && (
        <DiscoveryDetailModal
          item={selectedItem}
          category={selectedCategory}
          onClose={handleCloseModal}
        />
      )}

      {showIOCModal && (
        <IntelDetailModal
          category={modalCategory}
          iocs={iocs}
          iocCount={iocCount}
          yaraRules={yaraRules}
          onClose={() => setShowIOCModal(false)}
        />
      )}

      {selectedAnomaly && (
        <AnomalyDetailModal anomaly={selectedAnomaly} onClose={() => setSelectedAnomaly(null)} />
      )}

      {selectedClusterDetail && (
        <ClusterDetailModal
          cluster={selectedClusterDetail}
          onClose={() => setSelectedClusterDetail(null)}
        />
      )}
    </div>
  );
}

export default BotnetsCCTab;
