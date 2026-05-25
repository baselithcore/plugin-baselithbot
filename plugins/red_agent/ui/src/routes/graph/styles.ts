import type { Css, LayoutOptions, StylesheetStyle } from 'cytoscape';
import type { LayoutName } from './types';
import type { Severity } from '../../lib/api';

export const NODE_SHAPE: Record<string, Css.NodeShape> = {
  Target: 'round-hexagon',
  CloudResource: 'round-rectangle',
  Endpoint: 'round-rectangle',
  Service: 'round-diamond',
  Vulnerability: 'round-octagon',
  Identity: 'ellipse',
  DataStore: 'barrel',
  ApiSpec: 'round-tag',
  CWE: 'ellipse',
  CVE: 'ellipse',
  Scan: 'round-rectangle',
  Scanner: 'round-tag',
};

export const NODE_FILL: Record<string, string> = {
  Target: '#0c2a2e',
  CloudResource: '#111f38',
  Endpoint: '#0e2233',
  Service: '#0e2a26',
  Vulnerability: '#2a1418',
  Identity: '#231a35',
  DataStore: '#172715',
  ApiSpec: '#271d12',
  CWE: '#1a1f2b',
  CVE: '#2a2410',
  Scan: '#1a1830',
  Scanner: '#0c2a2e',
};

export const NODE_BORDER: Record<string, string> = {
  Target: '#00ffd1',
  CloudResource: '#5b8cff',
  Endpoint: '#4cc9f0',
  Service: '#2dd4bf',
  Vulnerability: '#ff7a18',
  Identity: '#9b87f5',
  DataStore: '#86efac',
  ApiSpec: '#f59e0b',
  CWE: '#6b7a90',
  CVE: '#ffb000',
  Scan: '#9b87f5',
  Scanner: '#00ffd1',
};

export const SEV_RING: Record<string, string> = {
  info: '#4cc9f0',
  low: '#2dd4bf',
  medium: '#ffb000',
  high: '#ff7a18',
  critical: '#ff3860',
};

export const EDGE_COLOR: Record<string, string> = {
  HAS_VULN: '#ff7a18',
  HAS_ENDPOINT: '#4cc9f0',
  EXPOSES: '#00ffd1',
  SCANNED_BY: '#9b87f5',
  FOUND: '#ff3860',
  FOUND_IN: '#ff3860',
  MAPS_TO: '#6b7a90',
  DETECTED_BY: '#2dd4bf',
  HOSTS: '#5b8cff',
  RUNS_AS: '#9b87f5',
  STORES: '#86efac',
  GOVERNED_BY: '#f59e0b',
  LATERAL_TO: '#ff3860',
};

export const SEV_RANK: Record<string, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

export function severityRank(s: Severity | null | undefined): number {
  return SEV_RANK[s ?? ''] ?? 0;
}

const NODE_TYPE_RANK: Record<string, number> = {
  Target: 10,
  CloudResource: 9,
  Endpoint: 8,
  Service: 8,
  Vulnerability: 6,
  Identity: 5,
  DataStore: 5,
  ApiSpec: 5,
  Scanner: 4,
  Scan: 4,
  CVE: 2,
  CWE: 2,
};

export const LAYOUT_OPTS: Record<LayoutName, LayoutOptions> = {
  fcose: {
    name: 'fcose',
    animate: true,
    animationDuration: 350,
    nodeRepulsion: 9000,
    idealEdgeLength: 110,
    nodeSeparation: 90,
    randomize: false,
    quality: 'proof',
    padding: 40,
  } as LayoutOptions,
  concentric: {
    name: 'concentric',
    animate: true,
    animationDuration: 350,
    minNodeSpacing: 40,
    concentric: (n) => NODE_TYPE_RANK[String(n.data('label'))] ?? 1,
    levelWidth: () => 1,
    padding: 40,
  } as LayoutOptions,
  breadthfirst: {
    name: 'breadthfirst',
    animate: true,
    animationDuration: 350,
    directed: true,
    spacingFactor: 1.4,
    padding: 40,
  } as LayoutOptions,
};

