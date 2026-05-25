/**
 * ClusterCard - Display a botnet cluster summary
 */

import type { BotnetCluster } from '../../../../../../types/discovery';

interface ClusterCardProps {
  cluster: BotnetCluster;
  onClick: () => void;
}

export function ClusterCard({ cluster, onClick }: ClusterCardProps) {
  return (
    <div className={`cluster-card ${cluster.severity}`} onClick={onClick}>
      <div className="cluster-header">
        <span className="cluster-id">Cluster #{cluster.cluster_id}</span>
        <span className={`cluster-severity ${cluster.severity}`}>{cluster.severity}</span>
      </div>
      <div className="cluster-stats">
        <div className="cluster-stat">
          <span className="cluster-stat-value">{cluster.size}</span>
          <span className="cluster-stat-label">Bots</span>
        </div>
        <div className="cluster-stat">
          <span className="cluster-stat-value">
            {(cluster.detection_confidence * 100).toFixed(0)}%
          </span>
          <span className="cluster-stat-label">Confidence</span>
        </div>
        <div className="cluster-stat">
          <span className="cluster-stat-value">
            {(cluster.attack_coordination_score * 100).toFixed(0)}%
          </span>
          <span className="cluster-stat-label">Coordination</span>
        </div>
      </div>
      {cluster.common_protocols.length > 0 && (
        <div className="cluster-protocols">
          {cluster.common_protocols.map((proto, i) => (
            <span key={i} className="cluster-protocol">
              {proto}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
