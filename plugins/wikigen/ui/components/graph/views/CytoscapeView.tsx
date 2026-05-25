/**
 * Cytoscape-backed graph viz (cose-bilkent layout).
 *
 * Label discipline mirrors the force-graph views:
 *   - edge labels OFF by default — re-emerge only on focus/hover
 *     (kind text was the main source of visual noise on dense graphs)
 *   - node labels gated by `LabelMode` (off | hubs | all) + zoom
 *   - long names truncated via `text-wrap: ellipsis` + `text-max-width`
 *   - hover dims non-neighbors and brightens the 1-hop subgraph
 *
 * Imperative cytoscape — React state diffing would be far slower than
 * direct .toggleClass() on the cytoscape collection. Filter mutations
 * never re-layout (they flip `.dimmed`); element-set changes do.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type {
  Core,
  EdgeSingular,
  ElementDefinition,
  EventObject,
  LayoutOptions,
  NodeSingular,
} from 'cytoscape';

type StyleBlock = { selector: string; style: Record<string, unknown> };
import coseBilkent from 'cytoscape-cose-bilkent';

import type { GraphData, GraphEdge, GraphNode } from '../../../lib/api/graph';
import { LabelToggle, Legend, type LabelMode } from './overlays';

let _layoutRegistered = false;
function ensureLayoutRegistered(): void {
  if (_layoutRegistered) return;
  cytoscape.use(coseBilkent);
  _layoutRegistered = true;
}

const COMMUNITY_COLOURS = [
  '#94a3b8',
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
  '#06b6d4',
  '#84cc16',
  '#a855f7',
] as const;

function communityColour(community: number): string {
  if (community < 0) return COMMUNITY_COLOURS[0];
  return COMMUNITY_COLOURS[(community + 1) % COMMUNITY_COLOURS.length];
}

function nodeSize(pagerank: number): number {
  const logged = Math.log10(1 + Math.max(0, pagerank) * 1000);
  return Math.max(22, Math.min(72, 22 + logged * 11));
}

function edgeWidth(confidence: number): number {
  return Math.max(0.8, Math.min(4, 0.8 + confidence * 3.2));
}

const HUB_PERCENTILE = 0.1;
const LABEL_ALL_MIN_ZOOM = 0.85;

interface CytoscapeViewProps {
  data: GraphData;
  visibleKinds: Set<string>;
  visibleCommunities: Set<number>;
  confidenceMin: number;
  search: string;
  onSelectNode: (node: GraphNode | null) => void;
  selectedNodeId: string | null;
}

export function CytoscapeView({
  data,
  visibleKinds,
  visibleCommunities,
  confidenceMin,
  search,
  onSelectNode,
  selectedNodeId,
}: CytoscapeViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const dataRef = useRef<GraphData>(data);
  dataRef.current = data;

  const [labelMode, setLabelMode] = useState<LabelMode>('hubs');
  const labelModeRef = useRef<LabelMode>(labelMode);
  labelModeRef.current = labelMode;

  const elements = useMemo(() => buildElements(data.nodes, data.edges), [data.nodes, data.edges]);
  const hubIds = useMemo(() => computeHubIds(data.nodes, data.edges), [data.nodes, data.edges]);
  const hubIdsRef = useRef<Set<string>>(hubIds);
  hubIdsRef.current = hubIds;

  // Mount cytoscape once per element-set.
  useEffect(() => {
    ensureLayoutRegistered();
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      wheelSensitivity: 0.25,
      minZoom: 0.15,
      maxZoom: 4,
      style: buildStyle(),
      layout: {
        name: 'cose-bilkent',
        animate: false,
        nodeRepulsion: 9000,
        idealEdgeLength: 180,
        edgeElasticity: 0.45,
        gravity: 0.25,
        gravityRangeCompound: 1.5,
        numIter: 2500,
        tile: true,
        padding: 30,
      } as unknown as LayoutOptions,
    });

    // Mark hubs once — drives label visibility via .hub class.
    cy.batch(() => {
      cy.nodes().forEach((n: NodeSingular) => {
        if (hubIdsRef.current.has(n.id())) n.addClass('hub');
      });
    });

    // Fit viewport after the deterministic layout settles.
    cy.one('layoutstop', () => cy.fit(undefined, 40));

    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target as NodeSingular;
      const nodeData = dataRef.current.nodes.find((n) => n.id === node.id());
      onSelectNode(nodeData ?? null);
    });
    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) onSelectNode(null);
    });

    // Hover highlight: brighten neighbours, dim the rest. Restored on mouseout.
    cy.on('mouseover', 'node', (evt: EventObject) => {
      const node = evt.target as NodeSingular;
      const hood = node.closedNeighborhood();
      cy.batch(() => {
        cy.elements().addClass('faded');
        hood.removeClass('faded').addClass('highlight');
        node.addClass('focus');
      });
      applyLabelClasses(cy, labelModeRef.current, cy.zoom());
    });
    cy.on('mouseout', 'node', () => {
      cy.batch(() => {
        cy.elements().removeClass('faded highlight focus');
      });
      applyLabelClasses(cy, labelModeRef.current, cy.zoom());
    });

    // Zoom-aware label gating (only matters when labelMode === 'all').
    let zoomFrame = 0;
    cy.on('zoom', () => {
      if (labelModeRef.current !== 'all') return;
      if (zoomFrame) return;
      zoomFrame = window.requestAnimationFrame(() => {
        zoomFrame = 0;
        applyLabelClasses(cy, labelModeRef.current, cy.zoom());
      });
    });

    applyLabelClasses(cy, labelModeRef.current, cy.zoom());

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, onSelectNode]);

  // Filters → class toggles, never re-layout.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const searchLower = search.trim().toLowerCase();
    cy.batch(() => {
      cy.nodes().forEach((n: NodeSingular) => {
        const kindOk = visibleKinds.size === 0 || visibleKinds.has(n.data('kind'));
        const commOk =
          visibleCommunities.size === 0 || visibleCommunities.has(n.data('community'));
        const visible = kindOk && commOk;
        n.toggleClass('dimmed', !visible);
        if (searchLower) {
          const hit = (n.data('name') || '').toLowerCase().includes(searchLower);
          n.toggleClass('search-hit', visible && hit);
        } else {
          n.removeClass('search-hit');
        }
      });
      cy.edges().forEach((e: EdgeSingular) => {
        const confOk = e.data('confidence') >= confidenceMin;
        const endpointsVisible =
          !e.source().hasClass('dimmed') && !e.target().hasClass('dimmed');
        e.toggleClass('dimmed', !(confOk && endpointsVisible));
      });
    });
    applyLabelClasses(cy, labelModeRef.current, cy.zoom());
  }, [visibleKinds, visibleCommunities, confidenceMin, search]);

  // Label mode change → recompute label classes (no layout).
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    applyLabelClasses(cy, labelMode, cy.zoom());
  }, [labelMode]);

  // External selection → centre + focus.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    cy.elements().removeClass('faded highlight focus');
    if (selectedNodeId) {
      const node = cy.getElementById(selectedNodeId);
      if (node && node.length) {
        node.select();
        node.addClass('focus');
        node.closedNeighborhood().addClass('highlight');
        cy.elements().not(node.closedNeighborhood()).addClass('faded');
        cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.4) }, { duration: 400 });
      }
    }
    applyLabelClasses(cy, labelModeRef.current, cy.zoom());
  }, [selectedNodeId]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={containerRef}
        data-testid="graph-canvas"
        className="h-full w-full bg-canvas-raised rounded-2xl border border-[var(--color-border)]"
      />
      <Legend nodes={data.nodes.length} edges={data.edges.length} hint="hover per vicini" />
      <LabelToggle mode={labelMode} onChange={setLabelMode} />
    </div>
  );
}

function applyLabelClasses(cy: Core, mode: LabelMode, zoom: number): void {
  cy.batch(() => {
    cy.nodes().forEach((n: NodeSingular) => {
      const isHub = n.hasClass('hub');
      const isFocus = n.hasClass('focus') || n.hasClass('highlight');
      let show = false;
      if (isFocus) show = true;
      else if (mode === 'off') show = false;
      else if (mode === 'hubs') show = isHub;
      else if (mode === 'all') show = isHub || zoom >= LABEL_ALL_MIN_ZOOM;
      n.toggleClass('show-label', show);
    });
    // Edge labels: only when an endpoint is the focus node.
    cy.edges().forEach((e: EdgeSingular) => {
      const hot = e.source().hasClass('focus') || e.target().hasClass('focus');
      e.toggleClass('show-label', hot);
    });
  });
}

function computeHubIds(nodes: GraphNode[], edges: GraphEdge[]): Set<string> {
  if (nodes.length === 0) return new Set();
  const deg = new Map<string, number>();
  for (const e of edges) {
    deg.set(e.src, (deg.get(e.src) ?? 0) + 1);
    deg.set(e.dst, (deg.get(e.dst) ?? 0) + 1);
  }
  const degrees = nodes.map((n) => deg.get(n.id) ?? 0).sort((a, b) => b - a);
  const idx = Math.floor(degrees.length * HUB_PERCENTILE);
  const threshold = Math.max(1, degrees[idx] ?? 1);
  const hubs = new Set<string>();
  for (const n of nodes) {
    const d = deg.get(n.id) ?? 0;
    if (d >= threshold) hubs.add(n.id);
  }
  return hubs;
}

function buildStyle(): StyleBlock[] {
  return [
    {
      selector: 'node',
      style: {
        'background-color': (n: NodeSingular) => communityColour(n.data('community')),
        label: '',
        'font-size': 11,
        'font-weight': 500,
        color: 'var(--color-ink)',
        'text-outline-width': 2,
        'text-outline-color': 'var(--color-canvas)',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 4,
        'text-wrap': 'ellipsis',
        'text-max-width': 110,
        width: (n: NodeSingular) => nodeSize(n.data('pagerank')),
        height: (n: NodeSingular) => nodeSize(n.data('pagerank')),
        'border-width': 1,
        'border-color': 'rgba(0,0,0,0.18)',
        'min-zoomed-font-size': 8,
        opacity: 1,
      } as unknown as Record<string, unknown>,
    },
    {
      selector: 'node.show-label',
      style: { label: 'data(name)' } as Record<string, unknown>,
    },
    {
      selector: 'node.hub.show-label',
      style: { 'font-size': 12, 'font-weight': 700 } as Record<string, unknown>,
    },
    {
      selector: 'node.dimmed',
      style: { opacity: 0.18, 'text-opacity': 0.25 } as Record<string, unknown>,
    },
    {
      selector: 'node.faded',
      style: { opacity: 0.18, 'text-opacity': 0 } as Record<string, unknown>,
    },
    {
      selector: 'node.highlight',
      style: { opacity: 1, 'text-opacity': 1, 'z-index': 5 } as Record<string, unknown>,
    },
    {
      selector: 'node.focus',
      style: {
        'border-width': 3,
        'border-color': '#0ea5e9',
        'z-index': 10,
      } as Record<string, unknown>,
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': '#0ea5e9',
        'border-opacity': 1,
      } as Record<string, unknown>,
    },
    {
      selector: 'node.search-hit',
      style: {
        'border-width': 3,
        'border-color': '#facc15',
        'border-opacity': 1,
      } as Record<string, unknown>,
    },
    {
      selector: 'edge',
      style: {
        width: (e: EdgeSingular) => edgeWidth(e.data('confidence')),
        'line-color': '#cbd5e1',
        'target-arrow-color': '#94a3b8',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.7,
        'curve-style': 'bezier',
        opacity: 0.55,
        label: '',
        'font-size': 9,
        color: 'var(--color-ink-muted)',
        'text-rotation': 'autorotate',
        'text-background-opacity': 0.7,
        'text-background-color': 'var(--color-canvas)',
        'text-background-padding': 2,
      } as unknown as Record<string, unknown>,
    },
    {
      selector: 'edge.show-label',
      style: { label: 'data(kind)' } as Record<string, unknown>,
    },
    {
      selector: 'edge.highlight',
      style: {
        opacity: 0.95,
        'line-color': '#0ea5e9',
        'target-arrow-color': '#0ea5e9',
        'z-index': 4,
      } as Record<string, unknown>,
    },
    {
      selector: 'edge.faded',
      style: { opacity: 0.06 } as Record<string, unknown>,
    },
    {
      selector: 'edge.dimmed',
      style: { opacity: 0.04 } as Record<string, unknown>,
    },
  ];
}

function buildElements(nodes: GraphNode[], edges: GraphEdge[]): ElementDefinition[] {
  const nodeIds = new Set(nodes.map((n) => n.id));
  return [
    ...nodes.map<ElementDefinition>((n) => ({
      group: 'nodes',
      data: {
        id: n.id,
        name: n.name,
        kind: n.kind,
        pagerank: n.pagerank,
        community: n.community,
      },
    })),
    ...edges
      .filter((e) => nodeIds.has(e.src) && nodeIds.has(e.dst))
      .map<ElementDefinition>((e) => ({
        group: 'edges',
        data: {
          id: `${e.src}__${e.kind}__${e.dst}`,
          source: e.src,
          target: e.dst,
          kind: e.kind,
          confidence: e.confidence,
        },
      })),
  ];
}
