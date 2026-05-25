/**
 * SinkholeControl - Monitor and control sinkholed domains
 *
 * Tracks domains that have been redirected to honeypots for containment.
 * Now connected to real backend APIs for persistent storage.
 */

import { useState, useEffect } from 'react';
import {
  Shield,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Play,
  Pause,
  Wifi,
  WifiOff,
} from 'lucide-react';
import type { NetworkAnomaly } from '../../../../../../types/discovery';
import { useSinkholeAPI } from '../hooks/useSinkholeAPI';
import { useSinkholeWebSocket } from '../hooks/useSinkholeWebSocket';

interface SinkholedDomain {
  id?: number;
  domain: string;
  redirectedAt: string;
  requestCount: number;
  uniqueIPs: number;
  status: 'active' | 'paused' | 'terminated';
  lastActivity: string;
  associatedCluster?: string;
  anomalyId?: string;
}

interface SinkholeControlProps {
  anomalies: NetworkAnomaly[];
  clusters: Array<{ cluster_id: string; size: number }>;
}

export function SinkholeControl({ anomalies }: SinkholeControlProps) {
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [sinkholedDomains, setSinkholedDomains] = useState<SinkholedDomain[]>([]);
  const [stats, setStats] = useState({ active: 0, paused: 0, totalRequests: 0, totalIPs: 0 });
  const { listSinkholes, getSinkholeStats, createSinkhole, updateSinkholeStatus } =
    useSinkholeAPI();

  // WebSocket for real-time updates
  const { connected: wsConnected } = useSinkholeWebSocket({
    onEvent: (event) => {
      // Handle real-time events
      switch (event.event) {
        case 'request_intercepted':
          // Reload to get updated request counts
          loadSinkholes();
          break;
        case 'status_changed':
          // Update specific domain status
          if (event.data?.domain_id) {
            setSinkholedDomains((prev) =>
              prev.map((d) =>
                d.id === event.data.domain_id ? { ...d, status: event.data.new_status } : d
              )
            );
          }
          break;
        case 'domain_created':
          // Reload to show new domain
          loadSinkholes();
          break;
        case 'stats_updated':
          // Update stats in real-time
          if (event.data?.stats) {
            setStats(event.data.stats);
          }
          break;
      }
    },
  });

  // Load sinkholed domains from backend
  const loadSinkholes = async () => {
    const domains = await listSinkholes({ limit: 100 });
    if (domains) {
      setSinkholedDomains(
        domains.map((d) => ({
          id: d.id,
          domain: d.domain,
          redirectedAt: d.created_at || '',
          requestCount: d.request_count,
          uniqueIPs: d.unique_ips_count,
          status: d.status as 'active' | 'paused' | 'terminated',
          lastActivity: d.last_activity || '',
          associatedCluster: d.associated_cluster_id,
          anomalyId: d.anomaly_id,
        }))
      );
    }

    const statsData = await getSinkholeStats();
    if (statsData) {
      setStats({
        active: statsData.active,
        paused: statsData.paused,
        totalRequests: statsData.total_requests,
        totalIPs: 0, // Will be computed from domains
      });
    }
  };

  // Load on mount
  useEffect(() => {
    loadSinkholes();
  }, []);

  // Auto-create sinkhole entries for DGA candidates not yet in DB
  useEffect(() => {
    const dgaCandidates = anomalies.filter(
      (a) =>
        a.anomaly_type.includes('dga') &&
        a.confidence > 0.7 &&
        a.metadata?.domain &&
        !sinkholedDomains.some((sd) => sd.domain === a.metadata?.domain)
    );

    // Auto-create in background (no await - fire and forget)
    dgaCandidates.forEach((anomaly) => {
      if (anomaly.metadata?.domain) {
        createSinkhole({
          domain: anomaly.metadata.domain,
          anomaly_id: anomaly.anomaly_id,
          detection_method: 'dga',
          entropy: anomaly.metadata.entropy as number,
          confidence: anomaly.confidence,
          associated_cluster_id: anomaly.metadata.cluster_id as string,
          tags: (anomaly.metadata.tags as string[]) || [],
        }).then(() => {
          // Reload after creation
          loadSinkholes();
        });
      }
    });
  }, [anomalies]);

  const handleToggleSinkhole = async (domainId: number, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    const result = await updateSinkholeStatus(domainId, newStatus as 'active' | 'paused');

    if (result) {
      // Update local state
      setSinkholedDomains((prev) =>
        prev.map((d) => (d.id === domainId ? { ...d, status: newStatus as any } : d))
      );

      // Reload stats
      loadSinkholes();
    }
  };

  return (
    <div className="sinkhole-control">
      {/* WebSocket Connection Indicator */}
      <div className="sinkhole-ws-status">
        {wsConnected ? (
          <span className="ws-status-connected">
            <Wifi size={14} />
            Live Updates
          </span>
        ) : (
          <span className="ws-status-disconnected">
            <WifiOff size={14} />
            Disconnected
          </span>
        )}
      </div>

      {/* Stats Overview */}
      <div className="sinkhole-control-stats">
        <div className="sinkhole-stat-mini">
          <Zap size={16} />
          <div>
            <div className="sinkhole-stat-mini-value">{stats.active}</div>
            <div className="sinkhole-stat-mini-label">Active Sinkholes</div>
          </div>
        </div>
        <div className="sinkhole-stat-mini">
          <Shield size={16} />
          <div>
            <div className="sinkhole-stat-mini-value">{stats.totalRequests}</div>
            <div className="sinkhole-stat-mini-label">Intercepted Requests</div>
          </div>
        </div>
        <div className="sinkhole-stat-mini">
          <AlertTriangle size={16} />
          <div>
            <div className="sinkhole-stat-mini-value">{stats.totalIPs}</div>
            <div className="sinkhole-stat-mini-label">Unique Attackers</div>
          </div>
        </div>
      </div>

      {/* Sinkholed Domains List */}
      <div className="sinkhole-domains-list">
        {sinkholedDomains.length > 0 ? (
          sinkholedDomains.map((domain: SinkholedDomain, i: number) => (
            <div
              key={domain.id || i}
              className={`sinkhole-domain-item ${selectedDomain === domain.domain ? 'selected' : ''}`}
              onClick={() => setSelectedDomain(domain.domain)}
            >
              <div className="sinkhole-domain-header">
                <div className="sinkhole-domain-info">
                  <span className="sinkhole-domain-name" title={domain.domain}>
                    {domain.domain}
                  </span>
                  {domain.associatedCluster && (
                    <span
                      className="sinkhole-cluster-badge"
                      title={`Part of cluster ${domain.associatedCluster}`}
                    >
                      Cluster {domain.associatedCluster.slice(0, 6)}
                    </span>
                  )}
                </div>
                <div className="sinkhole-domain-status">
                  {domain.status === 'active' && (
                    <span className="sinkhole-status-badge active">
                      <CheckCircle size={12} />
                      Active
                    </span>
                  )}
                  {domain.status === 'paused' && (
                    <span className="sinkhole-status-badge paused">
                      <Pause size={12} />
                      Paused
                    </span>
                  )}
                  {domain.status === 'terminated' && (
                    <span className="sinkhole-status-badge terminated">
                      <XCircle size={12} />
                      Terminated
                    </span>
                  )}
                </div>
              </div>

              <div className="sinkhole-domain-metrics">
                <div className="sinkhole-metric">
                  <span className="sinkhole-metric-label">Requests</span>
                  <span className="sinkhole-metric-value">{domain.requestCount}</span>
                </div>
                <div className="sinkhole-metric">
                  <span className="sinkhole-metric-label">Unique IPs</span>
                  <span className="sinkhole-metric-value">{domain.uniqueIPs}</span>
                </div>
                {domain.lastActivity && (
                  <div className="sinkhole-metric">
                    <span className="sinkhole-metric-label">Last Activity</span>
                    <span className="sinkhole-metric-value">
                      {new Date(domain.lastActivity).toLocaleTimeString()}
                    </span>
                  </div>
                )}
              </div>

              {domain.status !== 'terminated' && domain.id && (
                <div className="sinkhole-domain-actions">
                  <button
                    className={`sinkhole-action-btn ${domain.status === 'active' ? 'danger' : 'primary'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleSinkhole(domain.id!, domain.status);
                    }}
                    title={domain.status === 'active' ? 'Pause sinkhole' : 'Activate sinkhole'}
                  >
                    {domain.status === 'active' ? <Pause size={14} /> : <Play size={14} />}
                    {domain.status === 'active' ? 'Pause' : 'Activate'}
                  </button>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="sinkhole-empty-state">
            <Shield size={40} opacity={0.3} />
            <p>No sinkholed domains</p>
            <span>DGA-detected domains will appear here for sinkholing</span>
          </div>
        )}
      </div>
    </div>
  );
}
