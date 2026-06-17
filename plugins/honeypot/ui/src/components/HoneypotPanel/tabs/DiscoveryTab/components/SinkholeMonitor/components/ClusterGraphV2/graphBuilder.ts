import type { BotnetCluster, HubNode } from '../../../../../../types/discovery';
import type { Node, Link } from './types';

// Community colors for clusters
const COMMUNITY_COLORS = [
  '#2ed573',
  '#1e90ff',
  '#a55eea',
  '#ffa502',
  '#00d2d3',
  '#ff6b81',
  '#7bed9f',
  '#70a1ff',
];

export function buildClusterGraphData(
  clusters: BotnetCluster[],
  hubNodes: HubNode[]
): { nodes: Node[]; links: Link[] } {
  const nodes: Node[] = [];
  const links: Link[] = [];

  // Add hub nodes (C2 servers)
  hubNodes.forEach((hub) => {
    nodes.push({
      id: hub.ip,
      type: 'hub',
      label: hub.ip,
      size: Math.sqrt(hub.degree_centrality * 1000) + 15,
      centrality: hub.degree_centrality,
      color: hub.is_confirmed_cc ? '#ff4757' : '#ffaa00',
    });
  });

  // Add cluster nodes and bots
  clusters.forEach((cluster, clusterIdx) => {
    const clusterColor = COMMUNITY_COLORS[clusterIdx % COMMUNITY_COLORS.length];

    // Add cluster center node
    nodes.push({
      id: `cluster-${cluster.cluster_id}`,
      type: 'cluster',
      label: `Cluster ${cluster.cluster_id.slice(0, 6)}`,
      size: Math.sqrt(cluster.size) * 8 + 10,
      cluster: cluster.cluster_id,
      color: clusterColor,
    });

    // Add bot nodes (sample up to 10 per cluster for performance)
    const sampleSize = Math.min(10, cluster.member_ips.length);
    cluster.member_ips.slice(0, sampleSize).forEach((ip) => {
      nodes.push({
        id: ip,
        type: 'bot',
        label: ip,
        size: 6,
        cluster: cluster.cluster_id,
        color: clusterColor,
      });

      // Connect bot to cluster center
      links.push({
        source: ip,
        target: `cluster-${cluster.cluster_id}`,
        strength: 0.5,
        color: `${clusterColor}40`, // Add transparency
      });
    });

    // Connect cluster to its suspected C2
    if (cluster.suspected_cc_ip) {
      links.push({
        source: `cluster-${cluster.cluster_id}`,
        target: cluster.suspected_cc_ip,
        strength: 1.0,
        color: '#ff475766',
      });
    }

    // Connect to associated C2s
    cluster.associated_cc_ips?.forEach((ccIP) => {
      links.push({
        source: `cluster-${cluster.cluster_id}`,
        target: ccIP,
        strength: 0.7,
        color: '#ffaa0066',
      });
    });
  });

  return { nodes, links };
}
