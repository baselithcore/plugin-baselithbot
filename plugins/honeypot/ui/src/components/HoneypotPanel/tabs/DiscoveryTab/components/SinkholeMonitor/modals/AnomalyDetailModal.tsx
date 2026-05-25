/**
 * AnomalyDetailModal - Shows detailed information about a network anomaly
 */

import { X, Activity } from 'lucide-react';
import type { NetworkAnomaly } from '../../../../../../types/discovery';

interface AnomalyDetailModalProps {
  anomaly: NetworkAnomaly;
  onClose: () => void;
}

export function AnomalyDetailModal({ anomaly, onClose }: AnomalyDetailModalProps) {
  return (
    <div className="intel-detail-modal-overlay" onClick={onClose}>
      <div
        className="intel-detail-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '600px' }}
      >
        <div className="intel-modal-header">
          <div className="modal-title">
            <Activity />
            <h2>Anomaly Details</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="intel-modal-content" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'rgba(255,255,255,0.5)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                }}
              >
                Type
              </div>
              <div style={{ fontSize: '0.9rem', color: '#00ffff', fontFamily: 'monospace' }}>
                {anomaly.anomaly_type.replace(/_/g, ' ')}
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
                Description
              </div>
              <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.9)' }}>
                {anomaly.description}
              </div>
            </div>

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
                  Severity
                </div>
                <span className={`threat-severity-badge ${anomaly.severity}`}>
                  {anomaly.severity}
                </span>
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
                  Confidence
                </div>
                <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>
                  {(anomaly.confidence * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {anomaly.involved_ips && anomaly.involved_ips.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.5rem',
                    textTransform: 'uppercase',
                  }}
                >
                  Involved IPs
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {anomaly.involved_ips.slice(0, 10).map((ip, i) => (
                    <code
                      key={i}
                      style={{
                        padding: '0.25rem 0.5rem',
                        background: 'rgba(0,255,255,0.1)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        color: '#00ffff',
                      }}
                    >
                      {ip}
                    </code>
                  ))}
                </div>
              </div>
            )}

            {anomaly.metadata && Object.keys(anomaly.metadata).length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255,255,255,0.5)',
                    marginBottom: '0.5rem',
                    textTransform: 'uppercase',
                  }}
                >
                  Metadata
                </div>
                <pre
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '1rem',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    overflow: 'auto',
                    maxHeight: '200px',
                  }}
                >
                  {JSON.stringify(anomaly.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
