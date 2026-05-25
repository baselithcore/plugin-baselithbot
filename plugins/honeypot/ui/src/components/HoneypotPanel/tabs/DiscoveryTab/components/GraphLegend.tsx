import { CLUSTER_COLORS } from '../constants/graphConstants';

interface GraphLegendProps {
  clusters: Array<{ id: string; size: number; label?: string }>;
}

export function GraphLegend({ clusters }: GraphLegendProps) {
  return (
    <div className="graph-legend">
      <div className="legend-title">Network Topology</div>
      <div className="legend-section">
        <div className="legend-item">
          <span className="legend-node hub-node"></span>
          <span className="legend-text">Confirmed C&C</span>
        </div>
        <div className="legend-item">
          <span className="legend-node potential-cc-node"></span>
          <span className="legend-text">Potential C&C</span>
        </div>
        <div className="legend-item">
          <span className="legend-node bot-node"></span>
          <span className="legend-text">Botnet Node</span>
        </div>
      </div>
      {clusters.length > 0 && (
        <>
          <div className="legend-divider" />
          <div className="legend-section-title">Clusters</div>
          <div className="legend-clusters">
            {clusters.map((cluster: any) => (
              <div key={cluster.id} className="legend-cluster-item">
                <span
                  className="legend-cluster-dot"
                  style={{
                    backgroundColor: CLUSTER_COLORS[parseInt(cluster.id) % CLUSTER_COLORS.length],
                  }}
                />
                <span className="legend-cluster-label">
                  {cluster.label && cluster.label !== 'undefined'
                    ? cluster.label
                    : `Cluster #${cluster.id}`}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
      <div className="legend-hint">Click nodes for details • Scroll to zoom • Drag to pan</div>
    </div>
  );
}
