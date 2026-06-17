import type { BotnetCluster, HubNode } from '../../../../../../types/discovery';

export interface Node {
  id: string;
  type: 'hub' | 'bot' | 'cluster';
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  cluster?: string;
  centrality?: number;
}

export interface Edge {
  source: string;
  target: string;
  strength: number;
}

export interface ClusterGraphProps {
  clusters: BotnetCluster[];
  hubNodes: HubNode[];
}
