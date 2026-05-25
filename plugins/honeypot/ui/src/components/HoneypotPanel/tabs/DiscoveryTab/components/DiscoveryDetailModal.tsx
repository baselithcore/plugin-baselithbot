import { useState } from 'react';
import {
  X,
  Bug,
  Zap,
  AlertTriangle,
  Server,
  Users,
  Target,
  Shield,
  FileText,
  BarChart3,
  Network,
  Clock,
} from 'lucide-react';
import type { NetworkAnomaly, BotnetCluster, HubNode, DiscoveryGraphNode } from '../../../../types';
import { getSeverityClass } from '../utils';
import { AnomalyContent } from './modal/AnomalyContent';
import { BotnetContent } from './modal/BotnetContent';
import { HubContent } from './modal/HubContent';
import { AttackerContent } from './modal/AttackerContent';
import type { ModalTab } from '../discoveryTypes';

import './DiscoveryDetailModal.css';

type DetailItemType = NetworkAnomaly | BotnetCluster | HubNode | DiscoveryGraphNode | null;
type DetailCategory = 'zeroday' | 'exploit' | 'anomaly' | 'botnet' | 'hub' | 'attacker' | null;

interface DiscoveryDetailModalProps {
  item: DetailItemType;
  category: DetailCategory;
  onClose: () => void;
}

export function DiscoveryDetailModal({ item, category, onClose }: DiscoveryDetailModalProps) {
  const [activeTab, setActiveTab] = useState<ModalTab>('overview');

  if (!item || !category) return null;

  const isAnomaly = category === 'zeroday' || category === 'exploit' || category === 'anomaly';
  const anomaly = isAnomaly ? (item as NetworkAnomaly) : null;
  const botnet = category === 'botnet' ? (item as BotnetCluster) : null;
  const hub = category === 'hub' ? (item as HubNode) : null;
  const attacker = category === 'attacker' ? (item as DiscoveryGraphNode) : null;

  const getTitle = () => {
    if (anomaly) {
      if (category === 'zeroday') return 'Zero-Day Candidate Analysis';
      if (category === 'exploit') return 'Exploit Pattern Analysis';
      return 'Network Anomaly Analysis';
    }
    if (botnet) return 'Botnet Cluster Analysis';
    if (hub) return 'C&C Server Analysis';
    if (attacker) return 'Attacker Node Details';
    return 'Threat Analysis';
  };

  const getIcon = () => {
    if (category === 'zeroday') return <Bug size={20} />;
    if (category === 'exploit') return <Zap size={20} />;
    if (category === 'anomaly') return <AlertTriangle size={20} />;
    if (category === 'botnet') return <Users size={20} />;
    if (category === 'hub') return <Server size={20} />;
    if (category === 'attacker') return <Target size={20} />;
    return <Shield size={20} />;
  };

  const getCategoryColor = () => {
    if (category === 'zeroday') return 'zeroday';
    if (category === 'exploit') return 'exploit';
    if (category === 'botnet' || category === 'hub') return 'botnet';
    if (category === 'attacker') return 'default'; // Or add a specific class if needed
    return 'default';
  };

  // Determine available tabs based on content
  const getTabs = (): { id: ModalTab; label: string; icon: React.ReactNode }[] => {
    const tabs: { id: ModalTab; label: string; icon: React.ReactNode }[] = [
      { id: 'overview', label: 'Overview', icon: <FileText size={14} /> },
    ];

    if (anomaly) {
      if (anomaly.metadata && Object.keys(anomaly.metadata).length > 0) {
        tabs.push({ id: 'technical', label: 'Technical', icon: <BarChart3 size={14} /> });
      }
      if (anomaly.involved_ips && anomaly.involved_ips.length > 0) {
        tabs.push({ id: 'network', label: 'Network', icon: <Network size={14} /> });
      }
    }

    if (botnet) {
      tabs.push({ id: 'technical', label: 'Analysis', icon: <BarChart3 size={14} /> });
      tabs.push({ id: 'network', label: 'Members', icon: <Users size={14} /> });
      tabs.push({ id: 'timeline', label: 'Timeline', icon: <Clock size={14} /> });
    }

    if (hub) {
      tabs.push({ id: 'technical', label: 'Threat Score', icon: <Target size={14} /> });
      tabs.push({ id: 'timeline', label: 'Activity', icon: <Clock size={14} /> });
    }

    if (attacker) {
      // For simple nodes, overview might be enough, but we can add more if needed
    }

    return tabs;
  };

  const tabs = getTabs();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={`modal-container modal-${getCategoryColor()}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="modal-header">
          <div className="modal-header-content">
            <div className={`modal-icon ${getCategoryColor()}`}>{getIcon()}</div>
            <div className="modal-title-section">
              <h2 className="modal-title">{getTitle()}</h2>
              {anomaly && (
                <span className={`modal-severity ${getSeverityClass(anomaly.severity)}`}>
                  {anomaly.severity.toUpperCase()}
                </span>
              )}
              {botnet && (
                <span className={`modal-severity ${getSeverityClass(botnet.severity)}`}>
                  {botnet.severity.toUpperCase()}
                </span>
              )}
              {hub && (
                <span
                  className={`modal-severity ${hub.is_confirmed_cc ? 'severity-critical' : 'severity-medium'}`}
                >
                  {hub.is_confirmed_cc ? 'CONFIRMED C&C' : 'POTENTIAL C&C'}
                </span>
              )}
              {attacker && (
                <span className={`modal-severity ${getSeverityClass(attacker.severity)}`}>
                  {attacker.severity.toUpperCase()}
                </span>
              )}
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </header>

        {/* Tabs Navigation */}
        {tabs.length > 1 && (
          <nav className="modal-tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`modal-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        )}

        {/* Content */}
        <div className="modal-content">
          {/* ANOMALY CONTENT (Zero-Day, Exploit, Network Anomaly) */}
          {anomaly && (
            <AnomalyContent
              anomaly={anomaly}
              category={category as 'zeroday' | 'exploit' | 'anomaly'}
              activeTab={activeTab}
            />
          )}

          {/* BOTNET CLUSTER CONTENT */}
          {botnet && <BotnetContent botnet={botnet} activeTab={activeTab} />}

          {/* HUB NODE (C&C SERVER) CONTENT */}
          {hub && <HubContent hub={hub} activeTab={activeTab} />}

          {/* ATTACKER NODE CONTENT */}
          {attacker && <AttackerContent attacker={attacker} activeTab={activeTab} />}
        </div>
      </div>
    </div>
  );
}
