import type { Severity } from '../../lib/api';

export type LayoutName = 'fcose' | 'concentric' | 'breadthfirst';
export type ViewMode = 'graph' | 'graph3d' | 'table';

export interface SelectedNode {
  kind: 'node';
  id: string;
  label: string;
  display: string;
  severity: Severity | null;
  cvss: number | null;
  neighbors: number;
}

export interface SelectedEdge {
  kind: 'edge';
  id: string;
  type: string;
  source: string;
  target: string;
  sourceLabel: string;
  targetLabel: string;
}

export type Selected = SelectedNode | SelectedEdge;

export const NODE_TYPES = [
  'Target',
  'CloudResource',
  'Endpoint',
  'Service',
  'Vulnerability',
  'Identity',
  'DataStore',
  'ApiSpec',
  'Scan',
  'Scanner',
  'CVE',
  'CWE',
] as const;
export type NodeType = (typeof NODE_TYPES)[number];

export const SEVERITIES: Severity[] = ['info', 'low', 'medium', 'high', 'critical'];

export interface GraphSummaryStats {
  nodes: number;
  edges: number;
  visibleNodes: number;
  vulnerabilities: number;
  criticalHigh: number;
  entryPoints: number;
  enrichments: number;
  maxCvss: number | null;
  exposureScore: number;
}
