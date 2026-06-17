import type { BotnetCluster, HubNode } from '../../../../../../types/discovery';

export interface Node {
  id: string;
  type: 'hub' | 'bot' | 'cluster';
  label: string;
  size: number;
  cluster?: string;
  centrality?: number;
  color?: string;
  x?: number;
  y?: number;
}

export interface Link {
  source: string | Node;
  target: string | Node;
  strength: number;
  color?: string;
}

export interface ClusterGraphProps {
  clusters: BotnetCluster[];
  hubNodes: HubNode[];
}
