/**
 * ClusterDetailModal - Shows detailed information about a botnet cluster
 */

import { X, Users } from 'lucide-react';
import type { BotnetCluster } from '../../../../../../types/discovery';

interface ClusterDetailModalProps {
  cluster: BotnetCluster;
  onClose: () => void;
}

export function ClusterDetailModal({ cluster, onClose }: ClusterDetailModalProps) {
  return (
    <div className="intel-detail-modal-overlay" onClick={onClose}>
      <div
        className="intel-detail-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '700px' }}
      >
        <div className="intel-modal-header">
          <div className="modal-title">
            <Users />
            <h2>Botnet Cluster #{cluster.cluster_id}</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="intel-modal-content" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Stats Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div
                style={{
                  textAlign: 'center',
                  padding: '1rem',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '8px',
                }}
              >
                <div
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: '#fff',
                    fontFamily: 'monospace',
                  }}
                >
                  {cluster.size}
                </div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    textTransform: 'uppercase',
                    marginTop: '0.25rem',
                  }}
                >
                  Bots
                </div>
              </div>
              <div
                style={{
                  textAlign: 'center',
                  padding: '1rem',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '8px',
                }}
              >
                <div
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: '#fff',
                    fontFamily: 'monospace',
                  }}
                >
                  {(cluster.detection_confidence * 100).toFixed(0)}%
                </div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    textTransform: 'uppercase',
                    marginTop: '0.25rem',
                  }}
                >
                  Confidence
                </div>
              </div>
              <div
                style={{
                  textAlign: 'center',
                  padding: '1rem',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '8px',
                }}
              >
                <div
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: '#fff',
                    fontFamily: 'monospace',
                  }}
                >
                  {(cluster.attack_coordination_score * 100).toFixed(0)}%
                </div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    textTransform: 'uppercase',
                    marginTop: '0.25rem',
                  }}
                >
                  Coordination
                </div>
              </div>
            </div>

            {/* Severity */}
            <div>
              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'rgba(255,255,255,0.5)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                }}
              >
                Severity
              </div>
              <span className={`threat-severity-badge ${cluster.severity}`}>
                {cluster.severity}
              </span>
            </div>

            {/* Protocols */}
            {cluster.common_protocols.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.5rem',
                    textTransform: 'uppercase',
                  }}
                >
                  Common Protocols
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {cluster.common_protocols.map((proto, i) => (
                    <span key={i} className="cluster-protocol">
                      {proto}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* C&C Server */}
            {cluster.suspected_cc_ip && (
              <div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.5rem',
                    textTransform: 'uppercase',
                  }}
                >
                  Suspected C&C Server
                </div>
                <code
                  style={{
                    padding: '0.5rem',
                    background: 'rgba(255,71,87,0.1)',
                    border: '1px solid rgba(255,71,87,0.2)',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    color: '#ff6b9d',
                    display: 'inline-block',
                  }}
                >
                  {cluster.suspected_cc_ip}
                </code>
              </div>
            )}

            {/* Member IPs */}
            <div>
              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'rgba(255,255,255,0.5)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                }}
              >
                Member IPs ({cluster.member_ips.length})
              </div>
              <div
                style={{
                  maxHeight: '200px',
                  overflow: 'auto',
                  background: 'rgba(0,0,0,0.3)',
                  padding: '1rem',
                  borderRadius: '8px',
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: '0.5rem',
                  }}
                >
                  {cluster.member_ips.slice(0, 50).map((ip, i) => (
                    <code key={i} style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.8)' }}>
                      {ip}
                    </code>
                  ))}
                </div>
                {cluster.member_ips.length > 50 && (
                  <div
                    style={{
                      marginTop: '0.5rem',
                      fontSize: '0.7rem',
                      color: 'rgba(255,255,255,0.5)',
                      textAlign: 'center',
                    }}
                  >
                    ... and {cluster.member_ips.length - 50} more
                  </div>
                )}
              </div>
            </div>

            {/* Timeline */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.5rem',
                    textTransform: 'uppercase',
                  }}
                >
                  First Detected
                </div>
                <div
                  style={{
                    fontSize: '0.85rem',
                    color: 'rgba(255,255,255,0.9)',
                    fontFamily: 'monospace',
                  }}
                >
                  {new Date(cluster.first_detected).toLocaleString()}
                </div>
              </div>
              <div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.5rem',
                    textTransform: 'uppercase',
                  }}
                >
                  Last Activity
                </div>
                <div
                  style={{
                    fontSize: '0.85rem',
                    color: 'rgba(255,255,255,0.9)',
                    fontFamily: 'monospace',
                  }}
                >
                  {new Date(cluster.last_activity).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
