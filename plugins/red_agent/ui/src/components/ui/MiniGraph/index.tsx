import { useEffect, useMemo, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core } from 'cytoscape';
// @ts-expect-error — cytoscape-dagre ships no types.
import dagre from 'cytoscape-dagre';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../../lib/api';
import { NODE_BORDER, SEV_RING } from '../../../routes/graph/styles';
import { buildAttackPathElements, reduceGraph } from './reduce';
import { STYLE, TYPE_HINT } from './styles';
import { NodeDetailCard } from './parts/NodeDetailCard';
import type { Reduced, SelectedNode } from './types';

let _registered = false;
function ensureExtensionRegistered(): void {
  if (_registered) return;
  cytoscape.use(dagre);
  _registered = true;
}

export function MiniGraph({
  data,
  height = 320,
  highlightId,
  fill = false,
}: {
  data: AttackSurfaceResp;
  height?: number;
  highlightId?: string | null;
  fill?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [selected, setSelected] = useState<SelectedNode | null>(null);

  const reduced = useMemo<Reduced>(() => {
    const r = reduceGraph(data, highlightId ?? null);
    if (expanded.size === 0) return r;
    // Re-expand selected clusters: drop cluster node, restore members & their incoming edge.
    const keepNodes: CyNode[] = [];
    const keepEdges: CyEdge[] = [];
    const restored = new Set<string>();
    r.nodes.forEach((n) => {
      if (n.data.id.startsWith('cluster::') && expanded.has(n.data.id)) {
        const members = r.clusterMembers.get(n.data.id) ?? [];
        const parts = n.data.id.split('::');
        const parent = parts[1] ?? '';
        const relType = parts[3] ?? '';
        members.forEach((m) => {
          const orig = data.nodes.find((dn) => dn.data.id === m.id);
          if (orig) keepNodes.push(orig);
          keepEdges.push({
            data: {
              id: `${parent}--${relType}-->${m.id}`,
              source: parent,
              target: m.id,
              type: relType,
            },
          });
          restored.add(m.id);
        });
        return;
      }
      keepNodes.push(n);
    });
    r.edges.forEach((e) => {
      if (e.data.source.startsWith('cluster::') && expanded.has(e.data.source)) return;
      if (e.data.target.startsWith('cluster::') && expanded.has(e.data.target)) return;
      keepEdges.push(e);
    });
    return { nodes: keepNodes, edges: keepEdges, clusterMembers: r.clusterMembers };
  }, [data, highlightId, expanded]);

  useEffect(() => {
    ensureExtensionRegistered();
    if (!containerRef.current) return;
    const elements = buildAttackPathElements(reduced, highlightId);

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: STYLE,
      layout: {
        name: 'dagre',
        rankDir: 'LR',
        ranker: 'longest-path',
        nodeSep: 70,
        rankSep: 170,
        edgeSep: 30,
        animate: false,
        padding: 50,
      } as unknown as cytoscape.LayoutOptions,
      wheelSensitivity: 0.2,
      minZoom: 0.4,
      maxZoom: 2.5,
    });
    cyRef.current = cy;

    cy.fit(undefined, 40);
    if (highlightId) {
      const target = cy.getElementById(highlightId);
      if (target.nonempty()) cy.center(target);
    }

    cy.on('tap', 'node', (e) => {
      const n = e.target;
      const id = n.id();
      const raw = reduced.nodes.find((rn) => rn.data.id === id);
      if (!raw) return;
      const isCluster = id.startsWith('cluster::');
      setSelected({
        id,
        label: raw.data.label,
        type: TYPE_HINT[raw.data.label] ?? raw.data.label,
        display: raw.data.display || id,
        severity: raw.data.severity ?? undefined,
        cvss: raw.data.cvss ?? undefined,
        isCluster,
        members: isCluster ? reduced.clusterMembers.get(id) : undefined,
        ring: SEV_RING[raw.data.severity ?? ''] ?? NODE_BORDER[raw.data.label] ?? '#4cc9f0',
      });
    });
    cy.on('tap', (e) => {
      if (e.target === cy) setSelected(null);
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [reduced, highlightId]);

  const toggleCluster = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSelected(null);
  };

  return (
    <div
      style={fill ? undefined : { height }}
      className={`relative w-full overflow-hidden rounded border border-bg-line bg-bg-base ${
        fill ? 'h-full' : ''
      }`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, #6b7a90 1px, transparent 0)',
          backgroundSize: '18px 18px',
        }}
      />
      <div ref={containerRef} className="relative h-full w-full" />
      {selected && (
        <NodeDetailCard
          selected={selected}
          onClose={() => setSelected(null)}
          onToggleCluster={toggleCluster}
          isClusterExpanded={selected.isCluster && expanded.has(selected.id)}
        />
      )}
    </div>
  );
}
