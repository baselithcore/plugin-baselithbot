import type { ElementDefinition } from 'cytoscape';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../lib/api';
import { EDGE_COLOR, NODE_BORDER, NODE_FILL, NODE_SHAPE, SEV_RING } from './styles';

export function buildElements(data: AttackSurfaceResp): ElementDefinition[] {
  const nodeIds = new Set(data.nodes.map((n) => n.data.id));
  const nodes: ElementDefinition[] = data.nodes.map((n: CyNode) => ({
    group: 'nodes',
    data: {
      id: n.data.id,
      label: n.data.label,
      display: (n.data.display || n.data.id).slice(0, 80),
      severity: n.data.severity ?? '',
      cvss: n.data.cvss ?? '',
      shape: NODE_SHAPE[n.data.label] ?? 'ellipse',
      fill: NODE_FILL[n.data.label] ?? '#11161f',
      border: SEV_RING[n.data.severity ?? ''] ?? NODE_BORDER[n.data.label] ?? '#1f2937',
    },
  }));
  const edges: ElementDefinition[] = data.edges
    .filter((e: CyEdge) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target))
    .map((e) => ({
      group: 'edges',
      data: { ...e.data, color: EDGE_COLOR[e.data.type] ?? '#37445a' },
    }));
  return [...nodes, ...edges];
}
