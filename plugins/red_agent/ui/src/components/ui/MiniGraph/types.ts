import type { CyEdge, CyNode } from '../../../lib/api';

export type ClusterMembers = {
  id: string;
  display: string;
  severity?: string | null;
  cvss?: string | number | null;
};

export type SelectedNode = {
  id: string;
  label: string;
  type: string;
  display: string;
  severity?: string;
  cvss?: string | number;
  isCluster: boolean;
  members?: ClusterMembers[];
  ring: string;
};

export type Reduced = {
  nodes: CyNode[];
  edges: CyEdge[];
  clusterMembers: Map<string, ClusterMembers[]>;
};