export const STYLE: StylesheetStyle[] = [
  {
    selector: 'node',
    style: {
      'background-color': 'data(fill)',
      'background-opacity': 0.92,
      'border-color': 'data(border)',
      'border-width': 2.5,
      'border-opacity': 0.96,
      shape: 'data(shape)' as never,
      label: 'data(display)',
      color: '#e7ecf7',
      'font-family': '"JetBrains Mono Variable", ui-monospace',
      'font-size': 10,
      'font-weight': 500,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'text-outline-color': '#0a0e14',
      'text-outline-width': 2.5,
      'text-wrap': 'ellipsis',
      'text-max-width': '150',
      width: 48,
      height: 48,
      'transition-property': 'opacity, border-width, width, height',
      'transition-duration': 180,
    } as Css.Node,
  },
  {
    selector: 'node[severity = "high"]',
    style: { 'border-width': 3.5, width: 52, height: 52 } as Css.Node,
  },
  {
    selector: 'node[severity = "critical"]',
    style: {
      'border-width': 4,
      width: 58,
      height: 58,
      'overlay-color': '#ff3860',
      'overlay-opacity': 0.12,
    } as Css.Node,
  },
  {
    selector: 'node[label = "Target"]',
    style: { width: 66, height: 66, 'font-weight': 700 } as Css.Node,
  },
  {
    selector: 'node[label = "Vulnerability"]',
    style: { 'background-color': '#2a1418', width: 54, height: 54 } as Css.Node,
  },
  {
    selector: 'edge',
    style: {
      'line-color': 'data(color)',
      'target-arrow-color': 'data(color)',
      'target-arrow-shape': 'triangle-backcurve',
      'arrow-scale': 0.9,
      'curve-style': 'bezier',
      'line-cap': 'round',
      width: 1.6,
      label: 'data(type)',
      color: '#8b98b6',
      'font-family': '"JetBrains Mono Variable", ui-monospace',
      'font-size': 8,
      'text-rotation': 'autorotate',
      'text-background-color': '#0a0e14',
      'text-background-opacity': 0.7,
      'text-background-padding': '2',
      opacity: 0.82,
      'transition-property': 'opacity, width',
      'transition-duration': 180,
    } as Css.Edge,
  },
  {
    selector: 'edge.dense',
    style: {
      label: '',
      opacity: 0.62,
      width: 1.2,
    } as Css.Edge,
  },
  {
    selector: 'edge[type = "MAPS_TO"], edge[type = "DETECTED_BY"], edge[type = "GOVERNED_BY"]',
    style: { 'line-style': 'dashed', opacity: 0.7 } as Css.Edge,
  },
  {
    selector: 'edge[type = "LATERAL_TO"], edge[type = "HAS_VULN"], edge[type = "FOUND"]',
    style: { width: 2.2 } as Css.Edge,
  },
  {
    selector: '.dim',
    style: { opacity: 0.12 } as Css.Node,
  },
  {
    selector: '.searchDim',
    style: { opacity: 0.24 } as Css.Node,
  },
  {
    selector: 'edge.searchDim',
    style: { opacity: 0.1 } as Css.Edge,
  },
  {
    selector: '.searchHit',
    style: {
      'border-width': 4,
      'border-color': '#33dcff',
      'overlay-color': '#33dcff',
      'overlay-opacity': 0.16,
    } as Css.Node,
  },
  {
    selector: 'edge.searchHit',
    style: { width: 2.8, opacity: 1 } as Css.Edge,
  },
  {
    selector: '.focus',
    style: {
      'border-width': 4,
      'overlay-color': '#00ffd1',
      'overlay-opacity': 0.12,
    } as Css.Node,
  },
  {
    selector: 'edge.focus',
    style: { width: 2.4, opacity: 1 } as Css.Edge,
  },
  {
    selector: '.path',
    style: {
      'border-color': '#ffb000',
      'border-width': 4,
      'overlay-color': '#ffb000',
      'overlay-opacity': 0.12,
    } as Css.Node,
  },
  {
    selector: 'edge.path',
    style: {
      'line-color': '#ffb000',
      'target-arrow-color': '#ffb000',
      width: 2.6,
      opacity: 1,
    } as Css.Edge,
  },
  {
    selector: '.hidden',
    style: { display: 'none' } as Css.Node,
  },
];
