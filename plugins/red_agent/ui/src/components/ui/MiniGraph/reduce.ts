import type { ElementDefinition } from 'cytoscape';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../../lib/api';
import {
  EDGE_COLOR,
  NODE_BORDER,
  NODE_FILL,
  NODE_SHAPE,
  SEV_RING,
} from '../../../routes/graph/styles';
import { TYPE_HINT } from './styles';
import type { ClusterMembers, Reduced } from './types';

export function shorten(s: string, max: number): string {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}

// Drop redundant Target -> Vulnerability edge when Endpoint -> Vulnerability
// edge already exists (vuln semantically attached to endpoint).
// Then fold sibling leaves of same (parent, label, rel_type) into a cluster
// node so the attack-path renders close to one-line.
export function reduceGraph(data: AttackSurfaceResp, highlightId: string | null): Reduced {
  const nodeById = new Map(data.nodes.map((n) => [n.data.id, n]));
  let edges = data.edges.slice();

  // 1) Drop redundant Target -> V edge if Endpoint -> V exists.
  const endpointVulnTargets = new Set<string>();
  edges.forEach((e) => {
    if (e.data.type !== 'HAS_VULN') return;
    const src = nodeById.get(e.data.source);
    if (src?.data.label === 'Endpoint') endpointVulnTargets.add(e.data.target);
  });
  edges = edges.filter((e) => {
    if (e.data.type !== 'HAS_VULN') return true;
    const src = nodeById.get(e.data.source);
    if (src?.data.label !== 'Target') return true;
    return !endpointVulnTargets.has(e.data.target);
  });

  // 2) Compute degrees on the trimmed edge set.
  const outDeg = new Map<string, number>();
  const inEdges = new Map<string, CyEdge[]>();
  edges.forEach((e) => {
    outDeg.set(e.data.source, (outDeg.get(e.data.source) ?? 0) + 1);
    if (!inEdges.has(e.data.target)) inEdges.set(e.data.target, []);
    inEdges.get(e.data.target)!.push(e);
  });

  // 3) Group leaves: out-degree 0, in-degree 1, not the highlighted finding.
  const groups = new Map<string, string[]>();
  data.nodes.forEach((n) => {
    if (n.data.id === highlightId) return;
    const out = outDeg.get(n.data.id) ?? 0;
    const inc = inEdges.get(n.data.id) ?? [];
    if (out !== 0 || inc.length !== 1) return;
    const e = inc[0]!;
    const key = `${e.data.source}|${n.data.label}|${e.data.type}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(n.data.id);
  });

  const clustered = new Set<string>();
  const clusterMembers = new Map<string, ClusterMembers[]>();
  const clusterNodes: CyNode[] = [];
  const clusterEdges: CyEdge[] = [];

  groups.forEach((ids, key) => {
    if (ids.length < 2) return;
    const parts = key.split('|');
    const parent = parts[0] ?? '';
    const label = parts[1] ?? '';
    const relType = parts[2] ?? '';
    ids.forEach((id) => clustered.add(id));
    const cid = `cluster::${parent}::${label}::${relType}`;
    clusterNodes.push({
      data: {
        id: cid,
        label,
        display: `${TYPE_HINT[label] ?? label}s (${ids.length})`,
        severity: null,
        cvss: null,
      },
    } as unknown as CyNode);
    clusterEdges.push({
      data: {
        id: `${parent}--${relType}-->${cid}`,
        source: parent,
        target: cid,
        type: relType,
      },
    });
    clusterMembers.set(
      cid,
      ids.map((id) => {
        const m = nodeById.get(id);
        return {
          id,
          display: m?.data.display || id,
          severity: m?.data.severity ?? null,
          cvss: m?.data.cvss ?? null,
        };
      })
    );
  });

  const remainingNodes = data.nodes.filter((n) => !clustered.has(n.data.id));
  const remainingEdges = edges.filter(
    (e) => !clustered.has(e.data.source) && !clustered.has(e.data.target)
  );

  return {
    nodes: [...remainingNodes, ...clusterNodes],
    edges: [...remainingEdges, ...clusterEdges],
    clusterMembers,
  };
}

export function buildAttackPathElements(
  reduced: Reduced,
  highlightId?: string | null
): ElementDefinition[] {
  const nodeIds = new Set(reduced.nodes.map((n) => n.data.id));
  const nodes: ElementDefinition[] = reduced.nodes.map((n: CyNode) => {
    const isCluster = n.data.id.startsWith('cluster::');
    const ring = SEV_RING[n.data.severity ?? ''] ?? NODE_BORDER[n.data.label] ?? '#4cc9f0';
    const name = shorten(n.data.display || n.data.id, 28);
    const type = TYPE_HINT[n.data.label] ?? n.data.label;
    return {
      group: 'nodes',
      data: {
        id: n.data.id,
        label: n.data.label,
        display: isCluster ? name : `${name}\n${type}`,
        severity: n.data.severity ?? '',
        cvss: n.data.cvss ?? '',
        ring,
        shape: NODE_SHAPE[n.data.label] ?? 'round-rectangle',
        fill: NODE_FILL[n.data.label] ?? '#0d131c',
        isCluster: isCluster ? '1' : '0',
      },
      classes: highlightId && n.data.id === highlightId ? 'focus' : '',
    };
  });
  const edges: ElementDefinition[] = reduced.edges
    .filter((e: CyEdge) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target))
    .map((e) => ({
      group: 'edges',
      data: { ...e.data, color: EDGE_COLOR[e.data.type] ?? '#37445a' },
      classes:
        highlightId && (e.data.source === highlightId || e.data.target === highlightId)
          ? 'focus'
          : '',
    }));
  return [...nodes, ...edges];
}
