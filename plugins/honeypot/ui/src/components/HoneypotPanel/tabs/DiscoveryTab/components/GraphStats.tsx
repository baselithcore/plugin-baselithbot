interface GraphStatsProps {
  nodeCount: number;
  edgeCount: number;
  clusterCount: number;
}

export function GraphStats({ nodeCount, edgeCount, clusterCount }: GraphStatsProps) {
  return (
    <div className="graph-stats-overlay">
      <div className="stat-item">
        <span className="stat-value">{nodeCount}</span>
        <span className="stat-label">nodes</span>
      </div>
      <div className="stat-item">
        <span className="stat-value">{edgeCount}</span>
        <span className="stat-label">connections</span>
      </div>
      <div className="stat-item">
        <span className="stat-value">{clusterCount}</span>
        <span className="stat-label">clusters</span>
      </div>
    </div>
  );
}
