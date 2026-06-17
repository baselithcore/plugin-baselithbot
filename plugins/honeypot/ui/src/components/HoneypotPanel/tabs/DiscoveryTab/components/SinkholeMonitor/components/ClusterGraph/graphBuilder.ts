import type { BotnetCluster, HubNode } from '../../../../../../types/discovery';
import type { Node, Edge } from './types';

export function buildGraphData(
  clusters: BotnetCluster[],
  hubNodes: HubNode[]
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Add hub nodes (C2 servers)
  hubNodes.forEach((hub, i) => {
    nodes.push({
      id: hub.ip,
      type: 'hub',
      label: hub.ip,
      x: Math.cos((i * 2 * Math.PI) / hubNodes.length) * 150,
      y: Math.sin((i * 2 * Math.PI) / hubNodes.length) * 150,
      vx: 0,
      vy: 0,
      size: Math.sqrt(hub.degree_centrality * 1000) + 15,
      centrality: hub.degree_centrality,
    });
  });

  // Add cluster nodes and bots
  clusters.forEach((cluster, clusterIdx) => {
    const clusterCenter = {
      x: Math.cos((clusterIdx * 2 * Math.PI) / clusters.length) * 200,
      y: Math.sin((clusterIdx * 2 * Math.PI) / clusters.length) * 200,
    };

    // Add cluster center node
    nodes.push({
      id: `cluster-${cluster.cluster_id}`,
      type: 'cluster',
      label: `Cluster ${cluster.cluster_id.slice(0, 6)}`,
      x: clusterCenter.x,
      y: clusterCenter.y,
      vx: 0,
      vy: 0,
      size: Math.sqrt(cluster.size) * 8 + 10,
      cluster: cluster.cluster_id,
    });

    // Add bot nodes (sample up to 10 per cluster for performance)
    const sampleSize = Math.min(10, cluster.member_ips.length);
    cluster.member_ips.slice(0, sampleSize).forEach((ip, i) => {
      const angle = (i * 2 * Math.PI) / sampleSize;
      const radius = 80;
      nodes.push({
        id: ip,
        type: 'bot',
        label: ip,
        x: clusterCenter.x + Math.cos(angle) * radius,
        y: clusterCenter.y + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        size: 6,
        cluster: cluster.cluster_id,
      });

      // Connect bot to cluster center
      edges.push({
        source: ip,
        target: `cluster-${cluster.cluster_id}`,
        strength: 0.5,
      });
    });

    // Connect cluster to its suspected C2
    if (cluster.suspected_cc_ip) {
      edges.push({
        source: `cluster-${cluster.cluster_id}`,
        target: cluster.suspected_cc_ip,
        strength: 1.0,
      });
    }

    // Connect to associated C2s
    cluster.associated_cc_ips?.forEach((ccIP) => {
      edges.push({
        source: `cluster-${cluster.cluster_id}`,
        target: ccIP,
        strength: 0.7,
      });
    });
  });

  return { nodes, edges };
}
